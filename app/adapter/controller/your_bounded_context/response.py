from dataclasses import dataclass
from typing import Any

from dataclass_mixins import DataclassMixin, snake_to_camel_case
from pendulum.datetime import DateTime

from app.adapter.controller.base import UserResponse
from app.core.your_bounded_context.domain.entity.your_aggregate import YourAggregate
from app.core.your_bounded_context.domain.repository import SearchResult
from app.core.your_bounded_context.domain.value_object.your_aggregate_value_object import (
    OperationHistoryType,
    YourAggregateStatus,
    YourValueObject,
)


@dataclass
class OperationHistoryDataResponse(DataclassMixin):
    field: str
    before: Any
    after: Any


@dataclass
class OperationHistoryResponse(DataclassMixin):
    type: OperationHistoryType
    data: list[OperationHistoryDataResponse]
    doer: UserResponse
    created_at: DateTime


@dataclass
class YourAggregateResponse(DataclassMixin):
    id: str
    your_value_object: YourValueObject
    status: YourAggregateStatus
    operation_histories: list[OperationHistoryResponse]
    creator: UserResponse
    created_at: DateTime
    updated_at: DateTime | None

    @classmethod
    def create_from_object(cls, obj: YourAggregate) -> "YourAggregateResponse":
        resp = super().create_from_object(obj)

        for h_idx, h in enumerate(obj.operation_histories):
            h_resp = OperationHistoryResponse.create_from_object(h)
            h_resp.doer = UserResponse.create_from_object(h.doer)
            if h.data is not None:
                for d_idx, d in enumerate(h.data):
                    d_resp = OperationHistoryDataResponse.create_from_object(d)
                    d_resp.field = snake_to_camel_case(d.field)
                    h_resp.data[d_idx] = d_resp
            else:
                h_resp.data = []
            resp.operation_histories[h_idx] = h_resp

        resp.creator = UserResponse.create_from_object(obj.creator)

        return resp


@dataclass
class SearchYourAggregatesResponse(DataclassMixin):
    total: int
    results: list[YourAggregateResponse]

    @classmethod
    def create_from_object(cls, obj: SearchResult) -> "SearchYourAggregatesResponse":
        return cls(
            total=obj.total,
            results=[YourAggregateResponse.create_from_object(i) for i in obj.results],
        )
