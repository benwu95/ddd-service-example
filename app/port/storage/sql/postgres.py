from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import config

engine = create_async_engine(
    config.sqlalchemy_database_url, pool_pre_ping=True, pool_recycle=600, pool_size=50
)
DB_Session = async_sessionmaker(bind=engine, autoflush=False, autocommit=False)
