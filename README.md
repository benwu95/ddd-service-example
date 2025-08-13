# An example about DDD Service
Based on Domain-Driven Design and Event-Driven architecture, and using the following technologies
- web framework: [Connexion](https://connexion.readthedocs.io/en/stable/)
- server workers: [Gunicorn](https://docs.gunicorn.org/en/latest/index.html) with [Uvicorn worker](https://github.com/Kludex/uvicorn-worker)
- ORM: [SQLAlchemy](https://docs.sqlalchemy.org/en/20/)
- database migration tool: [Alembic](https://alembic.sqlalchemy.org/en/latest/)
- message queue: [pika](https://pika.readthedocs.io/en/stable/)

## Develop new service
### Prepare Python virtual env
- python: version >= `3.11`
- pyenv: https://github.com/pyenv/pyenv
- pyenv-virtualenv: https://github.com/pyenv/pyenv-virtualenv
```sh
pyenv virtualenv new-service
pyenv activate new-service
pip install pip wheel setuptools -U
pip install -r requirements_local.txt
```
### Init
1. `cd /path/to/new-service`
2. `python /path/to/ddd-service-example/copy_tool.py init`
3. `pip install -r requirements.txt -r requirements_local.txt -r requirements_test.txt`
4. update setting in `app/config.py`
    - `database_url`
    - `postgres_schema`
    - `rabbitmq_exchange_name`
    - `rabbitmq_consumer_name`

### Add bounded context
1. `python /path/to/ddd-service-example/copy_tool.py add bounded_context_name`
2. start coding
    - value object
    - event
    - entity
    - use case
    - orm
    - repository
    - controller
    - event handler
    - handler
    - swagger (openapi)

### Add message queue exchange handler
1. `python /path/to/ddd-service-example/copy_tool.py add_message_queue_handler exchange_name`
2. start coding
    - payload
    - exchange handler
    - `app/message_queue_consumer.py`

### Set local PostgreSQL database
1. use `database_username`, `database_password` in `app/config.py` to create local PostgreSQL database
```sh
# if database_username is `postgres`
brew install postgresql@15
brew services start postgresql@15
createuser -P -d postgres
createdb -O "postgres" default
```

### Update local database
1. `make build-migration message='migration message'`
2. `make migrate-database`

### Set local RabbitMQ
`docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 -e RABBITMQ_DEFAULT_USER=root -e RABBITMQ_DEFAULT_PASS=1234 rabbitmq:management`

### Run locally
- server: `make local-run`
- mq consumer: `make local-run-consumer`

### Debugging in VSCode
1. select the Debugging icon > Run and Debug
