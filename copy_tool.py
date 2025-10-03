import argparse
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

root = Path(__file__).parent.resolve()
cwd = Path().cwd()


def init():
    # init alembic
    subprocess.run(["alembic", "init", cwd.joinpath("alembic")])

    # copy
    ignore_patterns = shutil.ignore_patterns(
        "__pycache__", "tests", "tests.py", ".coverage", ".pytest_cache"
    )
    copy_templates = [
        ".vscode",
        "alembic/env.py",
        "app/adapter/controller/base.py",
        "app/adapter/event_handler/helper.py",
        "app/adapter/repository/orm/base.py",
        "app/adapter/repository/orm/domain_event_model.py",
        "app/adapter/repository/base.py",
        "app/core/ddd_base",
        "app/port/restful/handler/health.py",
        "app/port/restful/handler/token.py",
        "app/port/restful/openapi/components/responses",
        "app/port/restful/openapi/components/schemas/auth.yml",
        "app/port/restful/openapi/paths/health.yml",
        "app/port/restful/response.py",
        "app/port/storage",
        "app/config.py",
        "app/logger.py",
        "app/package_instance.py",
        "app/restful_server.py",
        "app/trace.py",
        "tests/conftest.py",
        "tests/utils/rabbitmq_test_helper.py",
        "packages",
        ".gitignore",
        "Dockerfile",
        "alembic.ini",
        "gunicorn.conf.py",
        "pyproject.toml",
        "requirements_local.txt",
        "requirements_test.txt",
        "requirements.txt",
        "startup.sh",
    ]
    for template in copy_templates:
        if not cwd.joinpath(template).parent.exists():
            cwd.joinpath(template).parent.mkdir(parents=True, exist_ok=True)
        if root.joinpath(template).is_dir():
            if cwd.joinpath(template).exists():
                shutil.rmtree(cwd.joinpath(template))
            shutil.copytree(root.joinpath(template), cwd.joinpath(template), ignore=ignore_patterns)
        else:
            shutil.copyfile(root.joinpath(template), cwd.joinpath(template))

    # update startup.sh file mode
    p = cwd.joinpath("startup.sh")
    p.chmod(0o755)

    # copy and update service name
    service_name = cwd.name
    with (
        open(root.joinpath("Makefile"), "r") as fin,
        open(cwd.joinpath("Makefile"), "w") as fout,
    ):
        content = fin.read()
        content = content.replace("ddd-service", cwd.name)
        fout.write(content)
    with (
        open(root.joinpath("app/config.py"), "r") as fin,
        open(cwd.joinpath("app/config.py"), "w") as fout,
    ):
        content = fin.read()
        content = content.replace("ddd-service", service_name)
        content = content.replace("ddd_service", service_name.replace("-", "_"))
        fout.write(content)
    with (
        open(root.joinpath("app/message_queue_consumer.py"), "r") as fin,
        open(cwd.joinpath("app/message_queue_consumer.py"), "w") as fout,
    ):
        content = fin.read()
        content = content.replace("ddd-service", service_name)
        fout.write(content)
    with (
        open(root.joinpath("app/port/restful/openapi/api.yml"), "r") as fin,
        open(cwd.joinpath("app/port/restful/openapi/api.yml"), "w") as fout,
    ):
        content = fin.read()
        content = content.replace("Your Service API", f'{cwd.name.replace("-", " ").title()} API')
        fout.write(content)

    # create __init__.py
    need_init_dirs = [
        "app/adapter/controller",
        "app/adapter/event_handler",
        "app/adapter/repository/orm",
        "app/adapter/repository",
        "app/adapter",
        "app/core",
        "app/port/message_queue",
        "app/port/restful",
        "app/port",
        "app",
        "tests",
        "tests/app/adapter/controller",
        "tests/utils",
    ]
    for d in need_init_dirs:
        Path(cwd.joinpath(d)).mkdir(parents=True, exist_ok=True)
        Path(cwd.joinpath(d, "__init__.py")).touch()

    # update __init__.py
    with open(cwd.joinpath("app/adapter/event_handler/__init__.py"), "w") as f:
        f.writelines(
            [
                "__all__ = []\n",
            ]
        )

    with open(cwd.joinpath("app/adapter/repository/orm/__init__.py"), "w") as f:
        f.writelines(
            [
                "from .base import ArchiveMixin, Base, BaseMixin\n",
                "from .domain_event_model import DomainEventModel\n",
            ]
        )

    with open(cwd.joinpath("app/adapter/__init__.py"), "w") as f:
        f.writelines(
            [
                "import app.adapter.event_handler\n",
            ]
        )


def add(name: str):
    def snake_to_pascal_case(s: str):
        return s.title().replace("_", "")

    def replace_path_by_name(path: Path):
        new_path = str(path.resolve())
        new_path = new_path.replace(str(root.resolve()), str(cwd.resolve()))
        new_path = new_path.replace("your_bounded_context", name)
        new_path = new_path.replace("your_aggregate", name)

        return Path(new_path)

    def copy_file(paths: Iterable[Path]):
        for path in paths:
            if path.is_dir():
                copy_file(path.rglob("*.py"))
                copy_file(path.rglob("*.yml"))
            else:
                dst = replace_path_by_name(path)
                if not dst.parent.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)

                with open(path, "r") as fin, open(dst, "w") as fout:
                    content = fin.read()
                    content = content.replace("your_bounded_context", name)
                    content = content.replace("your_aggregate", name)
                    content = content.replace("YourAggregate", snake_to_pascal_case(name))
                    content = content.replace("Your Aggregate", name.title().replace("_", " "))
                    fout.write(content)

    templates = [
        "app/adapter/controller/your_bounded_context",
        "app/adapter/event_handler/your_aggregate_event_handler.py",
        "app/adapter/repository/orm/your_aggregate_model.py",
        "app/adapter/repository/your_aggregate_repository.py",
        "app/core/your_bounded_context",
        "app/port/restful/handler/your_bounded_context",
        "app/port/restful/openapi/components/schemas/your_aggregate",
        "app/port/restful/openapi/paths/your_aggregates",
    ]

    copy_file([root.joinpath(t) for t in templates])

    with open(cwd.joinpath("app/adapter/controller/__init__.py"), "a") as f:
        f.writelines(
            [
                f"from .{name}.{name}_controller import {snake_to_pascal_case(name)}Controller\n",
                f"{name}_controller = {snake_to_pascal_case(name)}Controller()\n",
            ]
        )

    with open(cwd.joinpath("app/adapter/event_handler/__init__.py"), "a") as f:
        f.writelines(
            [
                f"from .{name}_event_handler import {snake_to_pascal_case(name)}EventHandler\n",
                f"__all__.append('{snake_to_pascal_case(name)}EventHandler')\n",
            ]
        )

    with open(cwd.joinpath("app/adapter/repository/orm/__init__.py"), "a") as f:
        f.write(
            f"from .{name}_model import {snake_to_pascal_case(name)}Model, {snake_to_pascal_case(name)}ArchiveModel\n"
        )


def add_message_queue_handler(name: str):
    def replace_path_by_name(path: Path):
        new_path = str(path.resolve())
        new_path = new_path.replace(str(root.resolve()), str(cwd.resolve()))
        new_path = new_path.replace("your_exchange", name)

        return Path(new_path)

    def copy_file(paths: Iterable[Path]):
        for path in paths:
            if path.is_dir():
                copy_file(path.rglob("*.py"))
            else:
                dst = replace_path_by_name(path)
                if not dst.parent.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)

                with open(path, "r") as fin, open(dst, "w") as fout:
                    content = fin.read()
                    content = content.replace("your_exchange", name)
                    fout.write(content)

    templates = [
        "app/port/message_queue/your_exchange",
    ]

    copy_file([root.joinpath(t) for t in templates])

    with open(cwd.joinpath("app/port/message_queue/__init__.py"), "a") as f:
        f.writelines(
            [
                f"from .{name}.{name}_handler import {name}_handler\n",
            ]
        )


if __name__ == "__main__":
    main_parser = argparse.ArgumentParser()

    sub_parsers = main_parser.add_subparsers(dest="command", help="commands")

    init_parser = sub_parsers.add_parser("init", help="init by ddd service template")

    add_parser = sub_parsers.add_parser("add", help="add new bounded context")
    add_parser.add_argument("name", help="snake case naming")

    add_message_queue_parser = sub_parsers.add_parser(
        "add_message_queue_handler", help="add new message queue handler"
    )
    add_message_queue_parser.add_argument("name", help="snake case naming")

    args = main_parser.parse_args()
    match args.command:
        case "init":
            init()
            print("init success")
        case "add":
            add(args.name)
            print("add success")
        case "add_message_queue_handler":
            add_message_queue_handler(args.name)
            print("add success")
