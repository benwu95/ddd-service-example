from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.adapter.repository.orm import Base
from app.config import config


class DomainEventModel(Base):
    __tablename__ = "domain_event"
    __table_args__ = (
        Index(
            f"ix_{config.postgres_schema}_{__tablename__}_body",
            "body",
            postgresql_using="gin",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, autoincrement=True, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=True, index=True)
    body: Mapped[dict] = mapped_column(JSONB, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    span_id: Mapped[str] = mapped_column(String, nullable=True)
    parent_span_id: Mapped[str | None] = mapped_column(String, nullable=True)
    trace_id: Mapped[str] = mapped_column(String, nullable=True)
