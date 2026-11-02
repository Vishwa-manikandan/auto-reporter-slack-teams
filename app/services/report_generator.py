import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.message import Message
from app.services.ai_provider import AIProviderFactory, AIProviderError


class ReportGenerator:
    def __init__(self, db: Session, provider: Optional[str] = None):
        self.db = db
        self.ai = AIProviderFactory.create(provider)

    def prepare_messages_for_analysis(self, channel_id: int, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        messages = (
            self.db.query(Message)
            .filter(Message.channel_id == channel_id)
            .filter(Message.ts >= start_time.timestamp() if False else True)  # flexible
            .order_by(Message.ts.asc())
            .all()
        )
        # Filter by time if ts is datetime-like
        result = []
        for m in messages:
            try:
                m_time = datetime.fromtimestamp(float(m.ts)) if hasattr(m.ts, '__float__') or isinstance(m.ts, (int, float, str)) and str(m.ts).replace('.', '').isdigit() else getattr(m, 'created_at', None)
                if m_time and isinstance(m_time, datetime):
                    if m_time < start_time or m_time >= end_time:
                        continue
            except Exception:
                pass
            result.append({
                "id": m.slack_message_id or getattr(m, 'id'),
                "ts": m.ts,
                "user_id": m.user_id,
                "text": m.text or "",
                "thread_ts": m.thread_ts,
                "channel_id": m.channel_id,
            })
        return result

    async def generate_daily_report(self, channel_id: int) -> Dict[str, Any]:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        messages = self.prepare_messages_for_analysis(channel_id, start_time, end_time)
        prompt = """You are an expert Slack report generator. Analyze the messages and return a JSON object with keys: executive_summary, decisions, action_items, blockers, project_updates, important_discussions, follow_ups, source_references. Only include items with evidence from messages. Do not invent facts."""
        try:
            content = await self.ai.generate(messages, prompt)
            data = json.loads(content)
            return {
                "type": "daily",
                "period": {"start": start_time.isoformat(), "end": end_time.isoformat()},
                "channel_id": channel_id,
                "message_count": len(messages),
                **data
            }
        except AIProviderError as e:
            raise Exception(f"AI generation failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Report generation failed: {str(e)}")

    async def generate_weekly_report(self, channel_id: int) -> Dict[str, Any]:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=7)
        messages = self.prepare_messages_for_analysis(channel_id, start_time, end_time)
        prompt = """You are an expert Slack report generator. Analyze messages from the past week and return a JSON object with keys: executive_summary, decisions, action_items, blockers, project_updates, important_discussions, follow_ups, source_references. Focus on themes and trends. Only include items with evidence."""
        try:
            content = await self.ai.generate(messages, prompt)
            data = json.loads(content)
            return {
                "type": "weekly",
                "period": {"start": start_time.isoformat(), "end": end_time.isoformat()},
                "channel_id": channel_id,
                "message_count": len(messages),
                **data
            }
        except AIProviderError as e:
            raise Exception(f"AI generation failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Report generation failed: {str(e)}")
