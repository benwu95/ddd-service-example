import abc
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Self

import pika
from dataclass_mixins import DataclassMixin
from pendulum.datetime import DateTime
from pika.adapters.blocking_connection import BlockingChannel
from pika.adapters.utils import connection_workflow
from pika.exchange_type import ExchangeType


class OperationType(Enum):
    PUBLISH = "PUBLISH"
    CONSUME = "CONSUME"


@dataclass
class QueueMessage(DataclassMixin):
    trace_id: str
    function_name: str | Enum
    data: list | dict
    started: DateTime | None = None
    attempt_number: int = 3
    retry_delay_second: int = 3

    def _check(self, o: Self):
        if not isinstance(o, QueueMessage):
            raise TypeError("must be QueueMessage")
        if o.trace_id != self.trace_id:
            raise ValueError("trace_id must be same")
        if o.function_name != self.function_name:
            raise ValueError("function_name must be same")
        if not isinstance(o.data, type(self.data)):
            raise ValueError("data must be same type")

    def __iadd__(self, o: Self) -> Self:
        self._check(o)
        if isinstance(self.data, list):
            self.data.extend(o.data)
        if isinstance(self.data, dict):
            raise NotImplementedError("data of dict type is not supported")
        return self

    def to_payload(self) -> dict:
        return self.to_camel_case_json()


class MessageQueuePublisherInterface(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def push_message(self, routing_key, message: QueueMessage):
        pass

    @abc.abstractmethod
    def publish_messages(self):
        pass


QueueHandler = Callable[[QueueMessage], None]


class MessageQueueConsumerInterface(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def start_consume(self, handler: QueueHandler):
        pass


class MessageQueueConnection:
    def __init__(
        self,
        amqp_url: str,
        operation_type: OperationType,
        queue_name: str | None = None,
        routing_key: str | None = None,
        exchange_name: str | None = None,
        exchange_type: ExchangeType | None = None,
    ):
        self.parameters = pika.URLParameters(amqp_url)
        self.operation_type = operation_type
        self.queue_name = queue_name
        self.routing_key = routing_key
        self.exchange_name = exchange_name
        self.exchange_type = exchange_type

        self.connection: pika.BlockingConnection | None = None
        self.channel: BlockingChannel | None = None

    def __enter__(self):
        try:
            self.connection = pika.BlockingConnection(self.parameters)
            self.channel = self.connection.channel()
            match self.operation_type:
                case OperationType.PUBLISH:
                    self.channel.exchange_declare(
                        exchange=self.exchange_name,
                        exchange_type=self.exchange_type,
                        durable=False,
                    )
                case OperationType.CONSUME:
                    self.channel.exchange_declare(
                        exchange=self.exchange_name,
                        exchange_type=self.exchange_type,
                        durable=False,
                    )
                    self.channel.queue_declare(queue=self.queue_name, durable=True)
                    self.channel.queue_bind(
                        queue=self.queue_name,
                        exchange=self.exchange_name,
                        routing_key=self.routing_key,
                    )
        except Exception as e:
            raise connection_workflow.AMQPConnectorException(
                "Failed to create connection, stopping..."
            ) from e

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection and self.connection.is_open:
            self.connection.close()
            self.connection = None
            self.channel = None

    def __del__(self):
        if self.connection and self.connection.is_open:
            self.connection.close()
