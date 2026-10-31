"""Slack API client for fetching messages."""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackClient:
    """Client for interacting with Slack API."""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.environ.get("SLACK_BOT_TOKEN")
        if not self.token:
            raise ValueError("SLACK_BOT_TOKEN not provided")
        self.client = WebClient(token=self.token)
    
    def get_channel_history(self, channel_id: str, days: int = 1) -> List[Dict[str, Any]]:
        """Fetch message history from a channel for the past N days."""
        oldest = (datetime.now() - timedelta(days=days)).timestamp()
        messages = []
        
        try:
            result = self.client.conversations_history(
                channel=channel_id,
                oldest=str(oldest),
                limit=1000
            )
            messages.extend(result.get("messages", []))
            
            # Handle pagination if needed
            while result.get("has_more"):
                cursor = result.get("response_metadata", {}).get("next_cursor")
                if not cursor:
                    break
                result = self.client.conversations_history(
                    channel=channel_id,
                    oldest=str(oldest),
                    cursor=cursor,
                    limit=1000
                )
                messages.extend(result.get("messages", []))
                
        except SlackApiError as e:
            raise RuntimeError(f"Error fetching messages: {e.response['error']}")
        
        return messages
    
    def get_thread_replies(self, channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
        """Fetch replies in a thread."""
        try:
            result = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts
            )
            return result.get("messages", [])
        except SlackApiError as e:
            raise RuntimeError(f"Error fetching thread replies: {e.response['error']}")
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information."""
        try:
            result = self.client.users_info(user=user_id)
            return result.get("user")
        except SlackApiError:
            return None
