"""Message aggregation logic."""

from typing import List, Dict, Any
from collections import defaultdict

from .keywords import DetectedItem, KeywordDetector


class MessageAggregator:
    """Aggregates messages by thread and context."""
    
    def __init__(self):
        self.detector = KeywordDetector()
    
    def aggregate(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate messages into structured report data."""
        # Group by thread
        threads = defaultdict(list)
        standalone = []
        
        for msg in messages:
            # Skip bot messages and system messages
            if msg.get("subtype") in ["bot_message", "channel_join", "channel_leave"]:
                continue
            
            thread_ts = msg.get("thread_ts")
            if thread_ts and thread_ts != msg.get("ts"):
                threads[thread_ts].append(msg)
            elif thread_ts == msg.get("ts"):
                # Thread parent
                threads[thread_ts].append(msg)
            else:
                standalone.append(msg)
        
        # Detect items
        all_items = []
        for msg in messages:
            if msg.get("subtype") in ["bot_message", "channel_join", "channel_leave"]:
                continue
            items = self.detector.detect(msg)
            all_items.extend(items)
        
        # Group items by type
        grouped = {
            "bugs": [],
            "blocked": [],
            "action_items": [],
            "feature_requests": [],
            "other": [],
        }
        
        for item in all_items:
            if item.type == "bug":
                grouped["bugs"].append(item)
            elif item.type == "blocked":
                grouped["blocked"].append(item)
            elif item.type == "action_item":
                grouped["action_items"].append(item)
            elif item.type == "feature_request":
                grouped["feature_requests"].append(item)
            else:
                grouped["other"].append(item)
        
        return {
            "messages": messages,
            "threads": dict(threads),
            "standalone": standalone,
            "detected_items": grouped,
            "total_messages": len(messages),
        }
