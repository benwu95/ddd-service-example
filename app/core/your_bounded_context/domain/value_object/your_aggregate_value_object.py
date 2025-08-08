from dataclasses import dataclass
from enum import Enum
from typing import Any

from dataclass_mixins import DataclassMixin
from pendulum.datetime import DateTime

from app.core.ddd_base import User


class YourAggregateStatus(Enum):
    CREATED = "created"
    VOIDED = "voided"

    def __str__(self):
        return self.value


class OperationHistoryType(Enum):
    CREATED = "created"
    UPDATED = "updated"
    VOIDED = "voided"


@dataclass(frozen=True)
class OperationHistoryData(DataclassMixin):
    field: str
    before: Any
    after: Any


@dataclass(frozen=True)
class OperationHistory(DataclassMixin):
    type: OperationHistoryType
    data: list[OperationHistoryData]
    doer: User
    created_at: DateTime


@dataclass(frozen=True)
class YourValueObject(DataclassMixin):
    property_a: str
    property_b: int
