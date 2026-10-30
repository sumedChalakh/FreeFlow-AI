pyrefly: ignore[missing-import]
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    api_host: str = Field('127.0.0.1', description='Bind address, loopback by default')
    api_port: int = Field(8000, ge=1, le=65535, description='Port to listen on')
    api_token: str = Field('', description='Secret token for authentication')
    log_level: str = Field('INFO', description='Logging level')

    class Config:
        env_file = '.env'
        case_sensitive = False



settings = Settings()
