"""Report generation logic."""

from datetime import datetime
from typing import Dict, Any, List

from .keywords import DetectedItem


class ReportGenerator:
    """Generates structured markdown reports."""
    
    def generate(self, aggregated_data: Dict[str, Any], channel_name: str = "channel") -> str:
        """Generate markdown report."""
        report_date = datetime.now().strftime("%b %d, %Y")
        detected = aggregated_data.get("detected_items", {})
        
        lines = []
        lines.append(f"## Daily Status Report – {report_date}")
        lines.append("")
        
        # Blocked Issues
        blocked = detected.get("blocked", [])
        if blocked:
            lines.append("### Blocked Issues:")
            for i, item in enumerate(blocked, 1):
                urgency_tag = f"[{item.urgency.title()} Priority]" if item.urgency == "high" else f"[{item.urgency.title()}]"
                owner = f" -> @{item.user}" if item.user else ""
                mentions = ""
                if item.mentions:
                    mentions = f" | Mentions: {', '.join('@' + m for m in item.mentions)}"
                lines.append(f"{i}. {urgency_tag} {self._clean_text(item.text)}{owner}{mentions}")
            lines.append("")
        else:
            lines.append("### Blocked Issues:")
            lines.append("*No blockers detected.*")
            lines.append("")
        
        # Bugs
        bugs = detected.get("bugs", [])
        if bugs:
            lines.append("### Bugs:")
            for i, item in enumerate(bugs, 1):
                urgency_tag = f"[{item.urgency.title()} Priority]" if item.urgency == "high" else ""
                owner = f" -> @{item.user}" if item.user else ""
                lines.append(f"{i}. {urgency_tag} {self._clean_text(item.text)}{owner}")
            lines.append("")
        
        # Action Items
        actions = detected.get("action_items", [])
        if actions:
            lines.append("### Action Items:")
            for i, item in enumerate(actions, 1):
                owner = f" -> @{item.user}" if item.user else ""
                if item.mentions and not item.user:
                    owner = f" → {', '.join('@' + m for m in item.mentions)}"
                lines.append(f"- [ ] {self._clean_text(item.text)}{owner}")
            lines.append("")
        else:
            lines.append("### Action Items:")
            lines.append("*No action items detected.*")
            lines.append("")
        
        # Feature Requests
        features = detected.get("feature_requests", [])
        if features:
            lines.append("### Feature Requests:")
            for i, item in enumerate(features, 1):
                lines.append(f"{i}. {self._clean_text(item.text)}")
            lines.append("")
        
        # Summary
        lines.append("---")
        lines.append(f"> Generated from #{channel_name} • {aggregated_data.get('total_messages', 0)} messages analyzed")
        lines.append(f"> Sent at {datetime.now().strftime('%I:%M %p UTC')}")
        
        return "\n".join(lines)
    
    def _clean_text(self, text: str) -> str:
        """Clean text for better readability."""
        # Remove Slack user mentions formatting for display
        import re
        text = re.sub(r'<@([A-Z0-9]+)>', r'@\1', text)
        text = re.sub(r'<#([A-Z0-9]+)\|([^>]+)>', r'#\2', text)
        text = re.sub(r'<([^>|]+)>', r'\1', text)
        # Truncate very long messages
        if len(text) > 200:
            text = text[:197] + "..."
        return text
