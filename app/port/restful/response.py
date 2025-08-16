from dataclasses import dataclass, is_dataclass
from io import BytesIO
from typing import Any

import orjson
from dataclass_mixins import to_camel_case_json
from starlette.responses import JSONResponse, StreamingResponse

from app.trace import get_trace_id


@dataclass
class DefaultContent:
    code: str
    data: Any


class DefaultResponse(JSONResponse):
    def render(self, content: DefaultContent) -> bytes:
        def convert(value):
            if isinstance(value, list):
                return [convert(v) for v in value]
            if is_dataclass(value):
                return to_camel_case_json(value)
            return value

        return orjson.dumps(
            {
                "code": content.code,
                "traceId": get_trace_id(),
                "data": convert(content.data),
            }
        )


class ResponseMixin:

    @staticmethod
    def accepted(detail: Any = "Accepted") -> DefaultResponse:
        return DefaultResponse(DefaultContent("Accepted", detail), status_code=202)

    @staticmethod
    def failed(detail: Any = "Bad Request") -> DefaultResponse:
        return DefaultResponse(DefaultContent("Bad Request", detail), status_code=400)

    @staticmethod
    def unauthorized(detail: Any = "Unauthorized") -> DefaultResponse:
        return DefaultResponse(DefaultContent("Unauthorized", detail), status_code=401)

    @staticmethod
    def forbidden(detail: Any = "Forbidden") -> DefaultResponse:
        return DefaultResponse(DefaultContent("Forbidden", detail), status_code=403)

    @staticmethod
    def not_found(detail: Any = "Not Found") -> DefaultResponse:
        return DefaultResponse(DefaultContent("Not Found", detail), status_code=404)

    @staticmethod
    def error(detail: Any = "Internal Server Error") -> DefaultResponse:
        return DefaultResponse(DefaultContent("Internal Server Error", detail), status_code=500)


class ApiResponse(ResponseMixin):

    @staticmethod
    def success(detail: Any = None, status_code: int = 200) -> DefaultResponse:
        return DefaultResponse(DefaultContent("OK", detail), status_code=status_code)


class FileResponse(ResponseMixin):

    @staticmethod
    def success(file: BytesIO, file_name: str, content_type: str) -> StreamingResponse:
        file.seek(0)
        return StreamingResponse(
            file,
            headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
            media_type=content_type,
        )
