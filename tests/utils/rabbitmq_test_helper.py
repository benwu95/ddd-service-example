import json
import time

import pika
from pika.exchange_type import ExchangeType

from app.config import config
from packages.message_queue.message_queue import QueueMessage


class TemporaryQueueWatcher:
    def __init__(self, amqp_url: str, routing_key: str):
        self.exchange = config.rabbitmq_exchange_name
        self.routing_key = routing_key

        parameters = pika.URLParameters(amqp_url)
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

        self.channel.exchange_declare(exchange=self.exchange, exchange_type=ExchangeType.topic, durable=False)
        result = self.channel.queue_declare(queue="", exclusive=True)
        self.queue_name = result.method.queue

        self.channel.queue_bind(exchange=self.exchange, queue=self.queue_name, routing_key=routing_key)

    def assert_message_published(self, expected_message: QueueMessage, timeout: float = 3):
        expected = expected_message.to_payload()
        expected_function_name = expected["functionName"]
        expected_data = expected["data"]

        deadline = time.time() + timeout
        while time.time() < deadline:
            method, _, body = self.channel.basic_get(queue=self.queue_name, auto_ack=True)
            if method:
                try:
                    message = json.loads(body)
                    function_name = message.get("functionName", "")
                    data = message.get("data", [])
                    if expected_data == data and expected_function_name == function_name:
                        return
                    raise AssertionError(
                        f"Expected ({expected_function_name}, {expected_data}), but got ({function_name}, {data})"
                    )
                except json.JSONDecodeError:
                    pass
            time.sleep(0.2)
        raise AssertionError("Did not receive the expected message from MQ.")

    def close(self):
        self.connection.close()
