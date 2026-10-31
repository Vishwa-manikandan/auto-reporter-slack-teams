from typing import List, Dict, Any
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


class SlackService:
    def __init__(self, token: str):
        self.client = WebClient(token=token)
    
    async def get_channels(self) -> List[Dict[str, Any]]:
        try:
            result = self.client.conversations_list(types="public_channel,private_channel")
            return result.get("channels", [])
        except SlackApiError:
            return []
    
    async def get_channel_history(self, channel_id: str, oldest: str = None) -> List[Dict[str, Any]]:
        try:
            result = self.client.conversations_history(
                channel=channel_id,
                oldest=oldest,
                limit=1000
            )
            return result.get("messages", [])
        except SlackApiError:
            return []
    
    async def get_thread_replies(self, channel_id: str, thread_ts: str) -> List[Dict[str, Any]]:
        try:
            result = self.client.conversations_replies(
                channel=channel_id,
                ts=thread_ts
            )
            return result.get("messages", [])
        except SlackApiError:
            return []
    
    async def reconstruct_threads(self, messages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        threads = {}
        for msg in messages:
            thread_ts = msg.get("thread_ts")
            if thread_ts:
                if thread_ts not in threads:
                    threads[thread_ts] = []
                threads[thread_ts].append(msg)
        return threads
