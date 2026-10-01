.PHONY: setup build up identity gateway down logs update-actions

PYTHON ?= python3

setup:
	$(PYTHON) scripts/setup.py

# Bump every SHA-pinned GitHub Action in .github/workflows to its latest
# release, keeping the `# vX.Y.Z` comment in sync. Requires pinact
# (brew install pinact); set GITHUB_TOKEN to avoid API rate limits.
update-actions:
	pinact run -u

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
