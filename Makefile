SHELL := /bin/bash

.PHONY: venv install-dev hooks lint fmt check run

venv:
	python3 -m venv .venv

install-dev:
	source .venv/bin/activate && python -m pip install --upgrade pip
	source .venv/bin/activate && pip install -r requirements.txt
	source .venv/bin/activate && pip install -e '.[dev]'

hooks:
	source .venv/bin/activate && pre-commit install

lint:
	source .venv/bin/activate && pre-commit run --all-files --show-diff-on-failure

fmt:
	source .venv/bin/activate && pre-commit run black --all-files
	source .venv/bin/activate && pre-commit run isort --all-files
	source .venv/bin/activate && pre-commit run ruff-format --all-files
	source .venv/bin/activate && pre-commit run ruff --all-files

check: lint

run:
	source .venv/bin/activate && PYTHONPATH=src python -m album_print_flow
