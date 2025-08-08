import app.core.your_bounded_context.domain.event as your_aggregate_event
from app.adapter.event_handler.helper import EventHandlerHelper
from app.adapter.repository.your_aggregate_repository import YourAggregateRepository
from app.core.ddd_base import event_bus
from app.core.your_bounded_context.domain.value_object.your_aggregate_value_object import (
    YourAggregateStatus,
    YourValueObject,
)
from app.core.your_bounded_context.use_case.your_aggregate_use_case import (
    YourAggregateUseCase,
)
from app.package_instance import message_queue_publisher
from app.trace import get_trace_id
from packages.message_queue import QueueMessage
from packages.message_queue.type import (
    RoutingKey,
    YourAggregateServiceFuntion,
    YourAggregateVoided,
)


class YourAggregateEventHandlerHelper(EventHandlerHelper):
    def __init__(self):
        super().__init__()

        self.repository = YourAggregateRepository(self.session_provider)
        self.use_case = YourAggregateUseCase(self.repository)
        self.add_use_case(self.use_case)


helper = YourAggregateEventHandlerHelper()


class YourAggregateEventHandler:
    @staticmethod
    @event_bus.subscribe(event_types=[your_aggregate_event.YourAggregateCreated])
    @helper.connect_db_session()
    async def handle_your_aggregate_created(
        event: your_aggregate_event.YourAggregateCreated,
    ):
        # do something with use case or package
        if event.your_value_object is not None:
            # 測試 session 新增 model 的行為
            v = YourValueObject(
                event.your_value_object.property_a + "_test_event_handler",
                event.your_value_object.property_b,
            )
            await helper.use_case.update_your_aggregate(event.your_aggregate_id, v, event.doer)

    @staticmethod
    @event_bus.subscribe(event_types=[your_aggregate_event.YourAggregateVoided])
    @helper.connect_db_session()
    async def handle_your_aggregate_voided(
        event: your_aggregate_event.YourAggregateVoided,
    ):
        your_aggregate = await helper.repository.load_your_aggregate(event.your_aggregate_id, lock=False)
        if your_aggregate.status == YourAggregateStatus.VOIDED:
            payload = YourAggregateVoided(event.your_aggregate_id)
            message_queue_publisher.push_message(
                RoutingKey.YOUR_AGGREGATE_SERVICE.value,
                QueueMessage(
                    get_trace_id(),
                    YourAggregateServiceFuntion.YOUR_AGGREGATE_VOIDED,
                    [payload],
                ),
            )
