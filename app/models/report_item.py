from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.db.session import Base


class ReportItem(Base):
    __tablename__ = "report_items"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id"))
    item_type = Column(String)  # bug, blocked, action_item, feature_request
    title = Column(Text)
    assignee = Column(String)
    urgency = Column(String)
    message_ts = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
