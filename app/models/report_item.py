from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class ReportItem(Base):
    __tablename__ = "report_items"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    category = Column(String, nullable=False)  # decision, action_item, blocker, project_update, discussion, follow_up
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    assignee = Column(String, nullable=True)
    due_date = Column(String, nullable=True)
    status = Column(String, nullable=True)
    priority = Column(String, nullable=True)
    source_references = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    report = relationship("Report", back_populates="items")
