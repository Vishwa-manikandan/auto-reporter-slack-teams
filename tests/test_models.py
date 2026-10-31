from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models import User, Workspace, Channel, Message, Thread, Report, ReportItem, SyncState


def test_models_creation():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    # Create instances
    user = User(slack_user_id="U123", name="Test User")
    workspace = Workspace(slack_team_id="T123", name="Test Team")
    channel = Channel(slack_channel_id="C123", name="test")
    
    db.add_all([user, workspace, channel])
    db.commit()
    
    assert db.query(User).count() == 1
    assert db.query(Workspace).count() == 1
    assert db.query(Channel).count() == 1
    
    db.close()
