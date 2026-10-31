import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app


client = TestClient(app)


def test_slack_status_missing_token():
    # When no token configured, get_slack_service should raise
    from app.core import config
    original = config.settings.SLACK_BOT_TOKEN
    try:
        config.settings.SLACK_BOT_TOKEN = ""
        response = client.get("/api/v1/slack/status")
        assert response.status_code == 401
    finally:
        config.settings.SLACK_BOT_TOKEN = original


@patch("app.api.slack.SlackService")
def test_slack_status_connected(mock_slack_service_cls):
    mock_service = AsyncMock()
    mock_slack_service_cls.return_value = mock_service
    mock_service.get_workspace_info.return_value = {
        "team_id": "T123",
        "team": "Test",
        "connected": True,
    }
    response = client.get("/api/v1/slack/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"


@patch("app.api.slack.SlackService")
def test_slack_channels(mock_slack_service_cls):
    mock_service = AsyncMock()
    mock_slack_service_cls.return_value = mock_service
    mock_service.get_channels.return_value = [
        {"id": "C1", "name": "general"},
    ]
    response = client.get("/api/v1/slack/channels")
    assert response.status_code == 200
    data = response.json()
    assert len(data["channels"]) == 1
