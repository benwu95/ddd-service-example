from dataclasses import dataclass

from app.adapter.controller.base import RequestBase, SearchRequestBase
from app.core.your_bounded_context.domain.value_object.your_aggregate_value_object import (
    YourValueObject,
)


@dataclass
class GetYourAggregateRequest(RequestBase):
    id: str


@dataclass
class SearchYourAggregatesRequest(SearchRequestBase):
    ids: list[str] | None
    statuses: list[str] | None


@dataclass
class CreateYourAggregateRequest(RequestBase):
    your_value_object: YourValueObject


@dataclass
class UpdateYourAggregateRequest(RequestBase):
    id: str
    your_value_object: YourValueObject


@dataclass
class DeleteYourAggregateRequest(RequestBase):
    id: str


@dataclass
class VoidYourAggregateRequest(RequestBase):
    id: str
