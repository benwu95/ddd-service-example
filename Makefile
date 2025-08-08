.PHONY: all

# test
.PHONY: check-style unit-test

# local
.PHONY: local-run migrate-database build-migration

# deployment
.PHONY: build build-dev build-stg build-fix check-deploy

GIT_COMMIT := $(shell git rev-parse --short HEAD)
GIT_COMMIT_DATE := $(shell git show -s --date=format:'%Y-%m-%d' --format=%cd)
PUBLISH_DATE := $(shell TZ='Asia/Taipei' date +%Y%m%d-%H%M%S)
PUBLISH_DATE_TIMESTAMP := $(shell TZ='Asia/Taipei' date +%s)
COMPONENT_VERSION := $(shell git describe --always --tags)
GAR := 
IMAGE_NAME := ddd-service-template
K8S_NAMESPACE := default

export PYTHONPATH = ./
export DEPLOYMENT_TYPE = LOCAL
export SWAGGER_VERSION = LOCAL

# build/deployment setting
export PORT = 8080

define add_tag_with_env
	docker pull ${GAR}/${IMAGE_NAME}:${GIT_COMMIT}
	docker tag ${GAR}/${IMAGE_NAME}:${GIT_COMMIT} ${GAR}/${IMAGE_NAME}:${GIT_COMMIT}-$(1)
	docker push ${GAR}/${IMAGE_NAME}:${GIT_COMMIT}-$(1)
endef


all:
	@echo ${GIT_COMMIT}
	@echo ${COMPONENT_VERSION}

check-style:
	@echo "check-style"
	pycodestyle --ignore=E203,E265,E402,E501,E722,W503 app/ tests/

unit-test:
	@echo "unit-test"
	pytest tests --cov -s --cov-report=term-missing
	coverage xml

build:
	@echo "build"
	@echo ${GAR}/${IMAGE_NAME}:${GIT_COMMIT}

	docker build \
		--build-arg PORT_VAR=${PORT} \
		--build-arg PYTHONPATH_VAR=/${IMAGE_NAME} \
		-t ${IMAGE_NAME} .
	docker tag ${IMAGE_NAME} ${GAR}/${IMAGE_NAME}:${GIT_COMMIT}
	docker push ${GAR}/${IMAGE_NAME}:${GIT_COMMIT}

build-dev:
	@echo "build-dev"
	@echo ${GAR}/${IMAGE_NAME}:${GIT_COMMIT}-dev

	$(call add_tag_with_env,dev)

build-stg:
	@echo "build-stg"
	@echo ${GAR}/${IMAGE_NAME}:${GIT_COMMIT}-stage

	$(call add_tag_with_env,stage)

build-fix:
	@echo "build-fix"
	@echo ${GAR}/${IMAGE_NAME}:${GIT_COMMIT}-hotfix

	$(call add_tag_with_env,hotfix)

add-publish-date-tag:
	@echo "add-publish-date-tag"

	docker pull ${GAR}/${IMAGE_NAME}:${GIT_COMMIT}
	docker tag ${GAR}/${IMAGE_NAME}:${GIT_COMMIT} ${GAR}/${IMAGE_NAME}:${PUBLISH_DATE}
	docker push ${GAR}/${IMAGE_NAME}:${PUBLISH_DATE}

check-deploy:
	@echo "check-deploy"
	@for name in ${DEPLOYMENT_NAME};do kubectl rollout status deployment $$name --namespace="${K8S_NAMESPACE}" || (kubectl rollout undo deployment $$name --namespace="${K8S_NAMESPACE}"; exit 1); done

local-build:
	@echo "build"
	@echo ${GAR}/${IMAGE_NAME}:${GIT_COMMIT}

	docker build \
		--build-arg PORT_VAR=${PORT} \
		--build-arg PYTHONPATH_VAR=/${IMAGE_NAME} \
		-t ${IMAGE_NAME} .

local-run:
	gunicorn

local-run-consumer:
	python app/message_queue_consumer.py

local-test:
	pytest tests --cov -s --cov-report=term-missing

isort-and-black:
	isort app/ tests/ packages/
	black app/ tests/ packages/

migrate-database:
	alembic upgrade head

build-migration:
	alembic revision --autogenerate -m '$(message)'
