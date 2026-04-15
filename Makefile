.PHONY: install test run migrate cleanup compose-up compose-down

install:
	python3 -m venv .venv
	.venv/bin/pip install -e '.[dev]'

test:
	.venv/bin/pytest -q

run:
	.venv/bin/uvicorn app.main:app --reload

migrate:
	.venv/bin/alembic upgrade head

cleanup:
	.venv/bin/python -m app.cli.cleanup

compose-up:
	cp -n .env.example .env || true
	docker compose up --build

compose-down:
	docker compose down
