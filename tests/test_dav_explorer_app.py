# (c) 2009-2026 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
App-level tests for the DAV Explorer web UI (using WebTest, no server process).
"""

import tempfile

import pytest

from tests.test_http_dav_explorer import get_context_data
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.wsgidav_app import WsgiDAVApp

webtest = pytest.importorskip("webtest")

# ========================================================================
# Tests
# ========================================================================


def _make_app(share_path, **dav_explorer_opts):
    config = {
        "provider_mapping": {"/": FilesystemProvider(share_path)},
        "http_authenticator": {"domain_controller": None},
        "simple_dc": {"user_mapping": {"*": True}},
        "verbose": 1,
        "logging": {"enable_loggers": []},
        "property_manager": None,
        "lock_storage": True,
        "dir_browser": {"enable": False},
        "dav_explorer": {"enable": True, **dav_explorer_opts},
    }
    return webtest.TestApp(WsgiDAVApp(config))


def test_readonly_mode_rendered():
    with tempfile.TemporaryDirectory() as tmp:
        app = _make_app(tmp, readonly=True)
        res = app.get("/")
        assert get_context_data(res.text)["readonly"] is True
        assert 'document.documentElement.classList.add("readonly")' in res.text

        app = _make_app(tmp)
        res = app.get("/")
        assert get_context_data(res.text)["readonly"] is False
        assert 'classList.add("readonly")' not in res.text
