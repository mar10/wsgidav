"""Tests for read-only FilesystemProvider shares."""

import pytest
import webtest

from wsgidav import wsgidav_app
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.wsgidav_app import WsgiDAVApp


@pytest.mark.parametrize("readonly", [True, False])
def test_is_readonly(tmp_path, readonly):
    provider = FilesystemProvider(str(tmp_path), readonly=readonly, fs_opts={})
    assert provider.is_readonly() is readonly


@pytest.fixture
def client(tmp_path):
    rw = tmp_path / "rw"
    ro = tmp_path / "ro"
    rw.mkdir()
    ro.mkdir()
    (ro / "file.txt").write_text("protected")
    app = WsgiDAVApp(
        {
            "simple_dc": {"user_mapping": {"*": True}},  # anonymous access
            "provider_mapping": {
                "/": str(rw),
                "/ro": {"root": str(ro), "readonly": True},
            },
        }
    )
    return webtest.TestApp(app), ro


def _allow(response):
    return {m.strip() for m in response.headers["Allow"].split(",")}


def test_options_on_readonly_share(client):
    app, _ro = client
    res = app.options("/ro/file.txt")
    allow = _allow(res)
    assert {"GET", "HEAD", "PROPFIND"} <= allow
    assert not allow & {"PUT", "DELETE", "MOVE", "PROPPATCH", "LOCK", "UNLOCK"}
    assert res.headers["DAV"] == "1"

    res = app.options("/ro/")
    assert not _allow(res) & {"DELETE", "MOVE", "PROPPATCH", "LOCK"}


def test_options_on_readwrite_share(client):
    app, _ro = client
    app.put("/new.txt", b"data", status=201)
    res = app.options("/new.txt")
    assert {"PUT", "DELETE", "LOCK"} <= _allow(res)
    assert res.headers["DAV"] == "1,2"


@pytest.mark.parametrize(
    ("method", "path", "headers"),
    [
        ("PUT", "/ro/file.txt", {}),
        ("PUT", "/ro/new.txt", {}),
        ("DELETE", "/ro/file.txt", {}),
        ("MKCOL", "/ro/folder", {}),
        ("MOVE", "/ro/file.txt", {"Destination": "/ro/moved.txt"}),
        ("LOCK", "/ro/file.txt", {}),
    ],
)
def test_write_methods_rejected_on_readonly_share(client, method, path, headers):
    app, ro = client
    app.request(path, method=method, headers=headers, body=b"x", status=405)
    assert (ro / "file.txt").read_text() == "protected"
    assert sorted(p.name for p in ro.iterdir()) == ["file.txt"]


def test_startup_warning_reports_readonly(tmp_path, monkeypatch):
    (tmp_path / "ro").mkdir()
    messages = []
    # init_logging() resets the wsgidav logger's handlers, so spy on the call
    monkeypatch.setattr(
        wsgidav_app._logger, "warning", lambda msg, *a, **kw: messages.append(msg)
    )
    WsgiDAVApp(
        {
            "simple_dc": {"user_mapping": {"*": True}},
            "provider_mapping": {
                "/ro": {"root": str(tmp_path / "ro"), "readonly": True},
            },
        }
    )
    assert "Share '/ro' will allow anonymous read access." in messages
    assert "Share '/ro' will allow anonymous write access." not in messages
