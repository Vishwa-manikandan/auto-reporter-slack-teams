import os
from app.core.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.APP_NAME == "Auto-Reporter"
    assert s.DEBUG is False
    assert s.DATABASE_URL == "sqlite:///./autoreporter.db"
    assert isinstance(s.CORS_ORIGINS, list)


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("APP_NAME", "TestApp")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    s = Settings()
    assert s.APP_NAME == "TestApp"
    assert s.DEBUG is True
    assert s.DATABASE_URL == "sqlite:///./test.db"
