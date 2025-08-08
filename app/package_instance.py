from contextvars import ContextVar

from werkzeug.local import LocalProxy

from app.config import config
from app.logger import ServiceLogger
from packages.message_queue.rabbitmq_message_queue import RabbitMqPublisher


# global variables


# context variables
_message_queue_publisher = ContextVar('message_queue_publisher')
message_queue_publisher: RabbitMqPublisher = LocalProxy(_message_queue_publisher)  # type: ignore[assignment]


def set_message_queue_publisher():
    _message_queue_publisher.set(RabbitMqPublisher(
        config.amqp_url,
        config.rabbitmq_exchange_name
    ))
    message_queue_publisher.logger = ServiceLogger(message_queue_publisher.logger.name)


set_message_queue_publisher()
