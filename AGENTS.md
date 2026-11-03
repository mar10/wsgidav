# WsgiDAV contributor instructions

This file is the shared source of repository guidance for coding agents.

## Project overview

WsgiDAV is a Python WebDAV server and WSGI middleware. Keep changes consistent
with its existing provider, middleware, authentication, and configuration
patterns. The built-in DAV Explorer frontend lives in
`wsgidav/mw/dav_explorer/htdocs/`; it has no separate package or test runner.

## General workflow

- Read the surrounding implementation and tests before changing behavior.
- Keep changes focused and preserve existing public APIs and configuration
  behavior unless the task explicitly calls for a change.
- Add or update tests under `tests/` for behavior changes.
- Treat filesystem paths, authentication, authorization, locks, and WebDAV
  request handling as security-sensitive; validate inputs and preserve access
  controls.
- Update directly related documentation when behavior or usage changes.
- Do not overwrite or revert unrelated work in the working tree.

## Python conventions

- Python 3.10 is the minimum supported version; check `pyproject.toml` and
  `tox.ini` for the current supported/tested version matrix.
- Use `uv` for dependency management and project commands.
- Follow the existing code style. Ruff handles linting and formatting; its
  configuration is in `pyproject.toml`.
- Prefer the narrowest relevant test or check, and run broader validation when
  practical:
  - `uv run pytest -ra tests/test_<area>.py` for focused tests.
  - `uv run tox -e check` for Ruff lint and format checks.
  - `uv run tox` for the full configured test matrix.
  - `uv run tox -e docs` for the Sphinx documentation build.
- `uv run tox -e format` reformats the Python source; run it only when
  formatting changes are intended.

## DAV Explorer frontend

- Make frontend changes in the existing files under
  `wsgidav/mw/dav_explorer/htdocs/` and follow their established JavaScript
  patterns.
- There is no frontend package manifest or dedicated JavaScript test command;
  validate frontend changes using relevant existing Python tests and manual
  checks when available.
