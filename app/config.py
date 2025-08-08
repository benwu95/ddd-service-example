import os
from enum import Enum
from urllib.parse import quote_plus

import pendulum
from pendulum.datetime import DateTime


class DeploymentType(Enum):
    LOCAL = "LOCAL"
    DEV = "DEV"
    STAGE = "STAGE"
    UAT = "UAT"
    PROD = "PROD"


# env from manifest
class Config:
    service_name = "ddd-service"

    # Database
    database_username = os.environ.get("DATABASE_USERNAME", "postgres")
    database_password = os.environ.get("DATABASE_PASSWORD", "password")
    database_url = os.environ.get("DATABASE_URL", "127.0.0.1:5432/default")
    sqlalchemy_database_url = f"postgresql+psycopg://{database_username}:{quote_plus(database_password)}@{database_url}"
    postgres_schema = os.environ.get("POSTGRES_SCHEMA", "ddd_service")

    # Server
    port = os.environ.get("PORT", "8080")
    deployment_type = DeploymentType(os.environ.get("DEPLOYMENT_TYPE", "LOCAL"))

    # Swagger
    swagger_version = os.environ.get("SWAGGER_VERSION", None)
    enable_dev_route = os.environ.get("ENABLE_DEV_ROUTE", "false")
    gateway_prefix = os.environ.get("GATEWAY_PREFIX", "")

    # Time
    time_zone = os.environ.get("TIME_ZONE", "Asia/Taipei")
    pendulum_datetime_format = os.environ.get("PENDULUM_DATETIME_FORMAT", "YYYY-MM-DD HH:mm:ss")

    def convert_to_datetime(self, date_str: str) -> DateTime:
        d = pendulum.parse(date_str, tz=self.time_zone)
        if not isinstance(d, DateTime):
            raise ValueError(f"Expected DateTime, got {type(d)}, {d}")
        return d

    def convert_to_datetime_str(self, datetime: DateTime | None) -> str | None:
        if datetime:
            return datetime.in_tz(self.time_zone).format(self.pendulum_datetime_format)

    # rabbitmq
    rabbitmq_host = os.environ.get("RABBITMQ_HOST", "localhost")
    rabbitmq_port = os.environ.get("RABBITMQ_PORT", "5672")
    rabbitmq_username = os.environ.get("RABBITMQ_USERNAME", "root")
    rabbitmq_password = os.environ.get("RABBITMQ_PASSWORD", "1234")
    rabbitmq_virtual_host = os.environ.get("RABBITMQ_VIRTUAL_HOST", "/")
    amqp_url = f"amqp://{rabbitmq_username}:{quote_plus(rabbitmq_password)}@{rabbitmq_host}:{rabbitmq_port}/{quote_plus(rabbitmq_virtual_host)}?heartbeat=600"
    rabbitmq_exchange_name = "ddd-service-channel"
    rabbitmq_consumer_name = "ddd-service-consumer"


config = Config()
