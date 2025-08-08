import json
import logging
import signal
from copy import deepcopy

import pendulum
import pika
import pika.channel
import pika.exceptions
import pika.spec
from pika.exchange_type import ExchangeType

from packages.message_queue.message_queue import (
    MessageQueueConnection,
    MessageQueueConsumerInterface,
    MessageQueuePublisherInterface,
    QueueMessage,
    QueueHandler,
    OperationType,
)


class RabbitMqPublisher(MessageQueuePublisherInterface):
    def __init__(
        self,
        amqp_url: str,
        exchange_name: str,
        exchange_type: ExchangeType = ExchangeType.topic
    ):
        self.logger = logging.getLogger(self.__class__.__name__)

        self.connection = MessageQueueConnection(
            amqp_url,
            OperationType.PUBLISH,
            exchange_name=exchange_name,
            exchange_type=exchange_type
        )
        self.messages: dict[str, dict[str, QueueMessage]] = {}

    def clean_messages(self):
        self.messages = {}

    def push_message(self, routing_key: str, message: QueueMessage, auto_publish: bool = False):
        if auto_publish:
            payload = message.to_payload()
            self.publish_raw_message(routing_key, payload)
        else:
            if routing_key not in self.messages:
                self.messages[routing_key] = {}
            function_name = message.function_name if isinstance(message.function_name, str) else message.function_name.value
            m_key = f'{message.trace_id}_{function_name}'
            if m_key not in self.messages[routing_key]:
                self.messages[routing_key][m_key] = message
            else:
                self.messages[routing_key][m_key] += message

    def publish_messages(self):
        try:
            with self.connection:
                copy_messages = deepcopy(self.messages)
                for routing_key, messages in copy_messages.items():
                    for m_key, message in messages.items():
                        payload = message.to_payload()
                        self.logger.info('publish message to %s', routing_key, extra={'detail': payload, 'traceId': message.trace_id})
                        if not self.connection.channel:
                            raise RuntimeError('Publish channel not found')
                        self.connection.channel.basic_publish(
                            exchange=self.connection.exchange_name,
                            routing_key=routing_key,
                            body=json.dumps(payload)
                        )
                        self.logger.info('publish complete', extra={'traceId': message.trace_id})
                        self.messages[routing_key].pop(m_key)
                self.messages = {}
        except Exception as e:
            self.logger.error('publish messages error: %s', e)

    def publish_raw_message(self, routing_key: str, message: dict, message_logging: bool = True):
        with self.connection:
            trace_id = message.get('traceId')
            if message_logging:
                self.logger.info('publish message to %s', routing_key, extra={'detail': message, 'traceId': trace_id})
            if not self.connection.channel:
                raise RuntimeError('Publish channel not found')
            self.connection.channel.basic_publish(
                exchange=self.connection.exchange_name,
                routing_key=routing_key,
                body=json.dumps(message)
            )
            if message_logging:
                self.logger.info('publish complete', extra={'traceId': trace_id})


class RabbitMqConsumer(MessageQueueConsumerInterface):
    def __init__(
        self,
        amqp_url: str,
        queue_name: str,
        routing_key: str,
        exchange_name: str,
        exchange_type: ExchangeType = ExchangeType.topic
    ):
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        self.kill_now = False
        self.logger = logging.getLogger(f'{self.__class__.__name__}:{queue_name}')

        self.routing_key = routing_key
        self.connection = MessageQueueConnection(
            amqp_url,
            OperationType.CONSUME,
            queue_name=queue_name,
            routing_key=routing_key,
            exchange_name=exchange_name,
            exchange_type=exchange_type
        )
        self.publisher = RabbitMqPublisher(amqp_url, exchange_name, exchange_type)

    def exit_gracefully(self, signalnum, handler):
        self.logger.info('Stop consuming...')
        try:
            if self.connection.channel:
                self.connection.channel.stop_consuming()
        except Exception:
            pass
        self.kill_now = True

    def start_consume(self, handler: QueueHandler):
        def rabbitmq_handler(
            ch: pika.channel.Channel,
            method: pika.spec.Basic.Deliver,
            properties: pika.spec.BasicProperties,
            body: bytes
        ):
            # data: raw data
            # message: `QueueMessage`, data is snake case
            data = json.loads(body)
            message = QueueMessage.create_from_camel_case_json(data)

            try:
                if message.started:
                    if message.started < pendulum.now():
                        self.logger.info('message', extra={'detail': data, 'traceId': message.trace_id})
                        handler(message)
                    else:
                        self.publisher.publish_raw_message(self.routing_key, message.to_payload(), message_logging=False)
                else:
                    self.logger.info('message', extra={'detail': data, 'traceId': message.trace_id})
                    handler(message)
            except Exception as e:
                message.started = pendulum.now().add(seconds=message.retry_delay_second)

                if message.attempt_number == -1:
                    self.logger.warning('Consume failed: %s', e, extra={'traceId': message.trace_id})
                    self.logger.info('Retry message', extra={'traceId': message.trace_id})
                    self.publisher.publish_raw_message(self.routing_key, message.to_payload(), message_logging=False)
                else:
                    message.attempt_number -= 1
                    if message.attempt_number > 0:
                        self.logger.warning('Consume failed: %s', e, extra={'traceId': message.trace_id})
                        self.logger.info('Retry message, remaining %s times', message.attempt_number, extra={'traceId': message.trace_id})
                        self.publisher.publish_raw_message(self.routing_key, message.to_payload(), message_logging=False)
                    else:
                        self.logger.exception('Consume failed: %s', e, extra={'traceId': message.trace_id})

            ch.basic_ack(delivery_tag=method.delivery_tag)

        with self.connection:
            self.logger.info(
                'Start consuming %s from %s by %s',
                self.connection.queue_name,
                self.connection.exchange_name,
                self.connection.routing_key
            )
            while not self.kill_now:
                try:
                    if not self.connection.channel:
                        raise RuntimeError('Consume channel not found')
                    self.connection.channel.basic_consume(
                        self.connection.queue_name,
                        rabbitmq_handler,
                        auto_ack=False
                    )
                    self.connection.channel.start_consuming()
                except pika.exceptions.ConnectionClosedByBroker:
                    self.logger.error('Connection was closed by broker, retrying...')
                    self.connection.connection.sleep(1)
                    continue
                # Do not recover on channel errors
                except pika.exceptions.AMQPChannelError as err:
                    self.logger.error('Caught a channel error: %s, stopping...', err)
                    break
                # Recover on all other connection errors
                except pika.exceptions.AMQPConnectionError:
                    self.logger.error('Connection was closed, retrying...')
                    self.connection.connection.sleep(1)
                    continue
