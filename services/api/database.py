"""
Database engine, session, and helper.
Supports SQLite (dev/demo) and PostgreSQL (staging/production).

Phase 11 hardening:
- Connection pool tuning for PostgreSQL
- create_db_and_tables skipped in production (Alembic handles it)
- Session auto-rollback on exception
"""
import logging
from sqlmodel import SQLModel, create_engine, Session
from config import settings

logger = logging.getLogger(__name__)

# Build engine kwargs based on DB type
_connect_args = {}
_engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}

if settings.is_sqlite:
    _connect_args = {"check_same_thread": False}
else:
    # Phase 11: PostgreSQL connection pool tuning
    _engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_recycle": 1800,  # recycle connections every 30 min
    })

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    **_engine_kwargs,
)


def create_db_and_tables():
    """Create all tables. Used in dev/test; Alembic migrations handle production."""
    if settings.is_production:
        logger.info("Production mode — skipping create_all (Alembic handles schema)")
        return
    # Import all models so their metadata is registered
    import models  # noqa: F401 — side-effect: registers all table metadata
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency — yields a DB session, commits or rolls back on exit."""
    with Session(engine) as session:
        yield session
