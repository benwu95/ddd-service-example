from urllib.parse import quote_plus

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer
from testcontainers.rabbitmq import RabbitMqContainer

from app.adapter.repository.base import SessionProvider, _session_provider
from app.adapter.repository.orm import Base
from app.config import config
from app.package_instance import _message_queue_publisher
from packages.message_queue.rabbitmq_message_queue import RabbitMqPublisher


@pytest_asyncio.fixture(scope="session")
async def test_db_engine():
    with PostgresContainer("postgres:15.10") as postgres:
        db_url = postgres.get_connection_url(driver="psycopg")

        engine = create_async_engine(
            db_url,
            poolclass=NullPool,
        )

        async with engine.begin() as conn:
            await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {config.postgres_schema};"))
            await conn.run_sync(Base.metadata.create_all)

        yield engine

        await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_db_session(test_db_engine):
    DBSession = async_sessionmaker(bind=test_db_engine, autoflush=False, autocommit=False)
    async with DBSession() as session:
        yield session


@pytest.fixture(scope="function", autouse=True)
def mock_db_session_provider(test_db_session):

    class TestSessionProvider(SessionProvider):
        async def __aenter__(self):
            if self.session_count == 0:
                self.session = test_db_session
            self.session_count += 1
            return self

    _session_provider.set(TestSessionProvider())


@pytest.fixture(scope="session")
def test_rabbitmq():
    with RabbitMqContainer("rabbitmq:3.12.8") as rabbitmq:
        connection_params = rabbitmq.get_connection_params()
        rabbitmq_virtual_host = "/"
        amqp_url = f"amqp://guest:guest@{connection_params.host}:{connection_params.port}/{quote_plus(rabbitmq_virtual_host)}?heartbeat=120"
        yield amqp_url


@pytest.fixture(scope="session", autouse=True)
def mock_rabbitmq_publisher(test_rabbitmq):
    _message_queue_publisher.set(RabbitMqPublisher(test_rabbitmq, config.rabbitmq_exchange_name))
