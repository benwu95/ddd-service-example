import abc
import uuid

from app.core.ddd_base.domain_event import DomainEvent


class AggregateRoot(metaclass=abc.ABCMeta):
    def __init__(self):
        self.is_archive = False
        self.is_delete = False
        self.domain_events: list[DomainEvent] = []

    def add_event(self, event: DomainEvent):
        self.domain_events.append(event)
        self.is_archive = True

    def clear_events(self):
        self.domain_events = []
        self.is_archive = False

    def save_events_tracing(
        self, parent_event: DomainEvent | None = None, trace_id: str | None = None
    ):
        if parent_event:
            for event in self.domain_events:
                event.tracer.parent_span_id = parent_event.tracer.span_id
                event.tracer.trace_id = parent_event.tracer.trace_id
        elif trace_id:
            for event in self.domain_events:
                event.tracer.trace_id = trace_id

    @property
    def all_events(self) -> list[DomainEvent]:
        return list(self.domain_events)

    @abc.abstractmethod
    def mark_as_delete(self):
        pass

    @staticmethod
    def generate_id() -> str:
        return str(uuid.uuid4())
