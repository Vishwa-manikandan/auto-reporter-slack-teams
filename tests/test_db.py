from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock, patch

from app.db.session import Base, engine
from app.models import User


def test_sqlite_engine_initialization():
    assert engine is not None
    assert str(engine.url).startswith("sqlite")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


@patch("app.db.session.SessionLocal")
def test_session_cleanup(mock_session_local):
    from app.db.session import get_db
    mock_session = MagicMock()
    mock_session_local.return_value = mock_session
    db_gen = get_db()
    db = next(db_gen)
    assert db == mock_session
    try:
        next(db_gen)
    except StopIteration:
        pass
    mock_session.close.assert_called_once()


def test_in_memory_db():
    engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    try:
        Base.metadata.create_all(bind=engine_test)
        inspector = inspect(engine_test)
        table_names = inspector.get_table_names()
        assert len(table_names) > 0
        SessionLocalTest = sessionmaker(bind=engine_test)
        db = SessionLocalTest()
        try:
            user = User(slack_user_id="U_TEST", name="Test")
            db.add(user)
            db.commit()
            assert db.query(User).count() == 1
        finally:
            db.close()
    finally:
        engine_test.dispose()
