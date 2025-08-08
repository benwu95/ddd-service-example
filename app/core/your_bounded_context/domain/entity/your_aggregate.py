from pendulum.datetime import DateTime

from app.core.ddd_base import AggregateRoot, User
from app.core.your_bounded_context.domain.event import (
    YourAggregateCreated,
    YourAggregateDeleted,
    YourAggregateVoided,
    YourAggregateUpdated,
)
from app.core.your_bounded_context.domain.exception import (
    YourAggregateStatusNotMatched,
)
from app.core.your_bounded_context.domain.value_object.your_aggregate_value_object import (
    OperationHistory,
    OperationHistoryData,
    OperationHistoryType,
    YourAggregateStatus,
    YourValueObject,
)


class YourAggregate(AggregateRoot):
    def __init__(
        self,
        your_aggregate_id: str,
        your_value_object: YourValueObject,
        status: YourAggregateStatus,
        operation_histories: list[OperationHistory],
        creator: User,
        created_at: DateTime | None,
        updated_at: DateTime | None
    ):
        super().__init__()

        self._id = your_aggregate_id
        self._your_value_object = your_value_object
        self._status = status
        self._operation_histories = operation_histories
        self._creator = creator
        self._created_at = created_at
        self._updated_at = updated_at

    @property
    def id(self) -> str:
        return self._id

    @property
    def your_value_object(self) -> YourValueObject:
        return self._your_value_object

    @property
    def status(self) -> YourAggregateStatus:
        return self._status

    @property
    def operation_histories(self) -> list[OperationHistory]:
        return list(self._operation_histories)

    @property
    def creator(self) -> User:
        return self._creator

    @property
    def created_at(self) -> DateTime | None:
        return self._created_at

    @property
    def updated_at(self) -> DateTime | None:
        return self._updated_at

    @classmethod
    def create_your_aggregate(
        cls,
        your_aggregate_id: str,
        your_value_object: YourValueObject,
        creator: User
    ) -> 'YourAggregate':
        your_aggregate = cls(
            your_aggregate_id=your_aggregate_id,
            your_value_object=your_value_object,
            status=YourAggregateStatus.CREATED,
            operation_histories=[],
            creator=creator,
            created_at=None,
            updated_at=None
        )
        your_aggregate.add_operation_history(OperationHistoryType.CREATED, [], creator)
        your_aggregate.add_event(YourAggregateCreated(
            your_aggregate_id,
            your_value_object,
            creator
        ))
        return your_aggregate

    def mark_as_delete(self):
        self.is_delete = True

    def add_operation_history(
        self,
        operation_history_type: OperationHistoryType,
        operation_history_data: list[OperationHistoryData],
        doer: User
    ):
        if self.status == YourAggregateStatus.VOIDED:
            raise YourAggregateStatusNotMatched(f'Your Aggregate {self.id} is in Voided status')
        self._operation_histories.append(
            OperationHistory.create_strictly(
                type=operation_history_type,
                data=[d for d in operation_history_data if d.before != d.after],
                doer=doer,
                created_at=DateTime.now()
            )
        )

    def delete_your_aggregate(self, doer: User):
        self.mark_as_delete()
        self.add_event(YourAggregateDeleted(self.id, doer))

    def void_your_aggregate(self, doer: User):
        self.add_operation_history(
            OperationHistoryType.VOIDED,
            [
                OperationHistoryData('status', self._status.value, YourAggregateStatus.VOIDED.value)
            ],
            doer
        )

        self._status = YourAggregateStatus.VOIDED

        self.add_event(YourAggregateVoided(self.id, doer))

    def update_your_aggregate(
        self,
        your_value_object: YourValueObject,
        doer: User
    ):
        self.add_operation_history(
            OperationHistoryType.UPDATED,
            [
                OperationHistoryData('your_value_object', self._your_value_object.serialize(), your_value_object.serialize())
            ],
            doer
        )

        self._your_value_object = your_value_object

        self.add_event(YourAggregateUpdated(
            self.id,
            your_value_object,
            doer
        ))
