from contextlib import contextmanager
from logging.config import fileConfig

from sqlalchemy import Connection, engine_from_config, pool, text

from alembic import context

from app.config import config as app_config

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
# https://github.com/sqlalchemy/alembic/issues/700
config.set_main_option("sqlalchemy.url", app_config.sqlalchemy_database_url.replace("%", "%%"))

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from app.adapter.repository.orm import Base

target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_name(name, type_, parent_names):
    if type_ == "schema":
        return name == app_config.postgres_schema
    else:
        return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


@contextmanager
def pg_advisory_lock(connection: Connection):
    if connection.dialect.name != "postgresql":
        yield
        return

    raw_query = f"select exists (select from information_schema.tables where table_schema = '{app_config.postgres_schema}' and table_name = 'alembic_version')"
    result = connection.execute(text(raw_query))
    if not result.scalar():
        yield
        return

    postgres_lock_key = f"'{app_config.postgres_schema}.alembic_version'::regclass::oid::int"
    try:
        context.execute(f"select pg_advisory_lock({postgres_lock_key})")
        yield
    finally:
        context.execute(f"select pg_advisory_unlock({postgres_lock_key})")


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

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
            version_table_schema=target_metadata.schema,
            include_schemas=True,
            include_name=include_name,
            transaction_per_migration=True,
        )

        # https://stackoverflow.com/questions/73068830/alembic-postgres-how-to-switch-to-another-schema
        context.execute(f"create schema if not exists {target_metadata.schema}")

        with context.begin_transaction():
            with pg_advisory_lock(connection):
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
