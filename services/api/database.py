"""
Database engine, session, and helper.
Supports SQLite (dev/demo) and PostgreSQL (staging/production).
"""
from sqlmodel import SQLModel, create_engine, Session
from config import settings

# Build engine kwargs based on DB type
_connect_args = {}
if settings.is_sqlite:
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    echo=False,
    # Pool settings for PostgreSQL; SQLite ignores these
    pool_pre_ping=True,
)


def create_db_and_tables():
    """Create all tables. Used in dev/test; migrations handle production."""
    # Import all models so their metadata is registered
    import models  # noqa: F401 — side-effect: registers all table metadata
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency — yields a DB session, commits or rolls back on exit."""
    with Session(engine) as session:
        yield session
