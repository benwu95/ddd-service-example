from collections.abc import Callable
from functools import wraps

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapter.repository.base import session_provider
from app.core.ddd_base import DomainEvent, UseCaseBase
from app.logger import ServiceLogger


class EventHandlerHelper:
    def __init__(self):
        self.session_provider = session_provider
        self.logger = ServiceLogger(self.__class__.__name__)
        self.use_cases: list[UseCaseBase] = []

    @property
    def session(self) -> AsyncSession:
        return self.session_provider.session

    def set_tracing(self, parent_event: DomainEvent):
        for use_case in self.use_cases:
            use_case.parent_event = parent_event

    def add_use_case(self, use_case: UseCaseBase):
        self.use_cases.append(use_case)

    def connect_db_session(
        self,
        exception_message: str = "",
    ):
        def inner(func: Callable):
            @wraps(func)
            async def wrapper(event: DomainEvent, *args, **kwargs):
                async with self.session_provider:
                    try:
                        self.set_tracing(event)
                        await func(event, *args, **kwargs)
                        await self.session.flush()
                    except Exception as e:
                        await self.session.rollback()
                        if exception_message:
                            self.logger.warning(exception_message)
                        else:
                            self.logger.warning("%s event handler failed", type(event).__name__)
                        raise e

            return wrapper

        return inner
