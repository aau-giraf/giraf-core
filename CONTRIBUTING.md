# Contributing to GIRAF Core

Thank you for your interest in contributing to GIRAF Core, the shared domain service for the GIRAF platform.

## Development Setup

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (for PostgreSQL)

### Getting Started

```bash
# Clone the repository
git clone https://github.com/aau-giraf/giraf-core.git
cd giraf-core

# Install dependencies (including dev tools)
uv sync --all-extras

# Start PostgreSQL
docker compose up -d core-db

# Run migrations
uv run python manage.py migrate

# Start the development server
uv run python manage.py runserver
# API docs available at http://localhost:8000/api/v1/docs
```

## Code Style

We use automated tooling to maintain consistency:

```bash
# Lint
uv run ruff check .

# Auto-fix lint issues
uv run ruff check --fix .

# Format
uv run ruff format .

# Type check
uv run mypy apps/ config/ core/
```

All checks must pass before merging. CI enforces these automatically.

## Architecture Pattern

Every Django app follows the same structure:

```
apps/<app_name>/
  models.py      # Data models
  schemas.py     # Pydantic input/output schemas (django-ninja)
  services.py    # Business logic (never in endpoints)
  api.py         # HTTP endpoints (thin layer calling services)
  tests/         # Tests
```

**Key rules:**
- Business logic goes in `services.py`, never in `api.py`
- Endpoints are thin wrappers: validate input, call service, return response
- New routers are registered in `config/api.py`

## Testing

```bash
# Run all tests
uv run pytest

# Run tests for a specific app
uv run pytest apps/users/ -v

# Run with coverage
uv run pytest --cov=apps --cov=core --cov-report=term-missing
```

Tests use SQLite in-memory (`config/settings/test.py`) — no external dependencies required.

## Pull Request Workflow

1. Fork the repository and create a feature branch
2. Make your changes following the architecture pattern above
3. Add tests for new functionality
4. Ensure all checks pass: `uv run ruff check . && uv run ruff format --check . && uv run mypy apps/ config/ core/ && uv run pytest`
5. Open a PR against `main` with a clear description of the change
