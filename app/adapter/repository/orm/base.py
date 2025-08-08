from datetime import datetime

from sqlalchemy import UUID, DateTime, MetaData, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

from app.config import config


class Base(AsyncAttrs, DeclarativeBase):
    metadata = MetaData(schema=config.postgres_schema)


class BaseMixin:
    creator: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True, onupdate=func.now())


class ArchiveMixin:
    archive_id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    doer: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    event_name: Mapped[str | None] = mapped_column(String, nullable=True)
    event_span_id: Mapped[str | None] = mapped_column(String, nullable=True)
    event_trace_id: Mapped[str | None] = mapped_column(String, nullable=True)
