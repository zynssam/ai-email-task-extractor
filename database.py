import os
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def set_rls_user(db: Session, user_id) -> None:
    """Activates PostgreSQL Row-Level Security (RLS) for the current DB session.

    Note: SET LOCAL does not support parameterized queries in PostgreSQL.
    Safety is guaranteed because user_id is always a validated UUID from the
    database lookup in get_current_user(), never raw user input.
    """
    import uuid as _uuid
    # Validate UUID format to prevent any injection (defense in depth)
    safe_id = str(_uuid.UUID(str(user_id)))
    db.execute(text(f"SET LOCAL app.current_user_id = '{safe_id}'"))
