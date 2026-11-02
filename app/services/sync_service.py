import asyncio
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from app.models.channel import Channel
from app.models.message import Message
from app.models.sync_state import SyncState
from app.models.workspace import Workspace
from app.services.slack_service import SlackService, SlackServiceFactory, SlackRateLimitError, SlackAuthError


class SyncService:
    def __init__(self, db: Session):
        self.db = db

    async def incremental_sync(self, channel_id: int, last_sync_ts: str = None) -> Dict[str, Any]:
        channel = self.db.query(Channel).filter(Channel.id == channel_id).first()
        if not channel:
            return {"synced_count": 0, "new_messages": 0, "status": "failed", "error": "Channel not found"}

        workspace = self.db.query(Workspace).filter(Workspace.id == channel.workspace_id).first()
        if not workspace or not workspace.access_token:
            return {"synced_count": 0, "new_messages": 0, "status": "failed", "error": "Workspace not connected"}

        try:
            service = SlackServiceFactory.from_workspace(workspace)
        except Exception as e:
            return {"synced_count": 0, "new_messages": 0, "status": "failed", "error": str(e)}

        sync_state = self.db.query(SyncState).filter(SyncState.channel_id == channel_id).first()
        oldest = last_sync_ts or (sync_state.last_sync_ts if sync_state else None)

        try:
            messages = await self._fetch_channel_messages_with_retries(service, channel.slack_channel_id, oldest)
        except Exception as e:
            return {"synced_count": 0, "new_messages": 0, "status": "failed", "error": str(e)}

        try:
            new_count, updated_count = await self.store_messages(channel_id, messages)
        except Exception as e:
            self.db.rollback()
            return {"synced_count": 0, "new_messages": 0, "status": "failed", "error": str(e)}

        try:
            if not sync_state:
                sync_state = SyncState(channel_id=channel_id)
                self.db.add(sync_state)
            if messages:
                # Update checkpoint to latest ts
                latest_ts = messages[0].get("ts") if messages else sync_state.last_sync_ts
                sync_state.last_sync_ts = latest_ts
            sync_state.synced_at = datetime.utcnow()
            self.db.commit()
        except Exception:
            self.db.rollback()

        try:
            await service.close()
        except Exception:
            pass

        return {
            "synced_count": len(messages),
            "new_messages": new_count,
            "updated_messages": updated_count,
            "status": "completed",
        }

    async def _fetch_channel_messages_with_retries(self, service: SlackService, channel_id: str, oldest: str = None, max_retries: int = 3):
        retries = 0
        while retries < max_retries:
            try:
                messages = await service.get_channel_history(channel_id, oldest=oldest)
                # Also fetch thread replies for messages with threads
                all_messages = []
                for msg in messages:
                    all_messages.append(msg)
                    thread_ts = msg.get("thread_ts") or msg.get("ts")
                    if msg.get("reply_count", 0) > 0 or msg.get("thread_ts"):
                        try:
                            replies = await service.get_thread_replies(channel_id, thread_ts)
                            # Avoid duplicating parent
                            for r in replies:
                                if r.get("ts") != thread_ts or len(all_messages) == 0:  # include replies
                                    pass
                            all_messages.extend([r for r in replies if r.get("ts") != thread_ts])
                        except Exception:
                            pass
                return all_messages
            except SlackRateLimitError:
                retries += 1
                await asyncio.sleep(2 ** retries)
                continue
            except (SlackAuthError,):
                raise
            except Exception:
                retries += 1
                await asyncio.sleep(1)
                continue
        raise Exception("Failed to fetch messages after retries")

    async def deduplicate_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for msg in messages:
            ts = msg.get("ts")
            if ts and ts not in seen:
                seen.add(ts)
                unique.append(msg)
        return unique

    async def store_messages(self, channel_id: int, messages: List[Dict[str, Any]]):
        messages = await self.deduplicate_messages(messages)
        new_count = 0
        updated_count = 0
        for msg in messages:
            ts = msg.get("ts")
            if not ts:
                continue
            existing = self.db.query(Message).filter(
                Message.channel_id == channel_id,
                Message.slack_message_ts == ts,
            ).first()
            if existing:
                # Update if changed
                existing.text = msg.get("text") or existing.text
                existing.message_data = msg
                existing.thread_ts = msg.get("thread_ts") or existing.thread_ts
                updated_count += 1
            else:
                message = Message(
                    channel_id=channel_id,
                    slack_message_ts=ts,
                    text=msg.get("text"),
                    thread_ts=msg.get("thread_ts"),
                    message_data=msg,
                )
                self.db.add(message)
                new_count += 1
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return new_count, updated_count
