import json
import os
import time
from copy import deepcopy
from pathlib import Path

from connexion import AsyncApp, request
from connexion.exceptions import ProblemException
from connexion.middleware import MiddlewarePosition
from connexion.options import SwaggerUIOptions
from prance import ResolvingParser
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.adapter.repository.base import set_session_provider
from app.config import config
from app.logger import setup_logging, ServiceLogger
from app.package_instance import set_message_queue_publisher
from app.port.restful.response import render_problem_exception
from app.trace import (
    request_start_time,
    set_request_start_time,
    set_token_info,
    set_trace_id,
)


logger = ServiceLogger(__name__)


async def log_request(extra_info: dict):
    # [2023-03-31 02:27:32,165] INFO [root.log_request:32] 127.0.0.1 - - "GET /restful/hello HTTP/1.1" 200 -
    url = request.url.path
    method = request.method
    remote_addr = request.client.host
    status_code = extra_info['status']
    protocol = f'HTTP/{request.scope["http_version"]}'
    http_request_gcloud_info = {
        'requestMethod': method,
        'requestUrl': url,
        'status': status_code,
        'userAgent': request.headers['user-agent'],
        'remoteIp': remote_addr,
        'protocol': protocol
    }
    body = extra_info['body']
    resp = {}
    no_log_post_urls = []
    if (
        (method == 'POST' and url not in no_log_post_urls)
        or status_code >= 400
    ):
        resp = extra_info['resp']
    if request_start_time:
        http_request_gcloud_info['latency'] = f'{time.time() - request_start_time:6f}s'
    logger.info(
        '%s - - "%s %s %s" %s -',
        remote_addr,
        method,
        url,
        protocol,
        status_code,
        extra={'httpRequest': http_request_gcloud_info, 'detail': {'request': body, 'response': resp}}
    )


def modified_version(specification) -> dict:
    result = deepcopy(specification)

    if config.swagger_version:
        result['info']['version'] = config.swagger_version

    return result


# Remove swagger yml with x-dev: true while on production
def route_toggle(specification):
    result = deepcopy(specification)

    if config.enable_dev_route != 'true':
        for route, defines in specification['paths'].items():
            for method, schema in defines.items():
                if 'x-dev' in schema:
                    result['paths'][route].pop(method, None)
    return result


class LoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)

        extra_info = {'body': {}, 'status': None, 'resp': {}}

        async def receive_wrapper():
            message = await receive()
            if message['type'] == 'http.request':
                try:
                    extra_info['body'] = json.loads(message['body'].decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            return message

        async def send_wrapper(message: Message) -> None:
            if message['type'] == 'http.response.start':
                extra_info['status'] = message['status']
            if message['type'] == 'http.response.body':
                try:
                    extra_info['resp'] = json.loads(message['body'].decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            await send(message)

        set_request_start_time()
        set_session_provider()
        set_message_queue_publisher()
        set_trace_id()

        await self.app(scope, receive_wrapper, send_wrapper)

        await log_request(extra_info)
        set_token_info()


def serve():
    setup_logging()

    # 原因
    # 1. swagger ui 的 api 測試網址是使用 base_path
    # 2. 線上 istio 的設定， domain.com/xxx-service/... -> xxx-service/...
    #
    # 為了讓線上的 swagger ui 可以正常測試
    # 1. 多提供一份 api，路徑(gateway_base_path)為 `config.gateway_prefix + base_path`
    # 2. 將 swagger ui 的 json url 改為 `config.gateway_prefix + gateway_base_path + '/openapi.json'`

    base_path = '/api'
    gateway_base_path = config.gateway_prefix + base_path
    swagger_ui_config = {}
    swagger_ui_config['url'] = config.gateway_prefix + gateway_base_path + '/openapi.json'
    swagger_ui_options = SwaggerUIOptions(swagger_ui_config=swagger_ui_config)
    openapi_spec_dir = 'app/port/restful/openapi'

    app = AsyncApp(
        __name__,
        specification_dir=openapi_spec_dir,
        swagger_ui_options=swagger_ui_options
    )

    root = Path(openapi_spec_dir + '/api.yml')
    parser = ResolvingParser(
        str(root.absolute()),
        lazy=True,
        backend='openapi-spec-validator'
    )
    parser.parse()
    specification = modified_version(route_toggle(parser.specification))

    app.add_middleware(
        CORSMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LoggingMiddleware)

    for p in set([base_path, gateway_base_path]):
        app.add_api(
            specification,
            base_path=p,
            strict_validation=True,
            validate_responses=True,
            pythonic_params=True,
        )
    app.add_error_handler(ProblemException, render_problem_exception)

    # https://stackoverflow.com/questions/22192519/detect-if-flask-is-being-run-via-gunicorn
    if 'gunicorn' not in os.environ.get('SERVER_SOFTWARE', ''):
        app.run(port=int(config.port))
    else:
        return app


if __name__ == '__main__':
    serve()
