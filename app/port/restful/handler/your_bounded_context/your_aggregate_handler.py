from enum import Enum

import pendulum
from sqlalchemy.exc import NoResultFound

from app.adapter.controller import your_aggregate_controller
from app.adapter.controller.base import create_user
from app.adapter.controller.your_bounded_context.request import (
    CreateYourAggregateRequest,
    DeleteYourAggregateRequest,
    GetYourAggregateRequest,
    SearchYourAggregatesRequest,
    UpdateYourAggregateRequest,
    VoidYourAggregateRequest,
)
from app.config import config
from app.port.restful.response import ApiResponse, FileResponse
from app.trace import TokenInfo, get_trace_id


async def get_your_aggregate(your_aggregate_id: str, token_info: TokenInfo):
    try:
        get_request = GetYourAggregateRequest.create_strictly(
            id=your_aggregate_id, doer=create_user(token_info), trace_id=get_trace_id()
        )
        your_aggregate = await your_aggregate_controller.get_your_aggregate(get_request)
        return ApiResponse.success(your_aggregate)
    except NoResultFound as e:
        return ApiResponse.not_found(str(e))
    except Exception as e:
        return ApiResponse.error(str(e))


# https://connexion.readthedocs.io/en/latest/request.html#pythonic-parameters
# The search parameters used by the frontend are generally singular.
# If they conflict with Python reserved words (e.g., id, type, filter),
# to work with Connexion, name them by appending an underscore `_` at the end (e.g., id_).
async def search_your_aggregates(
    token_info: TokenInfo,
    id_: list[str] | None = None,
    status: list[str] | None = None,
    date_field: list[str] | None = None,
    start_time: float | None = None,
    end_time: float | None = None,
    search_key_field: list[str] | None = None,
    search_key: list[str] | None = None,
    sort_by: list[str] | None = None,
    offset: int = 0,
    limit: int = 100,
):
    try:
        search_request = SearchYourAggregatesRequest.create_strictly(
            ids=id_,
            statuses=status,
            date_fields=date_field,
            start_time=start_time,
            end_time=end_time,
            search_key_fields=search_key_field,
            search_keys=search_key,
            sort_by=sort_by,
            offset=offset,
            limit=limit,
            doer=create_user(token_info),
            trace_id=get_trace_id(),
        )
        result = await your_aggregate_controller.search_your_aggregates(search_request)
        return ApiResponse.success(result)
    except Exception as e:
        return ApiResponse.error(str(e))


async def export_your_aggregates(
    token_info: TokenInfo,
    id_: list[str] | None = None,
    status: list[str] | None = None,
    date_field: list[str] | None = None,
    start_time: float | None = None,
    end_time: float | None = None,
    search_key_field: list[str] | None = None,
    search_key: list[str] | None = None,
    sort_by: list[str] | None = None,
):
    try:
        search_request = SearchYourAggregatesRequest.create_strictly(
            ids=id_,
            statuses=status,
            date_fields=date_field,
            start_time=start_time,
            end_time=end_time,
            search_key_fields=search_key_field,
            search_keys=search_key,
            sort_by=sort_by,
            doer=create_user(token_info),
            trace_id=get_trace_id(),
        )
        result = await your_aggregate_controller.export_your_aggregates(search_request)
        return FileResponse.success(
            result,
            f"your-aggregates_{config.convert_to_datetime_str(pendulum.now(tz=config.time_zone))}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        return ApiResponse.error(str(e))


class Command(Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    VOID = "VOID"


async def command(body: dict, token_info: TokenInfo):
    trace_id = get_trace_id()
    cmd = body.get("cmd", "")
    payload = body.get("payload", [])
    resp = {"success": [], "failure": []}

    match cmd:
        case Command.CREATE.value:
            for p in payload:
                try:
                    data = CreateYourAggregateRequest.create_from_body(p, token_info, trace_id)
                    r = await your_aggregate_controller.create_your_aggregate(data)
                    resp["success"].append({"payload": p, "detail": r})
                except Exception as e:
                    resp["failure"].append({"payload": p, "detail": str(e)})
        case Command.UPDATE.value:
            for p in payload:
                try:
                    data = UpdateYourAggregateRequest.create_from_body(p, token_info, trace_id)
                    r = await your_aggregate_controller.update_your_aggregate(data)
                    resp["success"].append({"payload": p, "detail": r})
                except Exception as e:
                    resp["failure"].append({"payload": p, "detail": str(e)})
        case Command.DELETE.value:
            for p in payload:
                try:
                    data = DeleteYourAggregateRequest.create_from_body(p, token_info, trace_id)
                    r = await your_aggregate_controller.delete_your_aggregate(data)
                    resp["success"].append({"payload": p, "detail": r})
                except Exception as e:
                    resp["failure"].append({"payload": p, "detail": str(e)})
        case Command.VOID.value:
            for p in payload:
                try:
                    data = VoidYourAggregateRequest.create_from_body(p, token_info, trace_id)
                    r = await your_aggregate_controller.void_your_aggregate(data)
                    resp["success"].append({"payload": p, "detail": r})
                except Exception as e:
                    resp["failure"].append({"payload": p, "detail": str(e)})
        case _:
            return ApiResponse.failed(f"cmd:<{cmd}> is not supported")

    if resp["failure"]:
        return ApiResponse.failed(resp)
    return ApiResponse.success(resp)
