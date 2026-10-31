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
    
    # AI
    AI_PROVIDER: str = "mock"
    BHARATCODE_API_KEY: str = ""
    
    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
