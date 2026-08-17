import os
from typing import Generator
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://app_worker:app_secure_pass_123@localhost:5432/email_tasks"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def set_rls_user(db: Session, user_id: str) -> None:
    """Activates PostgreSQL Row-Level Security (RLS) for the current DB session."""
    db.execute(text("SET LOCAL app.current_user_id = :user_id"), {"user_id": str(user_id)})
