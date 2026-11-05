"""OpenAI-compatible request and response schemas for FreeFlow AI.

Adheres strictly to the OpenAI API specification conventions for
model listing and chat completions.
"""

import time

from pydantic import BaseModel, Field


class ModelCard(BaseModel):
    """An individual model card in OpenAI format."""

    id: str = Field(..., description="Model identifier or routing alias")
    object: str = Field(default="model", description="Object type")
    created: int = Field(
        default_factory=lambda: int(time.time()),
        description="Unix timestamp when entry was recorded",
    )
    owned_by: str = Field(default="freeflow-ai", description="Owner or provider name")


class ModelListResponse(BaseModel):
    """Response returned by GET /v1/models."""

    object: str = Field(default="list", description="Object type")
    data: list[ModelCard] = Field(default_factory=list, description="Available models and aliases")


class ChatMessageInput(BaseModel):
    """A message in a chat completions request."""

    role: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Message author role: 'system', 'user', 'assistant'",
    )
    content: str = Field(..., description="Text content of the message")
    name: str | None = Field(
        default=None,
        max_length=64,
        description="Optional name of the participant",
    )


class ChatCompletionRequestPayload(BaseModel):
    """Payload for POST /v1/chat/completions."""

    model: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Model deployment ID or routing profile",
    )
    messages: list[ChatMessageInput] = Field(
        ...,
        min_length=1,
        description="Ordered list of messages comprising the conversation",
    )
    max_tokens: int | None = Field(
        default=None,
        ge=1,
        description="Maximum number of tokens to generate",
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling probability",
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream partial tokens. Not supported in this slice.",
    )
    stop: list[str] | str | None = Field(
        default=None,
        description="Stop sequence(s)",
    )


class ChatChoiceOutput(BaseModel):
    """A generated completion choice."""

    index: int = Field(default=0, description="Choice index")
    message: ChatMessageInput = Field(..., description="Generated message")
    finish_reason: str | None = Field(default="stop", description="Reason token generation stopped")


class UsageOutput(BaseModel):
    """Token usage details. Missing fields remain None (never fabricated as zero)."""

    prompt_tokens: int | None = Field(default=None, description="Prompt tokens used")
    completion_tokens: int | None = Field(default=None, description="Completion tokens used")
    total_tokens: int | None = Field(default=None, description="Total tokens used")


class ChatCompletionResponsePayload(BaseModel):
    """Response returned by POST /v1/chat/completions."""

    id: str = Field(..., description="Unique completion ID")
    object: str = Field(default="chat.completion", description="Object type")
    created: int = Field(
        default_factory=lambda: int(time.time()),
        description="Unix timestamp when completion was generated",
    )
    model: str = Field(..., description="Model ID that generated the completion")
    choices: list[ChatChoiceOutput] = Field(..., min_length=1, description="Generated choices")
    usage: UsageOutput | None = Field(
        default=None,
        description="Token usage breakdown if reported by backend",
    )
    system_fingerprint: str | None = Field(
        default=None,
        description="System fingerprint",
    )


class OpenAiErrorDetail(BaseModel):
    """Normalized OpenAI error structure."""

    message: str = Field(..., description="Human-readable error description")
    type: str = Field(..., description="Error category classification")
    param: str | None = Field(default=None, description="Related parameter name if applicable")
    code: str | None = Field(default=None, description="Machine-readable error code")


class OpenAiErrorEnvelope(BaseModel):
    """OpenAI error envelope wrapper."""

    error: OpenAiErrorDetail
