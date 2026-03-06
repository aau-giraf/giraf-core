```
 ██████╗ ██╗██████╗  █████╗ ███████╗     ██████╗ ██████╗ ██████╗ ███████╗
██╔════╝ ██║██╔══██╗██╔══██╗██╔════╝    ██╔════╝██╔═══██╗██╔══██╗██╔════╝
██║  ███╗██║██████╔╝███████║█████╗      ██║     ██║   ██║██████╔╝█████╗
██║   ██║██║██╔══██╗██╔══██║██╔══╝      ██║     ██║   ██║██╔══██╗██╔══╝
╚██████╔╝██║██║  ██║██║  ██║██║         ╚██████╗╚██████╔╝██║  ██║███████╗
 ╚═════╝ ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝          ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝
  Django + Ninja  │  PostgreSQL  │  JWT Auth  │  Python 3.12+
```

# GIRAF Core API

Shared domain service for the GIRAF platform — manages users, organizations, citizens, grades, pictograms, invitations, and JWT authentication.

## How Other Apps Use Core

GIRAF Core is the **single source of truth** for all shared data. The platform has three app-specific backends (Weekplanner, Food Planner, VTA), and they all depend on Core rather than duplicating user/org/citizen management:

1. **Users log in through Core.** A mobile app calls `POST /api/v1/token/pair` with username + password. Core returns a JWT access token that contains an `org_roles` claim — a dictionary like `{"1": "owner", "5": "member"}` mapping organization IDs to the user's role.

2. **App backends validate JWTs locally.** They share the same `JWT_SECRET` as Core, so they can decode and verify tokens without making a network call. The `org_roles` claim inside the token tells them what the user is allowed to do — no need to query Core on every request.

3. **App backends call Core for shared data.** When the Weekplanner backend needs to verify that a citizen exists before creating an activity, it calls Core's API (e.g. `GET /api/v1/citizens/{id}`). Core is the authority — app backends never store their own copy of users, orgs, or citizens.

4. **Each app stores only its own domain data.** Weekplanner stores activities and schedules. VTA stores exercises and progress. Food Planner stores meals and menus. Each has its own database. Core holds everything shared.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Mobile Apps (Expo / React Native)            │
│   Weekplanner          Food Planner          VTA               │
└──────┬──────────────────────┬───────────────────┬──────────────┘
       │ domain data          │ domain data       │ domain data
       ▼                      ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
│ Weekplanner  │   │ Food Planner │   │ VTA Backend      │
│ Backend      │   │ Backend      │   │                  │
│ (.NET 8)     │   │ (planned)    │   │ (.NET + SignalR) │
│ Activities,  │   │ Meals, Menus │   │ Exercises,       │
│ Schedules    │   │ Nutrition    │   │ Progress         │
└──────┬───────┘   └──────┬───────┘   └──────┬───────────┘
       │                  │                   │
       │  users, orgs, citizens, pictograms   │
       ▼                  ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GIRAF Core API  ← (this repo)               │
│                    (Django + Ninja, Python)                     │
│                                                                 │
│  Auth/JWT │ Users │ Orgs │ Citizens │ Grades │ Pictos │ Invites │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                    ┌─────▼─────┐
                    │  Core DB  │
                    │ PostgreSQL│
                    └───────────┘
```

## Quick Start

```bash
# Install dependencies (requires uv — https://docs.astral.sh/uv/)
uv sync --all-extras

# Start the PostgreSQL database
docker compose up -d core-db

# Run database migrations
uv run python manage.py migrate

# Create a superuser (for Django Admin at /admin)
uv run python manage.py createsuperuser

# Start the dev server
uv run python manage.py runserver
# API at http://localhost:8000/api/v1/docs
```

Or run everything via Docker Compose:

```bash
docker compose up
# API at http://localhost:8000
```

## Architecture

### Stack

- **Python 3.12+** with **Django 5** and **Django Ninja** (fast, type-safe API layer)
- **PostgreSQL 16** (dev/prod) — **SQLite in-memory** for tests
- **JWT authentication** via django-ninja-jwt (access tokens: 1 hour, refresh tokens: 7 days)
- **`uv`** as the package manager

### Design Pattern: Service Layer

Every Django app in this project follows the same four-file structure:

```
models.py  →  schemas.py  →  services.py  →  api.py
```

Here's what each file does and why:

- **`models.py`** — Django ORM models. Defines the database tables and relationships.
- **`schemas.py`** — Pydantic-based input/output schemas (via Django Ninja). Defines what data the API accepts and returns. Keeps serialization separate from business logic.
- **`services.py`** — **All business logic lives here.** Services are static methods wrapped in `@transaction.atomic`. They raise domain exceptions (not HTTP errors) when something goes wrong.
- **`api.py`** — Thin endpoint layer. Each endpoint does three things: (1) check permissions, (2) call a service method, (3) return the response. No business logic here.

This separation matters because:
- Business rules are testable without HTTP — you can unit-test services directly.
- Endpoints stay small and consistent.
- When a rule changes, you know exactly where to look.

### Error Handling

Services raise domain exceptions from `core/exceptions.py`. These are caught by centralized exception handlers in `config/api.py` and mapped to HTTP status codes:

| Exception                  | HTTP Status | When to use                              |
| -------------------------- | ----------- | ---------------------------------------- |
| `BadRequestError`          | 400         | Invalid input that isn't a validation issue |
| `PermissionDeniedError`    | 403         | User lacks required role or permission   |
| `ResourceNotFoundError`    | 404         | Entity doesn't exist                     |
| `ConflictError`            | 409         | Duplicate resource (e.g. username taken) |
| `BusinessValidationError`  | 422         | Domain validation failure                |
| `ServiceError`             | 500         | Unexpected internal error                |

All error responses use the same shape: `{"detail": "Human-readable message"}`.

### Role System

Roles are per-organization, stored in the `Membership` model. The hierarchy is:

```
owner  >  admin  >  member
```

A permission check for `min_role=admin` will pass for both admins **and** owners. This is handled by `check_role_or_raise()` in `core/permissions.py`, which every endpoint calls before delegating to the service layer.

| Role       | Capabilities                                             |
| ---------- | -------------------------------------------------------- |
| **member** | Read org data, create/update citizens                    |
| **admin**  | + invite users, manage grades/pictograms, remove members |
| **owner**  | + update/delete org, change member roles                 |

### JWT Authentication

When a user logs in (`POST /api/v1/token/pair`), Core returns an access token with a custom `org_roles` claim embedded in the JWT payload:

```json
{
  "org_roles": {"1": "owner", "5": "member"}
}
```

This means any backend sharing the same `JWT_SECRET` can authorize requests locally — no call back to Core needed. The custom claim is built in `core/jwt.py` by querying the user's memberships at login time.

## Project Structure

```
config/
  settings/            # base.py, dev.py, test.py, prod.py
  api.py               # Central router registration + exception handlers
  urls.py              # URL config (admin + API mount)
apps/
  users/               # Custom User model, registration, profile management
  organizations/       # Organizations, Membership (with roles), CRUD
  citizens/            # Citizens (the kids), belong to an organization
  grades/              # Grade groupings, M2M with citizens
  pictograms/          # Visual aids library (global or org-specific)
  invitations/         # Email-based org invitations (send, accept, reject)
core/
  permissions.py       # check_role(), check_role_or_raise(), get_membership_or_none()
  exceptions.py        # Domain exception hierarchy
  jwt.py               # Custom JWT claims (org_roles)
  throttling.py        # Rate limiters (login, register, invitations)
  schemas.py           # Shared ErrorOut schema
```

---

## API Reference

Interactive API docs are available at **http://localhost:8000/api/v1/docs** when running locally. All endpoints are prefixed with `/api/v1`.

### Rate Limits

| Endpoint | Limit |
| -------- | ----- |
| Login (`/token/pair`) | 5 requests/minute per IP |
| Registration (`/auth/register`) | 3 requests/minute per IP |
| Invitation sends | 10 requests/minute per user |

---

## Environment Variables

| Variable                 | Default               | Description                            |
| ------------------------ | --------------------- | -------------------------------------- |
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` | Settings module (dev/test/prod)        |
| `DJANGO_SECRET_KEY`      | dev-only default      | Django secret key (required in prod)   |
| `JWT_SECRET`             | Same as `SECRET_KEY`  | JWT signing key (shared with app backends) |
| `POSTGRES_DB`            | `giraf_core`          | Database name                          |
| `POSTGRES_USER`          | `giraf`               | Database user                          |
| `POSTGRES_PASSWORD`      | `giraf`               | Database password                      |
| `POSTGRES_HOST`          | `localhost`           | Database host                          |
| `POSTGRES_PORT`          | `5432`                | Database port                          |
| `CORS_ALLOWED_ORIGINS`   | (empty)               | Comma-separated allowed origins        |
| `ALLOWED_HOSTS`          | (empty)               | Comma-separated allowed hosts (prod)   |

## Testing

```bash
# Run all tests
uv run pytest

# Verbose output
uv run pytest -v

# Single app
uv run pytest apps/users/ -v

# Single test
uv run pytest apps/users/tests/test_api.py::test_register -v

# With coverage
uv run pytest --cov=apps --cov=core --cov-report=term-missing
```

Tests use SQLite in-memory for speed (`config/settings/test.py`) with MD5 password hashing to keep tests fast.

## Code Quality

```bash
# Lint
uv run ruff check .

# Auto-format
uv run ruff format .

# Type check
uv run mypy apps/ config/ core/
```

Ruff is configured for Python 3.12, line length 120, with migrations excluded.

## Good First Issues

These are self-contained tasks ideal for getting familiar with the codebase:

### 1. Add test factories to all apps

**Apps affected:** `citizens`, `grades`, `pictograms`, `invitations`

Only `users` and `organizations` have `factories.py` files using `factory_boy`. The other four apps create test data inline. Add a `tests/factories.py` to each, following the pattern in `apps/users/tests/factories.py` and `apps/organizations/tests/factories.py`. Then update existing tests to use the new factories.

### 2. Add a `seed_dev_data` management command

Create a `manage.py seed_dev_data` command that populates the local database with realistic sample data — a few users, organizations with memberships, citizens, grades, pictograms, and invitations. This lets new developers get a working local environment without manually calling API endpoints. See [Django docs on custom management commands](https://docs.djangoproject.com/en/5.2/howto/custom-management-commands/).

### 3. Standardize test file organization

Test files are inconsistent across apps. `users/` has 6 focused test files (`test_api.py`, `test_services.py`, `test_models.py`, etc.), while `grades/` has a single `test_grades.py` covering everything. Pick one convention — splitting by layer (`test_api.py`, `test_services.py`) is recommended — and apply it to `citizens`, `grades`, `pictograms`, and `invitations`.

### 4. Write a "how to add a new app" guide

The `models → schemas → services → api` pattern is consistent but undocumented as a step-by-step. Add a section to `CONTRIBUTING.md` (or a new `docs/adding-an-app.md`) with a checklist: create the app, add to `INSTALLED_APPS`, create the four files, register the router in `config/api.py`, add factories, write tests.
