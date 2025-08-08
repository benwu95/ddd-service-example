from app.core.ddd_base.aggregate import AggregateRoot
from app.core.ddd_base.domain_event import DomainEvent


class UseCaseBase:
    def __init__(self):
        self._parent_event: DomainEvent | None = None
        self._trace_id: str | None = None

    @property
    def parent_event(self) -> DomainEvent | None:
        return self._parent_event

    @parent_event.setter
    def parent_event(self, value: DomainEvent):
        if not isinstance(value, DomainEvent):
            raise ValueError('parent_event must be a DomainEvent')
        self._parent_event = value
        self._trace_id = None

    @property
    def trace_id(self) -> str | None:
        return self._trace_id

    @trace_id.setter
    def trace_id(self, value: str):
        self._trace_id = value
        self._parent_event = None

    def _save_tracing(self, aggregate: AggregateRoot):
        if self._parent_event:
            aggregate.save_events_tracing(parent_event=self._parent_event)
            self._parent_event = None
        elif self._trace_id:
            aggregate.save_events_tracing(trace_id=self._trace_id)
            self._trace_id = None
