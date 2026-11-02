from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.db.base import Base


class Correction(Base):
    """User feedback on a generated report item ("wrong?" / "looks right")."""

    __tablename__ = "corrections"

    id = Column(Integer, primary_key=True, index=True)
    report_item_id = Column(Integer, ForeignKey("report_items.id"), nullable=False, index=True)
    verdict = Column(String, nullable=False)  # wrong | ok
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
