# Python

## Contents
- Detect
- Packaging and environments
- Typing
- Sync vs async
- Exceptions
- Project structure
- Testing
- Verification commands

## Detect

- Version: `requires-python`, `.python-version`, `.tool-versions`, the Dockerfile base image, CI matrix. Don't use syntax newer than the minimum supported version (for example `match`, `X | Y` unions at runtime, `ExceptionGroup`).
- Framework: FastAPI, Django, or Flask ([fastapi-django](../frameworks/fastapi-django.md)), or Litestar, Starlette, aiohttp, Celery workers, data pipelines, CLIs.
- Async vs sync: `async def` handlers, `asyncio`, async DB drivers/sessions.

## Packaging and environments

- Use the project's tool: uv (`uv add`, `uv run`), Poetry (`poetry add`, `poetry run`), PDM, Pipenv, Hatch, or pip with `requirements*.txt` (and possibly `pip-tools` `.in` files, which are the source of truth for compiled `.txt` files).
- Add dependencies where the project declares them (the `pyproject.toml` dependency group, or the right `requirements` file for prod vs dev). Keep the lockfile in sync using the tool.
- Run commands inside the project's environment (`uv run pytest`, `poetry run pytest`, an activated venv). Don't install into the global interpreter.

## Typing

- Follow the project's typing level. If mypy/pyright run in strict mode, new code must type-check. Use the project's type-checker config.
- Match the annotation style (`list[str]` vs `List[str]`, `X | None` vs `Optional[X]`) to the supported version and the existing code.
- Data models: use whatever the project uses (Pydantic v1 vs v2, dataclasses, attrs, TypedDict, Django models). Pydantic v1 and v2 APIs differ significantly, so check the installed version.

## Sync vs async

- In async code, never call blocking I/O (sync DB drivers, `requests`, `time.sleep`, heavy CPU work) directly. Use async libraries already in the project, or offload with the framework's threadpool mechanism.
- Don't mix sync and async sessions or clients for the same resource. Follow the existing pattern.
- Use `asyncio.gather`/`TaskGroup` for independent concurrent I/O, with bounded concurrency.

## Exceptions

- Raise specific exceptions, using the project's custom hierarchy if one exists. Map them to responses through the framework's exception handlers.
- Never use bare `except:` or broad `except Exception: pass`. Preserve context with `raise ... from err`.
- Use context managers (`with`, `async with`) for resources such as files, sessions, and locks.

## Project structure

- `src/` layout vs flat package: match it. Import style (absolute vs relative) follows the codebase.
- Don't do work at import time (connecting to databases, reading env vars) unless that's the project's pattern. Use the existing settings object (pydantic-settings, Django settings, dynaconf, env helpers).
- Logging: use `logging.getLogger(__name__)` or the project's structured logger. Use `print` only where the project does (for example CLIs).

## Testing

- pytest is the common default (fixtures in `conftest.py`, markers, parametrization). Some projects use `unittest` or Django's test runner. Match what the project uses.
- Reuse fixtures and factories (factory_boy, model_bakery, custom builders). Mock HTTP with the existing library (`responses`, `respx`, `pytest-httpx`). Use the project's DB test strategy.
- Async tests need the configured plugin (`pytest-asyncio` or `anyio`) and its mode or markers.

## Verification commands

Typically `<runner> pytest path/to/test_file.py -q`, then the full suite; `ruff check`/`ruff format --check` or `flake8`/`black --check`/`isort --check`; `mypy`/`pyright`. Use `tox`/`nox` sessions or Makefile targets if CI uses them.
