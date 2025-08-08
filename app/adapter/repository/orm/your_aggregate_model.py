from sqlalchemy import UUID, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.adapter.repository.orm import ArchiveMixin, Base, BaseMixin


class YourAggregateMixin(BaseMixin):
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    your_value_object: Mapped[dict] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=True)
    operation_histories: Mapped[list] = mapped_column(JSONB, nullable=True)


class YourAggregateModel(YourAggregateMixin, Base):
    __tablename__ = "your_aggregate"


class YourAggregateArchiveModel(ArchiveMixin, YourAggregateMixin, Base):
    __tablename__ = "your_aggregate_archive"
