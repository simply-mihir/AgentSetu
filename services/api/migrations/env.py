"""Alembic environment — reads DATABASE_URL from application config."""
from logging.config import fileConfig
from sqlalchemy import pool
from alembic import context
from sqlmodel import SQLModel

# Import all models so metadata is populated
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import models  # noqa: F401 — registers all table metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def get_url():
    from config import settings
    return settings.database_url


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import create_engine
    from config import settings

    connectable = create_engine(
        settings.database_url,
        poolclass=pool.NullPool,
        connect_args={"check_same_thread": False} if settings.is_sqlite else {},
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
