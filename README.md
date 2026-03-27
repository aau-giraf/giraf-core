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

# Seed sample data (users, orgs, citizens, pictograms, etc.)
uv run python manage.py seed_dev_data

# Start the dev server
uv run python manage.py runserver
# API at http://localhost:8000/api/v1/docs
```

Or run everything via Docker Compose:

```bash
docker compose up
# API at http://localhost:8000
```

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
  clients/             # External service clients (giraf-ai stub)
  permissions.py       # check_role(), check_role_or_raise(), get_membership_or_none()
  exceptions.py        # Domain exception hierarchy
  jwt.py               # Custom JWT claims (org_roles)
  throttling.py        # Rate limiters (login, register, invitations)
  validators.py        # Image and audio file validation
  schemas.py           # Shared ErrorOut schema
```

---

## Admin UI

Django Admin is available at `/admin/` in all environments — it serves as the central admin interface for the GIRAF platform. Client apps (Flutter, Expo, etc.) should not build their own admin systems.

**Access requirements:**
- Users must have `is_staff=True` to log in
- Create a staff user with `uv run python manage.py createsuperuser`

**What you can manage:**
- Users — create, edit, toggle staff/active status
- Organizations — full CRUD with inline membership editing
- Memberships — assign users to organizations with roles
- Citizens, Grades, Pictograms — full CRUD scoped to organizations
- Invitations — view status, filter by status/organization

Admin uses session-based auth (separate from the JWT API auth), and Django logs all admin actions for auditing.

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
| `GIRAF_AI_URL`           | (empty)               | Base URL for the giraf-ai service      |
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

---

## Adding a New App

Every app follows the same `models → schemas → services → api` pattern. Use this checklist:

### 1. Create the app

```bash
uv run python manage.py startapp myapp apps/myapp
```

Then update `apps/myapp/apps.py` to set the correct name:

```python
class MyappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.myapp"  # must match the path under apps/
```

### 2. Add to `INSTALLED_APPS`

In `config/settings/base.py`:

```python
INSTALLED_APPS = [
    ...
    "apps.myapp",
]
```

### 3. Create the four core files

| File | Purpose | Example to follow |
|------|---------|-------------------|
| `models.py` | Django models with `clean()` validation | `apps/citizens/models.py` |
| `schemas.py` | Ninja `Schema` classes for input/output | `apps/pictograms/schemas.py` |
| `services.py` | Business logic (static methods on a service class) | `apps/citizens/services.py` |
| `api.py` | Ninja `Router` with endpoints that delegate to the service | `apps/citizens/api.py` |

**Conventions:**
- Models call `self.full_clean()` in `save()` for validation
- Services raise exceptions from `core/exceptions.py` (`ResourceNotFoundError`, `BusinessValidationError`, etc.)
- API endpoints use `check_role_or_raise()` or `check_org_or_superuser()` from `core/permissions.py`
- Endpoints return `(status_code, data)` tuples

### 4. Register the router

In `config/api.py`:

```python
from apps.myapp.api import router as myapp_router

api.add_router("/myapp", myapp_router)
```

### 5. Create migrations

```bash
uv run python manage.py makemigrations myapp
```

### 6. Add admin registration

In `apps/myapp/admin.py`, register your models so they appear in Django Admin.

### 7. Add tests

Create the test directory structure:

```
apps/myapp/tests/
    __init__.py
    factories.py    # factory_boy factories for test data
    test_models.py  # model validation tests
    test_services.py # service logic tests
    test_api.py     # endpoint integration tests
```

Use `@pytest.mark.django_db` on test classes. See `apps/pictograms/tests/` for a complete example.

### 8. Run and verify

```bash
uv run python manage.py migrate
uv run pytest apps/myapp/ -v
uv run python manage.py runserver  # check /api/v1/docs for your endpoints
```
