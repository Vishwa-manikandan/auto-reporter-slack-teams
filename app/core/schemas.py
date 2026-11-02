from pydantic import BaseModel
from typing import List, Optional, Any


class SourceReference(BaseModel):
    workspace_id: Optional[int] = None
    channel_id: Optional[int] = None
    message_id: Optional[str] = None
    thread_ts: Optional[str] = None


class ActionItem(BaseModel):
    description: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    status: Optional[str] = None
    source_references: List[SourceReference] = []


class Decision(BaseModel):
    description: str
    context: Optional[str] = None
    source_references: List[SourceReference] = []


class Blocker(BaseModel):
    description: str
    source_references: List[SourceReference] = []


class ProjectUpdate(BaseModel):
    project: str
    progress: Optional[str] = None
    source_references: List[SourceReference] = []


class FollowUp(BaseModel):
    description: str
    source_references: List[SourceReference] = []


class ReportStructure(BaseModel):
    executive_summary: Optional[str] = None
    decisions: List[Decision] = []
    action_items: List[ActionItem] = []
    blockers: List[Blocker] = []
    project_updates: List[ProjectUpdate] = []
    important_discussions: List[Any] = []
    follow_ups: List[FollowUp] = []
    source_references: List[SourceReference] = []
