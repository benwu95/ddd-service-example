import pytest
import pytest_asyncio
import sqlalchemy as sa

from app.adapter.controller.your_bounded_context.request import (
    GetYourAggregateRequest,
    CreateYourAggregateRequest,
    SearchYourAggregatesRequest,
    UpdateYourAggregateRequest,
    DeleteYourAggregateRequest,
    VoidYourAggregateRequest,
)
from app.adapter.controller.your_bounded_context.your_aggregate_controller import YourAggregateController
from app.adapter.repository.base import DomainEventModel
from app.adapter.repository.your_aggregate_repository import YourAggregateModel
from app.core.your_bounded_context.domain.value_object.your_aggregate_value_object import (
    OperationHistoryType,
    YourAggregateStatus,
)
from packages.message_queue.message_queue import QueueMessage
from packages.message_queue.type import (
    RoutingKey,
    YourAggregateServiceFuntion,
    YourAggregateVoided,
)
from tests.utils.rabbitmq_test_helper import TemporaryQueueWatcher

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(autouse=False, scope='function')
async def created_your_aggregate_id():
    controller = YourAggregateController()
    create_request = CreateYourAggregateRequest.create_strictly(
        your_value_object={
            'property_a': 'value1',
            'property_b': 123
        },
        doer={'id': 'test-user-id'}
    )
    your_aggregate_id = await controller.create_your_aggregate(create_request)
    return your_aggregate_id


async def test_create_your_aggregate(test_db_session, created_your_aggregate_id):
    your_value_object = {
        'property_a': 'value1',
        'property_b': 123
    }

    your_aggregate: YourAggregateModel = (await test_db_session.execute(sa.select(YourAggregateModel).where(YourAggregateModel.id == created_your_aggregate_id))).scalars().one()
    domain_event: DomainEventModel = (await test_db_session.execute(sa.select(DomainEventModel).order_by(DomainEventModel.created_at.desc()))).scalars().first()

    assert your_aggregate.id == created_your_aggregate_id
    assert your_aggregate.status == YourAggregateStatus.CREATED.value
    # event handler 有做 update
    assert your_aggregate.your_value_object['property_a'] == your_value_object['property_a'] + '_test_event_handler'
    assert your_aggregate.your_value_object['property_b'] == your_value_object['property_b']
    assert your_aggregate.operation_histories[-1]['type'] == OperationHistoryType.UPDATED.value
    assert domain_event.name == 'YourAggregateUpdated'


async def test_get_your_aggregate(created_your_aggregate_id):
    controller = YourAggregateController()
    get_request = GetYourAggregateRequest.create_strictly(id=created_your_aggregate_id)
    your_aggregate = await controller.get_your_aggregate(get_request)

    assert your_aggregate.id == created_your_aggregate_id


async def test_search_your_aggregates_by_search_key_fields(created_your_aggregate_id):
    controller = YourAggregateController()
    request = SearchYourAggregatesRequest.create_strictly(
        ids=[created_your_aggregate_id],
        search_key_fields=['yourValueObjectA'],
        search_keys=['value1'],
        offset=0,
        limit=100,
        doer={'id': 'test-user-id'}
    )
    your_aggregates = await controller.search_your_aggregates(request)

    assert your_aggregates.total == 1
    assert your_aggregates.results[0].id == created_your_aggregate_id

    request = SearchYourAggregatesRequest.create_strictly(
        ids=[created_your_aggregate_id],
        search_keys=['value2'],
        search_key_fields=['yourValueObjectA'],
        offset=0,
        limit=100,
        doer={'id': 'test-user-id'}
    )
    your_aggregates = await controller.search_your_aggregates(request)

    assert your_aggregates.total == 0


async def test_search_your_aggregates_by_search_key_fields_startswith(created_your_aggregate_id):
    controller = YourAggregateController()
    request = SearchYourAggregatesRequest.create_strictly(
        ids=[created_your_aggregate_id],
        search_key_fields=['starts:yourValueObjectA'],
        search_keys=['value1'],
        offset=0,
        limit=100,
        doer={'id': 'test-user-id'}
    )
    your_aggregates = await controller.search_your_aggregates(request)

    assert your_aggregates.total == 1
    assert your_aggregates.results[0].id == created_your_aggregate_id

    request = SearchYourAggregatesRequest.create_strictly(
        ids=[created_your_aggregate_id],
        search_keys=['value2'],
        search_key_fields=['starts:yourValueObjectA'],
        offset=0,
        limit=100,
        doer={'id': 'test-user-id'}
    )
    your_aggregates = await controller.search_your_aggregates(request)

    assert your_aggregates.total == 0


async def test_search_your_aggregates_by_search_key_fields_endswith(created_your_aggregate_id):
    controller = YourAggregateController()
    request = SearchYourAggregatesRequest.create_strictly(
        ids=[created_your_aggregate_id],
        search_key_fields=['ends:yourValueObjectA'],
        search_keys=['_test_event_handler'],
        offset=0,
        limit=100,
        doer={'id': 'test-user-id'}
    )
    your_aggregates = await controller.search_your_aggregates(request)

    assert your_aggregates.total == 1
    assert your_aggregates.results[0].id == created_your_aggregate_id

    request = SearchYourAggregatesRequest.create_strictly(
        ids=[created_your_aggregate_id],
        search_key_fields=['ends:yourValueObjectA'],
        search_keys=['value1'],
        offset=0,
        limit=100,
        doer={'id': 'test-user-id'}
    )
    your_aggregates = await controller.search_your_aggregates(request)

    assert your_aggregates.total == 0


async def test_search_your_aggregates_by_search_key_fields_equals(created_your_aggregate_id):
    controller = YourAggregateController()
    request = SearchYourAggregatesRequest.create_strictly(
        ids=[created_your_aggregate_id],
        search_key_fields=['equals:yourValueObjectA'],
        search_keys=['value1_test_event_handler'],
        offset=0,
        limit=100,
        doer={'id': 'test-user-id'}
    )
    your_aggregates = await controller.search_your_aggregates(request)

    assert your_aggregates.total == 1
    assert your_aggregates.results[0].id == created_your_aggregate_id

    request = SearchYourAggregatesRequest.create_strictly(
        ids=[created_your_aggregate_id],
        search_keys=['value1'],
        search_key_fields=['equals:yourValueObjectA'],
        offset=0,
        limit=100,
        doer={'id': 'test-user-id'}
    )
    your_aggregates = await controller.search_your_aggregates(request)

    assert your_aggregates.total == 0


async def test_update_your_aggregate(test_db_session, created_your_aggregate_id):
    your_value_object = {
        'property_a': 'value2',
        'property_b': 321
    }

    controller = YourAggregateController()
    request = UpdateYourAggregateRequest.create_strictly(
        id=created_your_aggregate_id,
        your_value_object=your_value_object,
        doer={'id': 'test-user-id'}
    )
    your_aggregate_id = await controller.update_your_aggregate(request)

    your_aggregate: YourAggregateModel = (await test_db_session.execute(sa.select(YourAggregateModel).where(YourAggregateModel.id == your_aggregate_id))).scalars().one()
    domain_event: DomainEventModel = (await test_db_session.execute(sa.select(DomainEventModel).order_by(DomainEventModel.created_at.desc()))).scalars().first()

    assert your_aggregate.id == created_your_aggregate_id
    assert your_aggregate.status == YourAggregateStatus.CREATED.value
    assert your_aggregate.your_value_object['property_a'] == your_value_object['property_a']
    assert your_aggregate.your_value_object['property_b'] == your_value_object['property_b']
    assert your_aggregate.operation_histories[-1]['type'] == OperationHistoryType.UPDATED.value
    assert domain_event.name == 'YourAggregateUpdated'


async def test_delete_your_aggregate(test_db_session, created_your_aggregate_id):
    controller = YourAggregateController()
    request = DeleteYourAggregateRequest.create_strictly(
        id=created_your_aggregate_id,
        doer={'id': 'test-user-id'}
    )
    your_aggregate_id = await controller.delete_your_aggregate(request)

    your_aggregate: YourAggregateModel = (await test_db_session.execute(sa.select(YourAggregateModel).where(YourAggregateModel.id == your_aggregate_id))).scalars().one_or_none()
    domain_event: DomainEventModel = (await test_db_session.execute(sa.select(DomainEventModel).order_by(DomainEventModel.created_at.desc()))).scalars().first()

    assert your_aggregate is None
    assert domain_event.name == 'YourAggregateDeleted'


async def test_void_your_aggregate(test_db_session, test_rabbitmq, created_your_aggregate_id):
    queue_watcher = TemporaryQueueWatcher(test_rabbitmq, RoutingKey.YOUR_AGGREGATE_SERVICE.value)

    controller = YourAggregateController()
    request = VoidYourAggregateRequest.create_strictly(
        id=created_your_aggregate_id,
        doer={'id': 'test-user-id'}
    )
    your_aggregate_id = await controller.void_your_aggregate(request)

    your_aggregate: YourAggregateModel = (await test_db_session.execute(sa.select(YourAggregateModel).where(YourAggregateModel.id == your_aggregate_id))).scalars().one()
    domain_event: DomainEventModel = (await test_db_session.execute(sa.select(DomainEventModel).order_by(DomainEventModel.created_at.desc()))).scalars().first()

    assert your_aggregate.status == YourAggregateStatus.VOIDED.value
    assert your_aggregate.operation_histories[-1]['type'] == OperationHistoryType.VOIDED.value
    assert domain_event.name == 'YourAggregateVoided'

    queue_watcher.assert_message_published(QueueMessage('test-trace-id', YourAggregateServiceFuntion.YOUR_AGGREGATE_VOIDED, [YourAggregateVoided(your_aggregate_id)]))
    queue_watcher.close()
