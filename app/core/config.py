from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "Auto-Reporter"
    DEBUG: bool = False
    DATABASE_URL: str = "sqlite:///./autoreporter.db"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Slack
    SLACK_CLIENT_ID: str = ""
    SLACK_CLIENT_SECRET: str = ""
    SLACK_SIGNING_SECRET: str = ""
    SLACK_BOT_TOKEN: str = ""
    SLACK_CHANNEL_ID: str = ""
    SLACK_API_TIMEOUT: float = 30.0
    SLACK_REDIRECT_URI: str = ""
    SLACK_SCOPES: str = "channels:read,groups:read,chat:write,users:read"

    # OAuth
    TOKEN_ENCRYPTION_KEY: str = ""
    OAUTH_STATE_TTL_SECONDS: int = 600

    # AI
    AI_PROVIDER: str = "mock"
    AI_API_KEY: str = ""
    AI_MODEL: str = ""
    AI_API_BASE_URL: str = ""
    AI_REQUEST_TIMEOUT: float = 60.0
    AI_MAX_OUTPUT_TOKENS: int = 1024
    AI_RETRY_LIMIT: int = 2
    BHARATCODE_API_KEY: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
