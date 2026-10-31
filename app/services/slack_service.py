from typing import List, Dict, Any, Optional

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from app.core.config import settings


class SlackServiceError(Exception):
    """Base exception for Slack service errors."""

    def __init__(self, message: str, error: Optional[str] = None, response: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.error = error
        self.response = response or {}


class SlackAuthError(SlackServiceError):
    pass


class SlackPermissionError(SlackServiceError):
    pass


class SlackRateLimitError(SlackServiceError):
    pass


class SlackService:
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.SLACK_BOT_TOKEN
        if not self.token:
            raise SlackAuthError("Slack bot token is not configured")
        self.client = AsyncWebClient(token=self.token, timeout=settings.SLACK_API_TIMEOUT)

    async def test_auth(self) -> Dict[str, Any]:
        try:
            result = await self.client.auth_test()
            return {
                "ok": result.get("ok", False),
                "team": result.get("team"),
                "team_id": result.get("team_id"),
                "user": result.get("user"),
                "user_id": result.get("user_id"),
                "bot_id": result.get("bot_id"),
                "url": result.get("url"),
            }
        except SlackApiError as e:
            error = e.response.get("error") if e.response else str(e)
            if error == "invalid_auth" or error == "not_authed":
                raise SlackAuthError("Invalid Slack authentication", error=error, response=e.response)
            if error == "missing_scope":
                raise SlackPermissionError("Missing required Slack scope", error=error, response=e.response)
            if error == "ratelimited":
                raise SlackRateLimitError("Slack API rate limited", error=error, response=e.response)
            raise SlackServiceError(f"Slack API error: {error}", error=error, response=e.response)
        except Exception as e:
            raise SlackServiceError(f"Slack API request failed: {str(e)}")

    async def get_workspace_info(self) -> Dict[str, Any]:
        auth_info = await self.test_auth()
        return {
            "team_id": auth_info.get("team_id"),
            "team": auth_info.get("team"),
            "url": auth_info.get("url"),
            "bot_id": auth_info.get("bot_id"),
            "user_id": auth_info.get("user_id"),
            "connected": True,
        }

    async def get_channels(self, include_private: bool = True, limit: int = 1000) -> List[Dict[str, Any]]:
        channels: List[Dict[str, Any]] = []
        cursor: Optional[str] = None
        types = "public_channel,private_channel" if include_private else "public_channel"

        while True:
            try:
                kwargs: Dict[str, Any] = {
                    "types": types,
                    "limit": min(limit, 1000),
                }
                if cursor:
                    kwargs["cursor"] = cursor
                result = await self.client.conversations_list(**kwargs)
                page_channels = result.get("channels", []) or []
                channels.extend(page_channels)
                response_metadata = result.get("response_metadata") or {}
                next_cursor = response_metadata.get("next_cursor")
                if not next_cursor:
                    break
                cursor = next_cursor
            except SlackApiError as e:
                error = e.response.get("error") if e.response else str(e)
                if error == "invalid_auth" or error == "not_authed":
                    raise SlackAuthError("Invalid Slack authentication", error=error, response=e.response)
                if error == "missing_scope":
                    raise SlackPermissionError("Missing required Slack scope", error=error, response=e.response)
                if error == "ratelimited":
                    raise SlackRateLimitError("Slack API rate limited", error=error, response=e.response)
                raise SlackServiceError(f"Slack API error: {error}", error=error, response=e.response)
            except Exception as e:
                raise SlackServiceError(f"Slack API request failed: {str(e)}")

        return channels

    async def get_channel_history(self, channel_id: str, oldest: str = None) -> List[Dict[str, Any]]:
        try:
            result = await self.client.conversations_history(
                channel=channel_id,
                oldest=oldest,
                limit=1000,
            )
            return result.get("messages", []) or []
        except SlackApiError as e:
            error = e.response.get("error") if e.response else str(e)
            if error == "invalid_auth" or error == "not_authed":
                raise SlackAuthError("Invalid Slack authentication", error=error, response=e.response)
            if error == "missing_scope":
                raise SlackPermissionError("Missing required Slack scope", error=error, response=e.response)
            if error == "ratelimited":
                raise SlackRateLimitError("Slack API rate limited", error=error, response=e.response)
            raise SlackServiceError(f"Slack API error: {error}", error=error, response=e.response)
        except Exception as e:
            raise SlackServiceError(f"Slack API request failed: {str(e)}")

    async def get_thread_replies(self, channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
        try:
            result = await self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts,
            )
            return result.get("messages", []) or []
        except SlackApiError as e:
            error = e.response.get("error") if e.response else str(e)
            if error == "invalid_auth" or error == "not_authed":
                raise SlackAuthError("Invalid Slack authentication", error=error, response=e.response)
            if error == "missing_scope":
                raise SlackPermissionError("Missing required Slack scope", error=error, response=e.response)
            if error == "ratelimited":
                raise SlackRateLimitError("Slack API rate limited", error=error, response=e.response)
            raise SlackServiceError(f"Slack API error: {error}", error=error, response=e.response)
        except Exception as e:
            raise SlackServiceError(f"Slack API request failed: {str(e)}")

    async def reconstruct_threads(self, messages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        threads: Dict[str, List[Dict[str, Any]]] = {}
        for msg in messages:
            thread_ts = msg.get("thread_ts")
            if thread_ts:
                if thread_ts not in threads:
                    threads[thread_ts] = []
                threads[thread_ts].append(msg)
        return threads

    async def close(self):
        try:
            if hasattr(self.client, "session") and self.client.session:
                await self.client.session.close()
        except Exception:
            pass
