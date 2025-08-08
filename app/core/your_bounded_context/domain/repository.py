import abc
from dataclasses import dataclass
from enum import Enum

from pendulum.datetime import DateTime

from app.core.your_bounded_context.domain.entity.your_aggregate import YourAggregate


class SearchDateField(Enum):
    CREATED_AT = 'created_at'


@dataclass(frozen=True)
class SearchResult:
    total: int
    results: list[YourAggregate]


class YourAggregateRepositoryInterface(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def load_your_aggregate(self, your_aggregate_id: str) -> YourAggregate:
        raise NotImplementedError

    @abc.abstractmethod
    async def save_your_aggregate(self, your_aggregate: YourAggregate):
        raise NotImplementedError

    # 搜尋參數如果是 string，盡量使用 `list[str] | None`，然後名稱記得用複數或集合名詞
    @abc.abstractmethod
    async def search_your_aggregates(
        self,
        ids: list[str] | None = None,
        statuses: list[str] | None = None,
        date_fields: list[str] | None = None,
        start_time: DateTime | None = None,
        end_time: DateTime | None = None,
        search_key_fields: list[str] | None = None,
        search_keys: list[str] | None = None,
        sort_by: list[str] | None = None,
        offset: int = 0,
        limit: int = 0
    ) -> SearchResult:
        pass
