.PHONY: install test lint lint-fix typecheck shellcheck lock-check check ui ui-edit ui-check

install:
	uv sync

test:
	uv run pytest -q

lint:
	uv run ruff check src/ tests/ ui/
	uv run ruff format --check src/ tests/ ui/

# Applies the lint fixes and formatting that ruff can do on its own.
lint-fix:
	uv run ruff check --fix src/ tests/ ui/
	uv run ruff format src/ tests/ ui/

typecheck:
	uv run mypy src/

shellcheck:
	uv run shellcheck check.sh

# uv.lock matches pyproject.toml.
lock-check:
	uv lock --check

check:
	./check.sh

# The pruning UI as an app, or as a notebook to change it: see docs/ui.md.
ui:
	uv run --group ui marimo run ui/pruning.py

ui-edit:
	uv run --group ui marimo edit ui/pruning.py

ui-check:
	uv run --group ui marimo check ui/pruning.py
