import json
import re
import uuid
from contextvars import ContextVar
from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, JSONPATH
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute
from sqlalchemy.orm.state import InstanceState
from sqlalchemy.sql.base import ExecutableOption
from sqlalchemy.sql.expression import UnaryExpression
from werkzeug.local import LocalProxy

from app.adapter.repository.orm import (
    ArchiveMixin,
    DomainEventModel,
)
from app.core.ddd_base import AggregateRoot, DomainEvent
from app.port.storage.sql.postgres import DB_Session


class SessionProvider:
    def __init__(self):
        self.session: AsyncSession = None
        self.session_count = 0

    async def __aenter__(self):
        if self.session_count == 0:
            self.session = DB_Session()
        self.session_count += 1
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.session_count -= 1
        if self.session_count <= 0:
            self.session_count = 0
            try:
                await self.session.commit()
                await self.session.__aexit__(exc_type, exc_val, exc_tb)
                self.session = None
            except Exception as e:
                await self.session.rollback()
                await self.session.__aexit__(exc_type, exc_val, exc_tb)
                self.session = None
                raise e


_session_provider = ContextVar('session_provider')
session_provider: SessionProvider = LocalProxy(_session_provider)  # type: ignore[assignment]


def set_session_provider():
    _session_provider.set(SessionProvider())


set_session_provider()


@dataclass
class SearchKeyField:
    column: InstrumentedAttribute
    json_path: str | None = None


class RepositoryBase:
    def __init__(self, session_provider: SessionProvider):
        self.session_provider = session_provider

    @staticmethod
    def entity_name() -> str:
        raise NotImplementedError()

    @staticmethod
    def model_class() -> type:
        raise NotImplementedError()

    @staticmethod
    def archive_model_class() -> type[ArchiveMixin]:
        raise NotImplementedError()

    @staticmethod
    def search_key_fields() -> dict[str, SearchKeyField]:
        raise NotImplementedError()

    @staticmethod
    def sort_by_fields() -> dict[str, InstrumentedAttribute]:
        raise NotImplementedError()

    @staticmethod
    def model_to_entity(model):
        raise NotImplementedError()

    @classmethod
    def create_search_key_regexp(
        cls,
        search_key_field: str,
        search_keys: list[str]
    ) -> tuple[str, str]:
        search_key_regexp = '|'.join(re.escape(str(k)) for k in search_keys)
        search_key_field_pattern = re.compile(r'^((?P<operator>starts|ends|equals):)?(?P<search_key_field>\w+)$')
        m = search_key_field_pattern.match(search_key_field)
        if m:
            op = m.group('operator')
            field = m.group('search_key_field')
            match op:
                case 'starts':
                    return field, f'^{search_key_regexp}'
                case 'ends':
                    return field, f'{search_key_regexp}$'
                case 'equals':
                    return field, f'^{search_key_regexp}$'
                case _:
                    return field, search_key_regexp
        return search_key_field, search_key_regexp

    @classmethod
    def create_sort_by_exp(cls, sort_by: list[str]) -> list[UnaryExpression]:
        sort_by_exp = []
        used_fields = set()
        pattern = re.compile(r'^([\-\+]?)(\w+)$')
        for sort in sort_by:
            m = pattern.match(sort)
            if m:
                order, field = m.groups()
                if field in cls.sort_by_fields() and field not in used_fields:
                    used_fields.add(field)
                    if order == '-':
                        sort_by_exp.append(sa.desc(cls.sort_by_fields()[field]))
                    else:
                        sort_by_exp.append(sa.asc(cls.sort_by_fields()[field]))
        return sort_by_exp

    @property
    def session(self) -> AsyncSession:
        return self.session_provider.session

    async def _get_model(self, pkey):
        return await self.session.get(self.model_class(), pkey)

    async def _load(self, pkey, lock: bool):
        try:
            if lock:
                model = await self.session.get(self.model_class(), pkey, with_for_update=True)
            else:
                model = await self._get_model(pkey)
        except Exception:
            model = None

        if not model:
            raise NoResultFound(f'{self.entity_name()} {pkey} not found')

        return self.model_to_entity(model)

    async def _search(
        self,
        filters: list[sa.ColumnExpressionArgument],
        search_key_fields: list[str],
        search_keys: list[str] | None,
        sort_by: list[str],
        offset: int,
        limit: int,
        options: list[ExecutableOption] | None = None,
        return_entity: bool = True
    ) -> tuple[int, list]:
        q_filters = list(filters)
        if search_keys:
            search_key_filters = []
            for search_key_field in search_key_fields:
                f, search_key_regexp = self.create_search_key_regexp(search_key_field, search_keys)
                s = self.search_key_fields().get(f)
                if s:
                    if isinstance(s.column.type, JSONB):
                        search_key_filters.append(
                            s.column.path_match(
                                sa.cast(
                                    f'{s.json_path} like_regex {json.dumps(search_key_regexp)}',
                                    JSONPATH
                                )
                            )
                        )
                    else:
                        c = sa.cast(s.column, sa.TEXT) if f == 'id' else s.column
                        search_key_filters.append(c.regexp_match(search_key_regexp))
            if search_key_filters:
                q_filters.append(sa.or_(*search_key_filters))

        total_stmt = sa.select(sa.func.count()).select_from(self.model_class()).where(*q_filters)
        q_stmt = sa.select(self.model_class()).where(*q_filters)

        sort_by_exp = self.create_sort_by_exp(sort_by)
        if not sort_by_exp:
            sort_by_exp = self.create_sort_by_exp(['-created'])
        q_stmt = q_stmt.order_by(*sort_by_exp)

        q_stmt = q_stmt.offset(offset)
        if limit > 0:
            q_stmt = q_stmt.limit(limit)

        if options:
            q_stmt = q_stmt.options(*options)

        total = await self.session.execute(total_stmt)
        total = total.scalar() or 0
        q = await self.session.execute(q_stmt)

        if return_entity:
            return total, [self.model_to_entity(model) for model in q.scalars()]
        return total, list(q)

    def _archive(self, model, event: DomainEvent | None):
        archive_model = self.archive_model_class()()
        archive_model.archive_id = str(uuid.uuid4())
        if event:
            archive_model.doer = event.doer.serialize()
            archive_model.event_name = type(event).__name__
            archive_model.event_span_id = event.tracer.span_id
            archive_model.event_trace_id = event.tracer.trace_id
        for attr, value in vars(model).items():
            if not isinstance(value, InstanceState) and hasattr(archive_model, attr):
                setattr(archive_model, attr, value)

        self.session.add(archive_model)

    async def _save(self, aggregate: AggregateRoot, model):
        if aggregate.is_delete:
            await self.session.delete(model)
        else:
            self.session.add(model)

        if aggregate.is_archive:
            event = None
            if aggregate.all_events:
                event = aggregate.all_events[-1]
            self._archive(model, event)

        for event in aggregate.all_events:
            self.session.add(DomainEventModel(**event.serialize()))

        await self.session.flush()
