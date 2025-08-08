import dataclasses
import enum
import uuid
from functools import cached_property
from typing import Iterable

import pendulum
from dataclass_mixins import DataclassMixin
from pendulum.datetime import DateTime


class Tracer:
    def __init__(self):
        self._created_at = pendulum.now()
        self._span_id = str(uuid.uuid4())
        self._parent_span_id = None
        self._trace_id = self._span_id

    @property
    def created_at(self) -> DateTime:
        return self._created_at

    @property
    def span_id(self) -> str:
        return self._span_id

    @property
    def parent_span_id(self) -> str | None:
        return self._parent_span_id

    @parent_span_id.setter
    def parent_span_id(self, value: str):
        self._parent_span_id = value

    @property
    def trace_id(self) -> str:
        return self._trace_id

    @trace_id.setter
    def trace_id(self, value: str):
        self._trace_id = value


@dataclasses.dataclass(frozen=True)
class User(DataclassMixin):
    id: str | None = None
    organization_id: str | None = None
    name: str | None = None
    email: str | None = None
    mobile: str | None = None


class DomainEvent:
    doer: User
    VERSION = 1

    @cached_property
    def tracer(self) -> Tracer:
        return Tracer()

    def serialize(self) -> dict:
        dict_with_enum = dataclasses.asdict(self)
        dict_of_event = self._convert_enum_dict(dict_with_enum)
        return {
            "name": type(self).__name__,
            "body": dict_of_event,
            "created_at": self.tracer.created_at,
            "version": self.VERSION,
            "span_id": self.tracer.span_id,
            "parent_span_id": self.tracer.parent_span_id,
            "trace_id": self.tracer.trace_id,
        }

    def _convert_enum_dict(self, target: dict) -> dict:
        converted = {}
        for k, v in target.items():
            if isinstance(v, dict):
                converted[k] = self._convert_enum_dict(v)
            elif isinstance(v, (list, set)):
                converted[k] = self._convert_enum_iterable(v)
            elif isinstance(v, enum.Enum):
                converted[k] = v.value
            elif isinstance(v, DateTime):
                converted[k] = v.isoformat()
            else:
                converted[k] = v
        return converted

    def _convert_enum_iterable(self, target: Iterable):
        converted = []
        for v in target:
            if isinstance(v, dict):
                converted.append(self._convert_enum_dict(v))
            elif isinstance(v, (list, set)):
                converted.append(self._convert_enum_iterable(v))
            elif isinstance(v, enum.Enum):
                converted.append(v.value)
            elif isinstance(v, DateTime):
                converted.append(v.isoformat())
            else:
                converted.append(v)
        return converted
