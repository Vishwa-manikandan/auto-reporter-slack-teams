import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from cryptography.fernet import Fernet

from app.main import app
from app.core import config
from app.services.encryption_service import EncryptionService


client = TestClient(app)


def test_oauth_install_missing_config():
    original_id = config.settings.SLACK_CLIENT_ID
    original_uri = config.settings.SLACK_REDIRECT_URI
    try:
        config.settings.SLACK_CLIENT_ID = ""
        config.settings.SLACK_REDIRECT_URI = ""
        response = client.get("/api/v1/auth/slack/install")
        assert response.status_code == 400
    finally:
        config.settings.SLACK_CLIENT_ID = original_id
        config.settings.SLACK_REDIRECT_URI = original_uri


def test_encryption_roundtrip():
    key = Fernet.generate_key().decode()
    service = EncryptionService(key=key)
    token = "xoxb-test-token"
    encrypted = service.encrypt(token)
    assert encrypted != token
    decrypted = service.decrypt(encrypted)
    assert decrypted == token


def test_encryption_missing_key():
    from app.services.encryption_service import EncryptionServiceError
    original = config.settings.TOKEN_ENCRYPTION_KEY
    try:
        config.settings.TOKEN_ENCRYPTION_KEY = ""
        with pytest.raises(EncryptionServiceError):
            EncryptionService()
    finally:
        config.settings.TOKEN_ENCRYPTION_KEY = original
