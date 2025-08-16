import copy
import json
import logging
import sys

from app.config import DeploymentType, config
from app.trace import get_trace_id, token_info


def get_log_formatter() -> logging.Formatter:
    if config.deployment_type != DeploymentType.LOCAL:
        # append } in format()
        return GoogleCloudLoggingExceptionFormatter(
            r'{"timestamp": "%(asctime)s", '
            r'"severity": "%(levelname)s", '
            r'"logging.googleapis.com/sourceLocation": {"file": "%(filename)s", "line": "%(lineno)d", "function": "%(funcName)s"}, '
            r'"logger": "%(name)s", '
            r'"message": %(message)s'
        )
    return logging.Formatter(
        r"[%(asctime)s] %(levelname)s [%(filename)s:%(lineno)d %(funcName)s] %(message)s"
    )


def get_console_handler() -> logging.StreamHandler:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(get_log_formatter())

    return console_handler


def setup_logger(logger: logging.Logger):
    logger.setLevel(logging.INFO)

    # add a console handler
    logger.addHandler(get_console_handler())


def setup_logging():
    # if logger does not have handler, and `propagate` is True (default value),
    # the message will propagate up to the root logger
    root_logger = logging.getLogger()
    setup_logger(root_logger)

    console_handler = get_console_handler()

    # set packages logging
    logging.getLogger("pika").setLevel(logging.WARNING)
    logging.getLogger("pika").addHandler(console_handler)
    logging.getLogger("connexion.decorators.validation").addHandler(console_handler)


class ServiceLogger(logging.Logger):
    def __init__(self, name):
        super().__init__(name)
        setup_logger(self)


class GoogleCloudLoggingExceptionFormatter(logging.Formatter):
    def formatException(self, ei):
        # custom exception format
        traceback_msg_list = super().formatException(ei).replace('"', "'").split("\n")
        traceback_msg = f', "excInfo": {json.dumps(traceback_msg_list, ensure_ascii=False)}'
        return traceback_msg

    def format(self, record):
        recordcopy = copy.copy(record)
        msg_list = str(recordcopy.getMessage()).replace('"', "'").split("\n")
        if len(msg_list) == 1:
            msg_list = msg_list[0]
        recordcopy.msg = json.dumps(msg_list, ensure_ascii=False)
        recordcopy.args = ()

        extra_info_str = ""

        trace_id = getattr(recordcopy, "traceId", get_trace_id())
        extra_info_str += f', "traceId": "{trace_id}"'
        extra_info_str += f', "logging.googleapis.com/trace": "{trace_id.replace("-", "")}"'

        http_request = getattr(recordcopy, "httpRequest", {})
        extra_info_str += f', "httpRequest": {json.dumps(http_request)}'

        if token_info:
            t = token_info.serialize()
            t.pop("raw_token")
            extra_info_str += f', "tokenInfo": {json.dumps(t)}'

        detail = getattr(recordcopy, "detail", {})
        if not isinstance(detail, (dict, list)):
            detail = str(detail).replace('"', "'").split("\n")

        MAX_DETAIL_LENGTH = 190000
        detail_str = json.dumps(detail, ensure_ascii=False)
        detail_parts = len(detail_str) // MAX_DETAIL_LENGTH + 1
        if detail_parts > 1:
            log_str = ""
            for i in range(detail_parts):
                part_str = detail_str[i * MAX_DETAIL_LENGTH : (i + 1) * MAX_DETAIL_LENGTH]
                extra_info_str = f', "part": "{i + 1}/{detail_parts}", "detail": {json.dumps(part_str, ensure_ascii=False)}'
                log_str += super().format(recordcopy).replace("\n", "") + extra_info_str + "}\n"
        else:
            extra_info_str += f', "detail": {detail_str}'
            log_str = super().format(recordcopy).replace("\n", "") + extra_info_str + "}"

        return log_str
