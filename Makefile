.PHONY: help up down test lint format

help:
	@echo "Available targets:"
	@echo "  up      - start mongo container (docker compose up -d)"
	@echo "  down    - stop mongo container (docker compose down)"
	@echo "  test    - run the test suite"
	@echo "  lint    - run ruff lint checks"
	@echo "  format  - run ruff formatter"

up:
	docker compose up -d

down:
	docker compose down

test:
	.venv/bin/python -m pytest tests/ -v

lint:
	pre-commit run --all-files
