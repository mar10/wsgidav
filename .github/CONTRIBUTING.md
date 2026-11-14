# Contribution Guideline

Thanks for contributing :-)

The full guide is in the
[Development section](https://wsgidav.readthedocs.io/en/latest/development.html)
of the documentation. This page is the short version.

## Before you start

- **Questions** go to the [discussion forum](https://github.com/mar10/wsgidav/discussions),
  not the issue tracker.
- **Bugs and feature requests**: search the
  [issue tracker](https://github.com/mar10/wsgidav/issues) first, then open an
  issue (even if you plan to send a pull request), so the approach can be
  discussed.
- **Security issues**: do **not** open a public issue. Follow
  [SECURITY.md](SECURITY.md) instead.

## Development setup

WsgiDAV requires Python 3.10 or later and uses [uv](https://docs.astral.sh/uv/)
for dependency management:

```sh
git clone https://github.com/YOUR_USERNAME/wsgidav
cd wsgidav
git checkout -b my-feature
uv sync                     # creates .venv with runtime and dev dependencies
uv run wsgidav --version
```

Start a local server for manual testing (anonymous access, so bind to
localhost only):

```sh
uv run wsgidav --no-config --host 127.0.0.1 --port 8080 \
    --root /path/to/tmpdir --auth anonymous --web-ui dav-explorer
```

## Checks

Run these before you open a pull request. CI runs the same lint and tests
on all supported Python versions.

```sh
uv run tox -e check         # Ruff lint and format check
uv run tox -e format        # Auto-format with Ruff (if `check` complains)
uv run pytest -ra tests/test_<area>.py   # Focused tests
uv run tox                  # Full test matrix
uv run tox -e docs          # Sphinx docs build (if you changed docs)
```

`tests/test_litmus.py`, `tests/stressor/`, and `tests/benchmarks.py` need
external tools and are not part of the default run.

## Pull request checklist

- [ ] One topic per pull request; reference the related issue.
- [ ] Code follows PEP 8 naming (`snake_case` for functions, methods, and
      variables) and passes `uv run tox -e check`.
- [ ] Behavior changes come with new or updated tests under `tests/`.
- [ ] New or changed configuration options are updated in
      `wsgidav/default_conf.py`, `sample_wsgidav.yaml`, **and**
      `docs/source/user_guide_configure.rst`.
- [ ] User-visible changes have an entry in `CHANGELOG.md`.
- [ ] Changes to paths, authentication, authorization, locking, or request
      handling keep existing access controls intact.
- [ ] Generated files (`build/`, `docs/source/_autosummary/`, `*.egg-info`)
      and vendored files (`htdocs/wunderbaum.*`) are not modified;
      `uv.lock` is only changed via `uv` commands.

Code in `wsgidav/samples/` is example code: it is lightly maintained, not
covered by the test suite, and not guaranteed to work correctly or securely.

Coding agents: see [AGENTS.md](../AGENTS.md) for repository-specific
instructions.

Happy hacking :)
