# https://docs.gunicorn.org/en/stable/settings.html

import os

from app.package_instance import message_queue_publisher

wsgi_app = 'app.restful_server:serve()'
worker_class = 'uvicorn_worker.UvicornH11Worker'  # ref: https://github.com/Kludex/uvicorn-worker/issues/22
workers = os.environ.get('GUNICORN_WORKERS', 2)
timeout = os.environ.get('GUNICORN_TIMEOUT', 30)
max_requests = 1000
max_requests_jitter = 50
keepalive = 5
preload_app = True


def post_worker_init(worker):
    pass


def worker_exit(server, worker):
    if message_queue_publisher.messages:
        message_queue_publisher.publish_messages()


def on_exit(server):
    if message_queue_publisher.messages:
        message_queue_publisher.publish_messages()
