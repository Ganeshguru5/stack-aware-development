# Python web: FastAPI, Django, Flask

## Contents
- Inspect the application
- FastAPI
- Django (and Django REST Framework)
- Flask
- Security
- Performance
- Testing

## Inspect the application

- Framework and version. Pydantic v1 vs v2 matters for FastAPI. Django major version. Flask 2 vs 3.
- Sync vs async: async route handlers, async ORM sessions, async drivers.
- App layout: routers/blueprints/apps, settings module, dependency or service layer, where DB sessions are created.
- Migration tool (Alembic, Django migrations), task queue (Celery, RQ, Dramatiq, ARQ), cache.

## FastAPI

- Structure: `APIRouter` per resource, included in the app. Request/response models via Pydantic. Dependencies (`Depends`) for DB sessions, auth, and pagination. Follow the existing layering (routers → services/CRUD modules → models).
- Use `response_model` (or return annotations) the way neighbors do, so internal fields aren't leaked.
- DB session: reuse the existing dependency (`get_db`/`get_session`). Match sync `Session` vs `AsyncSession`. Never block in `async def` endpoints. A sync DB driver belongs in `def` endpoints, which FastAPI runs in a threadpool.
- SQLAlchemy 2.x style (`select()`, `session.execute`, `scalars()`) vs legacy `session.query()`: match the codebase. Use eager loading (`selectinload`, `joinedload`) to avoid N+1. With async sessions, lazy loading raises errors, so load relationships explicitly.
- Errors: `HTTPException` or custom exceptions with registered exception handlers. Use the existing error shape.
- Settings via pydantic-settings or the existing config module.

## Django (and Django REST Framework)

- Apps under `INSTALLED_APPS`. Models → migrations (`makemigrations`, review the generated file, never edit applied ones) → views (function, class-based, or DRF viewsets) → URLs. Templates or serializers.
- DRF: serializers for validation and representation, viewsets/routers, permission classes, pagination classes, filter backends. Reuse the project's defaults from `REST_FRAMEWORK` settings.
- ORM: `select_related` (FK/one-to-one) and `prefetch_related` (many) for N+1; `only`/`values` for slim queries; `F` expressions and `update()` for atomic updates; `transaction.atomic` for multi-step writes.
- Forms or serializers carry validation, and model constraints back it up. Use the auth system and permissions already in place (`django.contrib.auth`, custom user model via `AUTH_USER_MODEL`).
- Async views exist, but the ORM's async support is partial in many versions. Follow the project.

## Flask

- App factory and blueprints, extensions (Flask-SQLAlchemy, Flask-Login, Flask-Migrate/Alembic, Marshmallow, WTForms). Follow the existing extension set.
- Use the request context and `g` the way the project does. Register error handlers per app or blueprint.

## Security

- FastAPI: auth via dependencies (OAuth2 scheme, API key, session). Apply them per router or per route as neighbors do. Validate everything with Pydantic models. CORS through the configured middleware.
- Django: CSRF middleware for session-auth forms, auto-escaping templates (avoid `mark_safe`/`|safe` on user data), `ALLOWED_HOSTS`, permission classes on every DRF view. Don't let default permissions accidentally become `AllowAny`.
- Never build SQL with f-strings. Use ORM parameters or `text()` with bound parameters.
- Settings: `DEBUG` off and secrets from env in production configuration.

## Performance

- Count queries: SQLAlchemy `echo=True` or event listeners, Django `assertNumQueries` or debug toolbar, in tests or locally.
- Paginate with the project's mechanism. Push filtering and aggregation into SQL.
- Move slow work (emails, exports, external calls) to the existing task queue.
- In async apps, look for hidden blocking calls (sync HTTP clients, sync drivers, CPU-heavy work).

## Testing

- FastAPI: `TestClient` or `httpx.AsyncClient` with `ASGITransport`. Override dependencies (`app.dependency_overrides`) for DB, auth, and external services, as neighbors do. Use pytest fixtures for the DB (transaction rollback or a test database).
- Django: `pytest-django` or `django.test.TestCase`, DRF `APIClient`, factories. Use `assertNumQueries` for N+1 regression tests.
- Flask: `app.test_client()` with the app factory in testing config.
