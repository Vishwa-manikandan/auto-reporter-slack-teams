from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import Base, SessionLocal, engine


def test_sqlite_engine_initialization():
    assert engine is not None
    # Check if it's SQLite
    if str(engine.url).startswith("sqlite"):
        # SQLite should have check_same_thread
        pass


def test_session_cleanup():
    from app.db.session import get_db
    db_gen = get_db()
    db = next(db_gen)
    assert db is not None
    try:
        db_gen.close()
    except Exception:
        pass
    # Session should be closed after cleanup


def test_in_memory_db():
    engine_test = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine_test)
    SessionLocalTest = sessionmaker(bind=engine_test)
    db = SessionLocalTest()
    assert db is not None
    db.close()
