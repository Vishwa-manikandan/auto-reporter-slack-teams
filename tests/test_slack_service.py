import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from slack_sdk.errors import SlackApiError

from app.services.slack_service import (
    SlackAuthError,
    SlackPermissionError,
    SlackRateLimitError,
    SlackService,
    SlackServiceError,
)


@pytest.mark.asyncio
async def test_test_auth_success():
    with patch("app.services.slack_service.AsyncWebClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.auth_test.return_value = {
            "ok": True,
            "team": "Test Team",
            "team_id": "T123",
            "user": "bot",
            "user_id": "U123",
            "bot_id": "B123",
            "url": "https://test.slack.com",
        }
        service = SlackService(token="xoxb-test")
        result = await service.test_auth()
        assert result["team_id"] == "T123"
        assert result["ok"] is True


@pytest.mark.asyncio
async def test_test_auth_invalid():
    with patch("app.services.slack_service.AsyncWebClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        error_response = {"ok": False, "error": "invalid_auth"}
        mock_client.auth_test.side_effect = SlackApiError(message="invalid_auth", response=MagicMock(data=error_response))
        # Make response attribute accessible
        error = SlackApiError(message="invalid_auth", response=error_response)
        mock_client.auth_test.side_effect = error
        service = SlackService(token="xoxb-bad")
        with pytest.raises(SlackAuthError):
            await service.test_auth()


@pytest.mark.asyncio
async def test_test_auth_missing_scope():
    with patch("app.services.slack_service.AsyncWebClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        error_response = {"ok": False, "error": "missing_scope"}
        error = SlackApiError(message="missing_scope", response=error_response)
        mock_client.auth_test.side_effect = error
        service = SlackService(token="xoxb-test")
        with pytest.raises(SlackPermissionError):
            await service.test_auth()


@pytest.mark.asyncio
async def test_get_channels_success():
    with patch("app.services.slack_service.AsyncWebClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.conversations_list.return_value = {
            "ok": True,
            "channels": [
                {"id": "C1", "name": "general"},
                {"id": "C2", "name": "random"},
            ],
            "response_metadata": {"next_cursor": ""},
        }
        service = SlackService(token="xoxb-test")
        channels = await service.get_channels()
        assert len(channels) == 2
        assert channels[0]["name"] == "general"


@pytest.mark.asyncio
async def test_get_channels_pagination():
    with patch("app.services.slack_service.AsyncWebClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        # First page
        mock_client.conversations_list.side_effect = [
            {
                "ok": True,
                "channels": [{"id": "C1", "name": "general"}],
                "response_metadata": {"next_cursor": "cursor123"},
            },
            {
                "ok": True,
                "channels": [{"id": "C2", "name": "random"}],
                "response_metadata": {"next_cursor": ""},
            },
        ]
        service = SlackService(token="xoxb-test")
        channels = await service.get_channels()
        assert len(channels) == 2
        assert mock_client.conversations_list.call_count == 2


@pytest.mark.asyncio
async def test_get_channels_empty():
    with patch("app.services.slack_service.AsyncWebClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.conversations_list.return_value = {
            "ok": True,
            "channels": [],
            "response_metadata": {"next_cursor": ""},
        }
        service = SlackService(token="xoxb-test")
        channels = await service.get_channels()
        assert channels == []


@pytest.mark.asyncio
async def test_get_channels_ratelimit():
    with patch("app.services.slack_service.AsyncWebClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        error_response = {"ok": False, "error": "ratelimited"}
        error = SlackApiError(message="ratelimited", response=error_response)
        mock_client.conversations_list.side_effect = error
        service = SlackService(token="xoxb-test")
        with pytest.raises(SlackRateLimitError):
            await service.get_channels()


@pytest.mark.asyncio
async def test_get_workspace_info():
    with patch("app.services.slack_service.AsyncWebClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value = mock_client
        mock_client.auth_test.return_value = {
            "ok": True,
            "team": "Test Team",
            "team_id": "T123",
            "bot_id": "B123",
            "user_id": "U123",
            "url": "https://test.slack.com",
        }
        service = SlackService(token="xoxb-test")
        info = await service.get_workspace_info()
        assert info["team_id"] == "T123"
        assert info["connected"] is True
