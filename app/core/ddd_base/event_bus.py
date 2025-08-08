from collections import defaultdict
from functools import wraps
from typing import Any, Callable, Coroutine, Iterable

from app.core.ddd_base.domain_event import DomainEvent
from app.core.ddd_base.exception import InvalidEventRegisterError

type AsyncEventHandler = Callable[[DomainEvent], Coroutine[Any, Any, Any]]


class EventBus:
    def __init__(self) -> None:
        self._subscribed_for_events: dict[type[DomainEvent], set[AsyncEventHandler]] = defaultdict(
            set
        )
        self._subscribed_for_all: set[AsyncEventHandler] = set()

    def subscribe(self, event_types: list[type[DomainEvent]] = None, all_event=False):
        """Decorator for subscribing a function to a specific event.
        :param event_types: Type of events to subscribe to.
        :return: The outer function.
        """

        def outer(func: AsyncEventHandler):
            if all_event and event_types:
                raise InvalidEventRegisterError(
                    "You can only register a function to some specific event or for all event"
                )

            if all_event:
                self._subscribed_for_all.add(func)
            else:
                for event_type in event_types:
                    self._subscribed_for_events[event_type].add(func)

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return outer

    async def publish_all(self, events: list[DomainEvent]) -> None:
        """Publish all events and run the related subscribed functions.
        :param events: Instances of domain events.
        """
        for event in events:
            await self.publish(event)

    async def publish(self, event: DomainEvent) -> None:
        """Emit an event and run the subscribed functions.
        :param event: Instance of domain event.
        """
        for func in self._event_funcs(event):
            await func(event)

    def deregister_all_events(self) -> None:
        """Clear all registered event handlers"""
        self._subscribed_for_events = defaultdict(set)
        self._subscribed_for_all = set()

    # ------------------------------------------
    # Private methods.
    # ------------------------------------------
    def _event_funcs(self, event: DomainEvent) -> Iterable[AsyncEventHandler]:
        """Returns an Iterable of the functions subscribed to a event.
        :param event: Name of the event.
        :return: A iterable to do things with.
        """
        yield from self._subscribed_for_events[type(event)].union(self._subscribed_for_all)


event_bus = EventBus()
