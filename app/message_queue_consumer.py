import concurrent.futures
import signal
import sys
import time
from enum import Enum

from pika.adapters.utils import connection_workflow

from app.config import config
from app.logger import ServiceLogger, setup_logging
from app.package_instance import message_queue_publisher
from app.port.message_queue import (
    your_exchange_handler,
)
from packages.message_queue.rabbitmq_message_queue import RabbitMqConsumer

logger = ServiceLogger(__name__)
RESTART_MAX_NUM = 10
SHUTDOWN_DELAY_SECONDS = 10
PROCESS_TIMEOUT_SECONDS = 600


class Exchange(Enum):
    YOUR_EXCHANGE = "your-exchange"


class GracefulKiller:
    def __init__(self, executor: concurrent.futures.ProcessPoolExecutor):
        self.executor = executor
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)

    def exit_gracefully(self, signalnum, handler):
        logger.info("Graceful shutdown...")
        self.executor.shutdown()
        sys.exit(0)


def serve(exchange_name: str, queue_name: str, routing_key: str):
    setup_logging()

    match exchange_name:
        case Exchange.YOUR_EXCHANGE.value:
            external_handler = your_exchange_handler
        case _:
            logger.error("Exchange %s not found", exchange_name)
            sys.exit(1)

    consumer = RabbitMqConsumer(config.amqp_url, queue_name, routing_key, exchange_name)
    consumer.logger = ServiceLogger(consumer.logger.name)
    consumer.start_consume(external_handler)
    if message_queue_publisher.messages:
        message_queue_publisher.publish_messages()


if __name__ == "__main__":
    service = "ddd-service"
    exchanges = [e.value for e in Exchange]
    # * (star) can substitute for exactly one word.
    # # (hash) can substitute for zero or more words.
    routing_key_with_hash = f"#.{service}.#"

    ps = []
    for exchange in exchanges:
        queue = f"{service}-queue_{exchange}"
        ps.append((serve, exchange, queue, routing_key_with_hash))

    exe = concurrent.futures.ProcessPoolExecutor(max_workers=len(ps) + 4)
    GracefulKiller(exe)
    fs: list[tuple[concurrent.futures.Future, tuple]] = []
    next_fs: list[tuple[concurrent.futures.Future, tuple]] = []

    try:
        for p in ps:
            fs.append((exe.submit(*p), p))

        restart_count = 0
        while restart_count < RESTART_MAX_NUM:
            next_fs = []
            for f, p in fs:
                try:
                    f.result(1)
                    next_fs.append((exe.submit(*p), p))
                    restart_count += 1
                except TimeoutError:
                    next_fs.append((f, p))
                except connection_workflow.AMQPConnectorException as e:
                    logger.exception(e)
                    restart_count += RESTART_MAX_NUM
                except Exception:
                    logger.exception("Unexpected error...")
                    next_fs.append((exe.submit(*p), p))
                    restart_count += 1
            fs = next_fs
    except Exception:
        logger.exception("Unexpected error...")

    logger.info("Start shutdown after %d seconds...", SHUTDOWN_DELAY_SECONDS)
    time.sleep(SHUTDOWN_DELAY_SECONDS)

    # terminate
    for pid, p in exe._processes.items():
        p.terminate()

    # force kill
    for f, p in fs:
        try:
            f.result(PROCESS_TIMEOUT_SECONDS)
        except Exception:
            pass
    for pid, p in exe._processes.items():
        p.kill()

    exe.shutdown()
