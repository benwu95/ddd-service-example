from enum import Enum

from app.config import config
from app.core.ddd_base import User
from app.logger import ServiceLogger
from app.port.message_queue.your_exchange.payload import ExamplePayload
from app.trace import set_trace_id
from packages.message_queue import QueueMessage

logger = ServiceLogger(__name__)


class Function(Enum):
    EXAMPLE = "example"


def your_exchange_handler(data: QueueMessage):
    set_trace_id(trace_id=data.trace_id)

    match data.function_name:
        case Function.EXAMPLE.value:
            example(data)
        case _:
            logger.warning("function name %s not found", data.function_name)
    logger.info("process complete")


def example(data: QueueMessage):
    trace_id = data.trace_id
    doer = User(name=config.rabbitmq_consumer_name)

    for d in data.data:
        try:
            p = ExamplePayload.create(**d)
        except Exception as e:
            logger.exception(e)
