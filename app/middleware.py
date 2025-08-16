import json
import time

from connexion import request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.adapter.repository.base import set_session_provider
from app.logger import ServiceLogger
from app.package_instance import set_message_queue_publisher
from app.trace import (
    request_start_time,
    set_request_start_time,
    set_token_info,
    set_trace_id,
)


class LoggingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = ServiceLogger(self.__class__.__name__)
        self.no_log_post_urls = []

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        extra_info = {"body": {}, "status": None, "resp": {}}

        async def receive_wrapper():
            message = await receive()
            if message["type"] == "http.request":
                try:
                    extra_info["body"] = json.loads(message["body"].decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            return message

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                extra_info["status"] = message["status"]
            if message["type"] == "http.response.body":
                try:
                    extra_info["resp"] = json.loads(message["body"].decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            await send(message)

        set_request_start_time()
        set_session_provider()
        set_message_queue_publisher()
        set_trace_id()

        await self.app(scope, receive_wrapper, send_wrapper)

        await self.log_request(extra_info)
        set_token_info()

    async def log_request(self, extra_info: dict):
        url = request.url.path
        method = request.method
        remote_addr = request.client.host
        status_code = extra_info["status"]
        protocol = f'HTTP/{request.scope["http_version"]}'
        http_request_gcloud_info = {
            "requestMethod": method,
            "requestUrl": url,
            "status": status_code,
            "userAgent": request.headers["user-agent"],
            "remoteIp": remote_addr,
            "protocol": protocol,
        }
        body = extra_info["body"]
        resp = {}
        if (method == "POST" and url not in self.no_log_post_urls) or status_code >= 400:
            resp = extra_info["resp"]
        if request_start_time:
            http_request_gcloud_info["latency"] = f"{time.time() - request_start_time:6f}s"
        self.logger.info(
            '%s - - "%s %s %s" %s -',
            remote_addr,
            method,
            url,
            protocol,
            status_code,
            extra={
                "httpRequest": http_request_gcloud_info,
                "detail": {"request": body, "response": resp},
            },
        )
