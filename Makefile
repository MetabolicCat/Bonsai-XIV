.PHONY: install test lint lint-fix typecheck shellcheck lock-check check

install:
	uv sync

test:
	uv run pytest -q

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

# Applies the lint fixes and formatting that ruff can do on its own.
lint-fix:
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/

typecheck:
	uv run mypy src/

shellcheck:
	uv run shellcheck check.sh

# uv.lock matches pyproject.toml.
lock-check:
	uv lock --check

check:
	./check.sh
