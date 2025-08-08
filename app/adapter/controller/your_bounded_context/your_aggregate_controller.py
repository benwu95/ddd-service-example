from io import BytesIO

from app.adapter.controller.base import ControllerBase
from app.adapter.controller.your_bounded_context.request import (
    CreateYourAggregateRequest,
    DeleteYourAggregateRequest,
    GetYourAggregateRequest,
    SearchYourAggregatesRequest,
    UpdateYourAggregateRequest,
    VoidYourAggregateRequest,
)
from app.adapter.controller.your_bounded_context.response import (
    SearchYourAggregatesResponse,
    YourAggregateResponse,
)
from app.adapter.repository.your_aggregate_repository import YourAggregateRepository
from app.config import config
from app.core.your_bounded_context.use_case.your_aggregate_use_case import (
    YourAggregateUseCase,
)
from packages.dataclass2excel import create_xlsx
from packages.dataclass2excel.type import YourAggregateExcel


class YourAggregateController(ControllerBase):
    def __init__(self):
        super().__init__()

        self.repository = YourAggregateRepository(self.session_provider)
        self.use_case = YourAggregateUseCase(self.repository)
        self.add_use_case(self.use_case)

    @ControllerBase.connect_db_session()
    async def get_your_aggregate(self, get_request: GetYourAggregateRequest) -> YourAggregateResponse:
        your_aggregate = await self.repository.load_your_aggregate(get_request.id, lock=False)
        return YourAggregateResponse.create_from_object(your_aggregate)

    @ControllerBase.connect_db_session()
    async def search_your_aggregates(self, search_request: SearchYourAggregatesRequest) -> SearchYourAggregatesResponse:
        result = await self.repository.search_your_aggregates(
            ids=search_request.ids,
            statuses=search_request.statuses,
            date_fields=search_request.date_fields,
            start_time=search_request.start_time,
            end_time=search_request.end_time,
            search_key_fields=search_request.search_key_fields,
            search_keys=search_request.search_keys,
            sort_by=search_request.sort_by,
            offset=search_request.offset,
            limit=search_request.limit,
        )

        return SearchYourAggregatesResponse.create_from_object(result)

    @ControllerBase.connect_db_session()
    async def export_your_aggregates(self, search_request: SearchYourAggregatesRequest) -> BytesIO:
        result = await self.repository.search_your_aggregates(
            ids=search_request.ids,
            statuses=search_request.statuses,
            date_fields=search_request.date_fields,
            start_time=search_request.start_time,
            end_time=search_request.end_time,
            search_key_fields=search_request.search_key_fields,
            search_keys=search_request.search_keys,
            sort_by=search_request.sort_by,
        )
        data = []
        for your_aggregate in result.results:
            data.append(
                YourAggregateExcel(
                    your_aggregate.id,
                    your_aggregate.your_value_object.property_a,
                    your_aggregate.your_value_object.property_b,
                    str(your_aggregate.status),
                    your_aggregate.creator.name,
                    config.convert_to_datetime_str(your_aggregate.created_at),
                )
            )
        return create_xlsx(title="YourAggregates", dc_type=YourAggregateExcel, dc_list=data)

    @ControllerBase.connect_db_session()
    async def create_your_aggregate(self, *create_requests: CreateYourAggregateRequest) -> list[str] | str:
        resp = []
        for create_request in create_requests:
            resp.append(
                await self.use_case.create_your_aggregate(create_request.your_value_object, create_request.doer)
            )
        return resp if len(resp) > 1 else resp[0]

    @ControllerBase.connect_db_session()
    async def delete_your_aggregate(self, *delete_requests: DeleteYourAggregateRequest) -> list[str] | str:
        resp = []
        for delete_request in delete_requests:
            await self.use_case.delete_your_aggregate(delete_request.id, delete_request.doer)
            resp.append(delete_request.id)
        return resp if len(resp) > 1 else resp[0]

    @ControllerBase.connect_db_session()
    async def update_your_aggregate(self, *update_requests: UpdateYourAggregateRequest) -> list[str] | str:
        resp = []
        for update_request in update_requests:
            await self.use_case.update_your_aggregate(
                update_request.id, update_request.your_value_object, update_request.doer
            )
            resp.append(update_request.id)
        return resp if len(resp) > 1 else resp[0]

    @ControllerBase.connect_db_session()
    async def void_your_aggregate(self, *void_requests: VoidYourAggregateRequest) -> list[str] | str:
        resp = []
        for void_request in void_requests:
            await self.use_case.void_your_aggregate(void_request.id, void_request.doer)
            resp.append(void_request.id)
        return resp if len(resp) > 1 else resp[0]
