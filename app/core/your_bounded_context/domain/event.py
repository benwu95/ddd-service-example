from dataclasses import dataclass

from app.core.ddd_base import User, DomainEvent
from app.core.your_bounded_context.domain.value_object.your_aggregate_value_object import (
    YourValueObject,
)


@dataclass(frozen=True)
class YourAggregateCreated(DomainEvent):
    your_aggregate_id: str
    your_value_object: YourValueObject
    doer: User


@dataclass(frozen=True)
class YourAggregateDeleted(DomainEvent):
    your_aggregate_id: str
    doer: User


@dataclass(frozen=True)
class YourAggregateVoided(DomainEvent):
    your_aggregate_id: str
    doer: User


@dataclass(frozen=True)
class YourAggregateUpdated(DomainEvent):
    your_aggregate_id: str
    your_value_object: YourValueObject
    doer: User
