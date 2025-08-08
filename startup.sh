#!/bin/bash

case $STARTUP_MODE in
    "RESTFUL")
        gunicorn
        ;;
    "DB_MIGRATE")
        pip3 install alembic
        alembic upgrade head
        ;;
    "CONSUMER")
        python app/message_queue_consumer.py
        ;;
    *)
        gunicorn
        ;;
esac
