# =============================================================================
# IPA Platform - Alembic Environment Configuration
# =============================================================================
# Sprint 72: Initial Alembic setup for Session User Association migration
#
# This file configures how Alembic runs migrations.
# It reads database URL from config.py and imports all models for autogenerate.
# =============================================================================

from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add backend directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import settings
from src.core.config import get_settings

# Import Base and all models for autogenerate support
from src.infrastructure.database.models.base import Base

# Import all models to ensure they're registered with Base.metadata
from src.infrastructure.database.models.user import User
from src.infrastructure.database.models.session import SessionModel, MessageModel, AttachmentModel

# Try to import other models (they may not exist yet)
try:
    from src.infrastructure.database.models.agent import AgentModel
except ImportError:
    pass

try:
    from src.infrastructure.database.models.workflow import Workflow
except ImportError:
    pass

try:
    from src.infrastructure.database.models.execution import Execution
except ImportError:
    pass

try:
    from src.infrastructure.database.models.thread import ThreadModel
except ImportError:
    pass

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from settings
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine,
    though an Engine is acceptable here as well. By skipping the Engine
    creation we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a
    connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
