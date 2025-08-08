from app.core.ddd_base.exception import DomainError


class YourAggregateError(DomainError):
    pass


class YourAggregateStatusNotMatched(YourAggregateError):
    pass
