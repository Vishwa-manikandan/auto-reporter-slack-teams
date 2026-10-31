from typing import List, Dict, Any
from datetime import datetime, timedelta
from app.services.ai_provider import get_ai_provider


class ReportGenerator:
    def __init__(self):
        self.ai_provider = get_ai_provider()
    
    async def generate_daily_report(self, messages: List[Dict[str, Any]], channel_name: str = "") -> Dict[str, Any]:
        summary = await self.ai_provider.summarize_messages(messages)
        action_items = await self.ai_provider.extract_action_items(messages)
        
        # Keyword detection
        keywords_found = self._detect_keywords(messages)
        
        report_content = f"""# Daily Status Report - {datetime.now().strftime('%Y-%m-%d')}

## Summary
{summary}

## Blocked Issues
{self._format_items(keywords_found.get('blocked', []))}

## Bugs
{self._format_items(keywords_found.get('bugs', []))}

## Action Items
{self._format_items(action_items)}

## Feature Requests
{self._format_items(keywords_found.get('features', []))}
"""
        
        return {
            "title": f"Daily Report - {datetime.now().strftime('%Y-%m-%d')}",
            "content": report_content,
            "type": "daily",
            "items": keywords_found
        }
    
    def _detect_keywords(self, messages: List[Dict[str, Any]]) -> Dict[str, List]:
        import re
        result = {"blocked": [], "bugs": [], "features": [], "other": []}
        
        patterns = {
            "blocked": [r'\bblock(ed|ing)?\b', r'\bstuck\b', r'\bwaiting on\b'],
            "bugs": [r'\bbug\b', r'\bcrash\b', r'\berror\b', r'\bbroken\b'],
            "features": [r'\bfeature request\b', r'\benhance\b', r'\badd\b.*feature\b']
        }
        
        for msg in messages:
            text = msg.get("text", "")
            for category, pats in patterns.items():
                for pattern in pats:
                    if re.search(pattern, text, re.IGNORECASE):
                        result[category].append({"text": text, "ts": msg.get("ts")})
                        break
        
        return result
    
    def _format_items(self, items: List[Dict]) -> str:
        if not items:
            return "- None\n"
        return "\n".join(f"- {item.get('text', '')[:100]}" for item in items) + "\n"
