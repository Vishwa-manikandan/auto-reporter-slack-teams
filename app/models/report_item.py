from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class ReportItem(Base):
    __tablename__ = "report_items"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"), nullable=False)
    category = Column(String, nullable=False)  # decision, action_item, blocker, bug, feature_request
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    assignee = Column(String, nullable=True)
    due_date = Column(String, nullable=True)
    status = Column(String, nullable=True)
    priority = Column(String, nullable=True)
    done = Column(Boolean, nullable=False, default=False, server_default="0")
    confidence = Column(Float, nullable=True)
    position = Column(Integer, nullable=False, default=0, server_default="0")
    source_references = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    report = relationship("Report", back_populates="items")
