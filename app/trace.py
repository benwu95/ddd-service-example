import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass

from dataclass_mixins import DataclassMixin
from werkzeug.local import LocalProxy

_trace_id = ContextVar("trace_id")
_trace_id.set(None)


def set_trace_id(trace_id: str | None = None):
    _trace_id.set(trace_id or str(uuid.uuid4()))


def get_trace_id() -> str:
    if not _trace_id.get():
        set_trace_id()
    return _trace_id.get()


_request_start_time = ContextVar("request_start_time")
_request_start_time.set(None)
request_start_time: float | None = LocalProxy(_request_start_time)  # type: ignore[assignment]


def set_request_start_time():
    _request_start_time.set(time.time())


@dataclass
class TokenUser(DataclassMixin):
    id: str
    email: str | None
    name: str | None
    mobile: str | None


@dataclass
class TokenOrganization(DataclassMixin):
    id: str
    name: str


@dataclass
class TokenInfo(DataclassMixin):
    # basic
    iss: str
    sub: str
    aud: str
    exp: int
    nbf: int
    iat: int

    # extended
    user: TokenUser
    organization: TokenOrganization

    # custom
    raw_token: str

    def get(self, key: str, default=None):
        return self.__dict__.get(key, default)


_token_info = ContextVar("token_info")
_token_info.set(None)
token_info: TokenInfo | None = LocalProxy(_token_info)  # type: ignore[assignment]


def set_token_info(t: TokenInfo | None = None):
    _token_info.set(t)
