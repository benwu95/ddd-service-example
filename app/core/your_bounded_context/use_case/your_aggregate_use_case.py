from app.core.ddd_base import User, event_bus, UseCaseBase
from app.core.your_bounded_context.domain.entity.your_aggregate import YourAggregate
from app.core.your_bounded_context.domain.value_object.your_aggregate_value_object import (
    YourValueObject,
)
from app.core.your_bounded_context.domain.repository import YourAggregateRepositoryInterface


class YourAggregateUseCase(UseCaseBase):
    def __init__(self, repository: YourAggregateRepositoryInterface):
        super().__init__()
        self.repository = repository

    async def _save(self, your_aggregate: YourAggregate):
        self._save_tracing(your_aggregate)
        await self.repository.save_your_aggregate(your_aggregate)
        await event_bus.publish_all(your_aggregate.all_events)

    async def create_your_aggregate(
        self,
        your_value_object: YourValueObject,
        creator: User
    ) -> str:
        your_aggregate = YourAggregate.create_your_aggregate(
            YourAggregate.generate_id(),
            your_value_object,
            creator
        )
        await self._save(your_aggregate)
        return your_aggregate.id

    async def delete_your_aggregate(self, your_aggregate_id: str, doer: User):
        your_aggregate = await self.repository.load_your_aggregate(your_aggregate_id)
        your_aggregate.delete_your_aggregate(doer)
        await self._save(your_aggregate)

    async def void_your_aggregate(self, your_aggregate_id: str, doer: User):
        your_aggregate = await self.repository.load_your_aggregate(your_aggregate_id)
        your_aggregate.void_your_aggregate(doer)
        await self._save(your_aggregate)

    async def update_your_aggregate(
        self,
        your_aggregate_id: str,
        your_value_object: YourValueObject,
        doer: User
    ):
        your_aggregate = await self.repository.load_your_aggregate(your_aggregate_id)
        your_aggregate.update_your_aggregate(
            your_value_object,
            doer
        )
        await self._save(your_aggregate)
