.PHONY: setup build up identity gateway down logs

PYTHON ?= python3

setup:
	$(PYTHON) scripts/setup.py

build:
	$(PYTHON) scripts/dependencies.py --build oauth2-proxy
	$(PYTHON) scripts/dependencies.py --build keycloak

identity:
	docker compose up -d keycloak

gateway:
	docker compose up -d oauth2-proxy

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs --follow --tail=100
