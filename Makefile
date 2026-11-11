PYTHON ?= .venv/bin/python
DC = docker compose --env-file .env.docker
.PHONY: lint test ci gate doctor docker-env build up down docker-test smoke
lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
test:
	$(PYTHON) -m pytest -q
ci:
	$(PYTHON) scripts/run_checks.py
gate:
	$(PYTHON) -m querypilot.evaluation.gate
doctor:
	$(PYTHON) -m querypilot.cli doctor --reference-date 2026-10-27
docker-env:
	$(PYTHON) scripts/prepare_docker.py
build:
	$(DC) build
up:
	$(DC) up --build --wait --wait-timeout 180
down:
	$(DC) down --timeout 40
docker-test:
	$(DC) -p querypilot_day12_test -f compose.yaml -f compose.test.yaml run --build --rm tests
smoke:
	$(DC) exec -T backend python -m querypilot.services.container_smoke
