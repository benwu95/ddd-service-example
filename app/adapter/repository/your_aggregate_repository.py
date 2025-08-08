import pendulum
from sqlalchemy import and_, or_
from sqlalchemy.orm import InstrumentedAttribute, load_only
from pendulum.datetime import DateTime

from app.adapter.repository.base import RepositoryBase, SearchKeyField
from app.adapter.repository.orm import (
    YourAggregateArchiveModel,
    YourAggregateModel,
)
from app.core.ddd_base import User
from app.core.your_bounded_context.domain.entity.your_aggregate import YourAggregate
from app.core.your_bounded_context.domain.repository import (
    SearchDateField,
    SearchResult,
    YourAggregateRepositoryInterface,
)
from app.core.your_bounded_context.domain.value_object.your_aggregate_value_object import (
    OperationHistory,
    YourAggregateStatus,
    YourValueObject,
)


class YourAggregateRepository(RepositoryBase, YourAggregateRepositoryInterface):
    @staticmethod
    def entity_name() -> str:
        return 'Your Aggregate'

    @staticmethod
    def model_class() -> type[YourAggregateModel]:
        return YourAggregateModel

    @staticmethod
    def archive_model_class() -> type[YourAggregateArchiveModel]:
        return YourAggregateArchiveModel

    @staticmethod
    def search_key_fields() -> dict[str, SearchKeyField]:
        return {
            'your_value_object_a': SearchKeyField(YourAggregateModel.your_value_object, json_path='$.property_a')
        }

    @staticmethod
    def sort_by_fields() -> dict[str, InstrumentedAttribute]:
        return {
            'created_at': YourAggregateModel.created_at
        }

    @staticmethod
    def model_to_entity(model: YourAggregateModel) -> YourAggregate:
        # if model field is JSON or JSONB and entity's property is:
        #   list of str/int/float: remember to create new list
        #   dict, list of dict: remember to use deepcopy
        return YourAggregate(
            model.id,
            YourValueObject.create(**model.your_value_object),
            YourAggregateStatus(model.status),
            [OperationHistory.create(**h) for h in model.operation_histories],
            User(**model.creator),
            pendulum.from_timestamp(model.created_at.timestamp()),
            pendulum.from_timestamp(model.updated_at.timestamp()) if model.updated_at else None,
        )

    async def load_your_aggregate(
        self,
        your_aggregate_id: str,
        lock: bool = True
    ) -> YourAggregate:
        obj = await self._load(your_aggregate_id, lock)
        return obj

    async def save_your_aggregate(self, your_aggregate: YourAggregate):
        model: YourAggregateModel | None = await self._get_model(your_aggregate.id)

        if not model:
            model = YourAggregateModel()
            model.id = your_aggregate.id
            model.creator = your_aggregate.creator.serialize()

        model.your_value_object = your_aggregate.your_value_object.serialize()
        model.status = your_aggregate.status.value
        model.operation_histories = [h.serialize() for h in your_aggregate.operation_histories]

        await self._save(your_aggregate, model)

    def _get_search_filters(
        self,
        ids: list[str] | None = None,
        statuses: list[str] | None = None,
        date_fields: list[str] | None = None,
        start_time: DateTime | None = None,
        end_time: DateTime | None = None
    ) -> list:
        filters = []
        # jsonb search example
        # - top-level key / array element
        #   - string
        #       filters.append(YourAggregateModel.str_array.has_key(str))
        #   - string list
        #       from sqlalchemy.dialects.postgresql import array
        #       filters.append(YourAggregateModel.str_array.has_any(array(str_array)))
        #   - number
        #       filters.append(YourAggregateModel.number_array.contains(f'{number}'))
        #   - number list
        #       from sqlalchemy import or_
        #       filters.append(or_(*[YourAggregateModel.number_array.contains(f'{n}') for n in number_array]))
        # - json path
        #     filters.append(YourAggregateModel.your_value_object.path_match(json_path))

        if ids is not None:
            filters.append(YourAggregateModel.id.in_(ids))
        if statuses is not None:
            filters.append(YourAggregateModel.status.in_(statuses))
        if date_fields is not None:
            date_filters = []
            for date_field in date_fields:
                _date_filters = []
                match date_field:
                    case SearchDateField.CREATED_AT.value:
                        if start_time is not None:
                            _date_filters.append(YourAggregateModel.created_at >= start_time)
                        if end_time is not None:
                            _date_filters.append(YourAggregateModel.created_at <= end_time)
                if _date_filters:
                    date_filters.append(and_(*_date_filters))
            if date_filters:
                filters.append(or_(*date_filters))

        return filters

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
        filters = self._get_search_filters(
            ids,
            statuses,
            date_fields,
            start_time,
            end_time
        )
        total, items = await self._search(
            filters,
            search_key_fields or [],
            search_keys,
            sort_by or [],
            offset,
            limit
        )
        return SearchResult(total, items)

    async def search_your_aggregate_models(
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
        limit: int = 0,
        load_fields: list[str] | None = None
    ) -> list[YourAggregateModel]:
        filters = self._get_search_filters(
            ids,
            statuses,
            date_fields,
            start_time,
            end_time
        )
        options = []
        if load_fields:
            options.append(load_only(*[getattr(YourAggregateModel, f) for f in load_fields], raiseload=True))
        _, results = await self._search(
            filters,
            search_key_fields or [],
            search_keys,
            sort_by or [],
            offset,
            limit,
            options,
            return_entity=False
        )
        return results
