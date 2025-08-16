import os
from copy import deepcopy
from pathlib import Path

from connexion import AsyncApp
from connexion.exceptions import ProblemException
from connexion.middleware import MiddlewarePosition
from connexion.options import SwaggerUIOptions
from prance import ResolvingParser
from starlette.middleware.cors import CORSMiddleware

from app.config import config
from app.logger import ServiceLogger, setup_logging
from app.middleware import LoggingMiddleware
from app.port.restful.response import render_problem_exception

logger = ServiceLogger(__name__)


def modified_version(specification) -> dict:
    result = deepcopy(specification)

    if config.swagger_version:
        result["info"]["version"] = config.swagger_version

    return result


# Remove swagger yml with x-dev: true while on production
def route_toggle(specification):
    result = deepcopy(specification)

    if config.enable_dev_route != "true":
        for route, defines in specification["paths"].items():
            for method, schema in defines.items():
                if "x-dev" in schema:
                    result["paths"][route].pop(method, None)
    return result


def serve():
    setup_logging()

    # Reason:
    # 1. The API test URL in Swagger UI uses base_path.
    # 2. In the online Istio configuration, domain.com/xxx-service/... -> xxx-service/...
    #
    # To allow the online Swagger UI to work properly:
    # 1. Provide an additional API whose path (gateway_base_path) is `config.gateway_prefix + base_path`.
    # 2. Change the Swagger UI's JSON URL to `config.gateway_prefix + gateway_base_path + '/openapi.json'`.

    base_path = "/api"
    gateway_base_path = config.gateway_prefix + base_path
    swagger_ui_config = {}
    swagger_ui_config["url"] = config.gateway_prefix + gateway_base_path + "/openapi.json"
    swagger_ui_options = SwaggerUIOptions(swagger_ui_config=swagger_ui_config)
    openapi_spec_dir = "app/port/restful/openapi"

    app = AsyncApp(
        __name__,
        specification_dir=openapi_spec_dir,
        swagger_ui_options=swagger_ui_options,
    )

    root = Path(openapi_spec_dir + "/api.yml")
    parser = ResolvingParser(str(root.absolute()), lazy=True, backend="openapi-spec-validator")
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
    if "gunicorn" not in os.environ.get("SERVER_SOFTWARE", ""):
        app.run(port=int(config.port))
    else:
        return app


if __name__ == "__main__":
    serve()
