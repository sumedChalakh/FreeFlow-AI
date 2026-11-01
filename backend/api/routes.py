"""OpenAI-compatible v1 API routes for FreeFlow AI.

Exposes GET /v1/models and POST /v1/chat/completions endpoints bound to loopback,
protected by Bearer token authentication, and integrated with ModelCatalog
and RoutingEngine.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from backend.catalog.service import ModelCatalog
from backend.providers.base import ChatCompletionRequest, ChatMessage
from backend.routing.engine import RoutingEngine

from .deps import get_catalog, get_routing_engine, verify_token
from .models import (
    ChatChoiceOutput,
    ChatCompletionRequestPayload,
    ChatCompletionResponsePayload,
    ChatMessageInput,
    ModelCard,
    ModelListResponse,
    UsageOutput,
)

v1_router = APIRouter(prefix="/v1", tags=["OpenAI-Compatible"])


@v1_router.get(
    "/models",
    response_model=ModelListResponse,
    summary="List available models and routing profiles",
)
async def list_models(
    _token: str = Depends(verify_token),  # noqa: B008
    catalog: ModelCatalog = Depends(get_catalog),  # noqa: B008
    engine: RoutingEngine = Depends(get_routing_engine),  # noqa: B008
) -> ModelListResponse:
    """List routing aliases and discovered non-stale catalog models."""
    cards: list[ModelCard] = []
    seen_ids: set[str] = set()

    # 1. Routing profiles (aliases, both built-in and restored custom profiles)
    for p_name in engine.list_profiles():
        if p_name not in seen_ids:
            seen_ids.add(p_name)
            cards.append(ModelCard(id=p_name, owned_by="freeflow-ai"))

    # 2. Catalog models (including restored entries)
    for entry in catalog.list_entries(include_stale=True):
        # Add composite ID (e.g. 'ollama:llama3.2:3b')
        if entry.composite_id not in seen_ids:
            seen_ids.add(entry.composite_id)
            cards.append(
                ModelCard(
                    id=entry.composite_id,
                    owned_by=entry.provider_id,
                )
            )

        # Add pure model ID (e.g. 'llama3.2:3b')
        if entry.model_id not in seen_ids:
            seen_ids.add(entry.model_id)
            cards.append(
                ModelCard(
                    id=entry.model_id,
                    owned_by=entry.provider_id,
                )
            )

    return ModelListResponse(data=cards)


@v1_router.post(
    "/chat/completions",
    response_model=ChatCompletionResponsePayload,
    summary="Create a non-streaming chat completion",
)
async def create_chat_completion(
    payload: ChatCompletionRequestPayload,
    _token: str = Depends(verify_token),  # noqa: B008
    engine: RoutingEngine = Depends(get_routing_engine),  # noqa: B008
) -> ChatCompletionResponsePayload:
    """Execute a non-streaming chat completion.

    Streaming is explicitly not supported in this version.
    """
    if payload.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Streaming is not currently supported in FreeFlow AI. Please set stream=false.",
        )

    # Convert API message models to internal ChatMessage domain models
    internal_messages = [
        ChatMessage(
            role=msg.role,
            content=msg.content,
            name=msg.name,
        )
        for msg in payload.messages
    ]

    internal_request = ChatCompletionRequest(
        model=payload.model,
        messages=internal_messages,
        max_tokens=payload.max_tokens,
        temperature=payload.temperature,
        top_p=payload.top_p,
        stream=False,
        stop=payload.stop,
    )

    response, _ = await engine.complete_chat(
        internal_request,
        target=payload.model,
    )

    choices = [
        ChatChoiceOutput(
            index=choice.index,
            message=ChatMessageInput(
                role=choice.message.role,
                content=choice.message.content,
                name=choice.message.name,
            ),
            finish_reason=choice.finish_reason,
        )
        for choice in response.choices
    ]

    usage_output = None
    if response.usage is not None:
        usage_output = UsageOutput(
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
        )

    return ChatCompletionResponsePayload(
        id=response.id,
        created=response.created_at,
        model=response.model,
        choices=choices,
        usage=usage_output,
    )
