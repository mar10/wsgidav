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

## Architecture

Request flow for every HTTP request:

1. `WsgiDAVApp` (`wsgidav/wsgidav_app.py`) merges the configuration and builds
   the `middleware_stack` (defaults in `wsgidav/default_conf.py`).
2. Middleware, outermost first: `Cors` → `ErrorPrinter` → `HTTPAuthenticator`
   → `WsgiDavDirBrowser` / `WsgiDavExplorer` → `RequestResolver`.
   `RequestResolver` must stay last; it maps the URL to a share/provider.
3. `RequestServer` (`wsgidav/request_server.py`) handles the WebDAV method in
   `do_<METHOD>` (`do_PROPFIND`, `do_PUT`, `do_COPY`/`do_MOVE`, `do_LOCK`, ...).
4. Providers expose resources: `DAVProvider`, `DAVCollection`,
   `DAVNonCollection` (`wsgidav/dav_provider.py`). The filesystem
   implementation is `wsgidav/fs_dav_provider.py`.

Key modules:

- `dc/`: domain controllers for authentication (`BaseDomainController`,
  simple, htpasswd, htdigest, NT, PAM).
- `lock_man/`: `LockManager` with dict, shelve, and Redis lock storage.
- `prop_man/`: dead-property storage (in-memory/shelve, CouchDB, MongoDB).
- `mw/`: `BaseMiddleware`, `cors.py`, `debug_filter.py`, `dir_browser/`
  (server-rendered listing), `dav_explorer/` (JavaScript web UI).
- `server/server_cli.py`: the `wsgidav` command-line entry point.
- `util.py`, `xml_tools.py`, `dav_error.py`: shared helpers and `DAVError`.
- `samples/`: example providers; excluded from coverage and lightly maintained.

## Configuration

- `wsgidav/default_conf.py` holds the defaults. `sample_wsgidav.yaml`
  documents all options for users.
- When adding or changing an option, update both files and
  `docs/source/user_guide_configure.rst`.

## Tests

- HTTP-level tests start a real server with `WsgiDavTestServer` from
  `tests/util.py` (see `tests/test_http_dav_explorer.py`).
- App-level tests use WebTest (see `tests/test_wsgidav_app.py`).
- `tests/test_litmus.py`, `tests/stressor/`, and `tests/benchmarks.py` need
  external tools or `-m benchmarks`; do not run them by default.
- CI (`.github/workflows/tests.yml`) runs `ruff check` and pytest on all
  supported Python versions.

## Running a local server

```sh
uv run wsgidav --no-config --host 127.0.0.1 --port 8080 \
    --root /path/to/tmpdir --auth anonymous --web-ui dav-explorer
```

Use `--web-ui dir-browser` for the classic listing. Bind only to `127.0.0.1`
when using anonymous auth. The `run-wsgidav` skill in `.claude/skills/`
describes the full start/verify/stop procedure.

## Housekeeping

- Add user-visible changes to `CHANGELOG.md`.
- Do not edit generated or local files: `build/`, `.tox/`, `*.egg-info`,
  `docs/source/_autosummary/`, `.coverage*`.
- `htdocs/wunderbaum.*` files are vendored and git-ignored; do not modify them.
- Change `uv.lock` only via `uv` commands.
