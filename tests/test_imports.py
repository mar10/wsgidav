# (c) 2009-2026 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""Smoke test that asserts that every module can be imported."""

import importlib
import pkgutil

import pytest

import wsgidav


def _reraise(module_name):
    raise


MODULE_NAMES = sorted(
    info.name
    # reraise ensures that import errors of subpackages are not silently ignored
    for info in pkgutil.walk_packages(wsgidav.__path__, "wsgidav.", onerror=_reraise)
)


def test_finds_at_least_some_modules():
    assert len(MODULE_NAMES) > 10


@pytest.mark.parametrize("module_name", MODULE_NAMES)
def test_module_is_importable(module_name):
    try:
        importlib.import_module(module_name)
    except ImportError as e:
        # accept missing optional or platform specific dependencies,
        if e.name and e.name.partition(".")[0] == "wsgidav":
            raise
        pytest.skip(f"missing dependency {e.name!r}")
