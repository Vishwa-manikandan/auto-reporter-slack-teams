from sqlalchemy import create_engine, text
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
        db_gen.close()
    except Exception:
        raise
    mock_session.close.assert_called_once()


def test_in_memory_db():
    engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine_test)
    inspector_tables = engine_test.dialect.get_table_names(engine_test.connect())
    assert len(inspector_tables) > 0
    SessionLocalTest = sessionmaker(bind=engine_test)
    db = SessionLocalTest()
    user = User(slack_user_id="U_TEST", name="Test")
    db.add(user)
    db.commit()
    assert db.query(User).count() == 1
    db.close()
    engine_test.dispose()
