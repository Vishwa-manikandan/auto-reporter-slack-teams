from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)
    report_type = Column(String, nullable=False)  # daily or weekly
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    title = Column(String, nullable=True)
    executive_summary = Column(Text, nullable=True)
    status = Column(String, default="completed")  # completed, failed, pending
    generated_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ai_provider = Column(String, nullable=True)
    ai_model = Column(String, nullable=True)
    token_usage = Column(JSON, nullable=True)
    estimated_cost = Column(JSON, nullable=True)
    error_details = Column(Text, nullable=True)
    report_data = Column(JSON, nullable=True)

    workspace = relationship("Workspace")
    channel = relationship("Channel")
    items = relationship("ReportItem", back_populates="report", cascade="all, delete-orphan")
