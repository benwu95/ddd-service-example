import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from functools import wraps
from typing import Self

from dataclass_mixins import DataclassMixin, camel_to_snake_case
from pendulum.datetime import DateTime
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapter.repository.base import session_provider
from app.core.ddd_base import UseCaseBase, User
from app.logger import ServiceLogger
from app.package_instance import message_queue_publisher
from app.trace import TokenInfo


def create_user(token_info: TokenInfo) -> User:
    return User(
        id=token_info.user.id,
        organization_id=token_info.organization.id,
        name=token_info.user.name,
        email=token_info.user.email,
        mobile=token_info.user.mobile,
    )


@dataclass
class RequestBase(DataclassMixin):
    doer: User
    trace_id: str | None

    @classmethod
    def create_from_body(cls, body: dict, token_info: TokenInfo, trace_id: str | None) -> Self:
        d = cls.create_from_camel_case_json(body)
        d.doer = create_user(token_info)
        d.trace_id = trace_id
        return d


@dataclass
class SearchRequestBase(RequestBase):
    date_fields: list[str] | None
    start_time: DateTime | None
    end_time: DateTime | None
    search_key_fields: list[str] | None
    search_keys: list[str] | None
    sort_by: list[str] | None
    offset: int
    limit: int

    def __post_init__(self):
        new_search_key_fields = []
        for field in self.search_key_fields or []:
            new_search_key_fields.append(camel_to_snake_case(field))
        self.search_key_fields = new_search_key_fields

        new_sort_by = []
        for s in self.sort_by or []:
            new_sort_by.append(camel_to_snake_case(s))
        self.sort_by = new_sort_by


@dataclass
class OrganizationResponse(DataclassMixin):
    id: str | None
    name: str | None


@dataclass
class UserResponse(DataclassMixin):
    id: str | None
    organization: OrganizationResponse
    name: str | None
    email: str | None
    mobile: str | None

    @classmethod
    def create_from_object(cls, obj: User) -> "UserResponse":
        resp = super().create_from_object(obj)

        # TODO: fix organization info
        resp.organization = OrganizationResponse(obj.organization_id, None)

        return resp


class ControllerBase:
    def __init__(self):
        self.session_provider = session_provider
        self.logger = ServiceLogger(self.__class__.__name__)
        self.use_cases: list[UseCaseBase] = []

        self.message_queue_publisher = message_queue_publisher

    @property
    def session(self) -> AsyncSession:
        return self.session_provider.session

    def set_tracing(self, trace_id: str | None = None):
        if not trace_id:
            trace_id = str(uuid.uuid4())
        for use_case in self.use_cases:
            use_case.trace_id = trace_id

    def add_use_case(self, use_case: UseCaseBase):
        self.use_cases.append(use_case)

    @staticmethod
    def connect_db_session(
        exception_message: str = "",
        warning_exceptions: Iterable[type[Exception]] = tuple(),
    ):
        def inner(func):
            @wraps(func)
            async def wrapper(self: ControllerBase, *requests: RequestBase):
                result = None
                async with self.session_provider:
                    try:
                        trace_id = requests[0].trace_id if len(requests) > 0 else None
                        self.set_tracing(trace_id)
                        result = await func(self, *requests)
                        await self.session.flush()
                    except NoResultFound as e:
                        await self.session.rollback()
                        self.logger.warning(exception_message if exception_message else str(e))
                        self.message_queue_publisher.clean_messages()
                        raise e
                    except IntegrityError as e:
                        await self.session.rollback()
                        self.logger.error(exception_message if exception_message else str(e))
                        self.message_queue_publisher.clean_messages()
                        raise SQLAlchemyError("\n".join(e.args)) from e
                    except tuple(warning_exceptions) as e:
                        await self.session.rollback()
                        self.logger.warning(exception_message if exception_message else str(e))
                        self.message_queue_publisher.clean_messages()
                        raise e
                    except Exception as e:
                        await self.session.rollback()
                        self.logger.exception(exception_message if exception_message else str(e))
                        self.message_queue_publisher.clean_messages()
                        raise e

                if self.message_queue_publisher.messages:
                    self.message_queue_publisher.publish_messages()
                return result

            return wrapper

        return inner
