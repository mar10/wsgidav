# (c) 2009-2026 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Security regression tests for request handling, storage, and web UI.
"""

import logging
import os

import pytest
import webtest

from wsgidav import util
from wsgidav.dav_error import DAVError
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.mw.debug_filter import WsgiDavDebugFilter
from wsgidav.prop_man.property_manager import PropertyManager
from wsgidav.wsgidav_app import WsgiDAVApp

LOCK_BODY = (
    b'<?xml version="1.0"?><D:lockinfo xmlns:D="DAV:">'
    b"<D:lockscope><D:exclusive/></D:lockscope>"
    b"<D:locktype><D:write/></D:locktype></D:lockinfo>"
)


def proppatch_body(name):
    return (
        '<?xml version="1.0"?><D:propertyupdate xmlns:D="DAV:"><D:set><D:prop>'
        f'<x:{name} xmlns:x="urn:x">value</x:{name}>'
        "</D:prop></D:set></D:propertyupdate>"
    ).encode()


@pytest.fixture
def root(tmp_path):
    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "a" / "b" / "c.txt").write_text("source")
    (tmp_path / "a" / "keep.txt").write_text("keep")
    return tmp_path


def make_client(root, **options):
    config = {
        "provider_mapping": {"/": str(root)},
        "simple_dc": {"user_mapping": {"*": True}},  # anonymous access
        "property_manager": True,
        "verbose": 1,
        # Don't reconfigure the global logger (other tests rely on it)
        "logging": {"enable": False},
    }
    config.update(options)
    return webtest.TestApp(WsgiDAVApp(config))


# --- COPY / MOVE ------------------------------------------------------------


@pytest.mark.parametrize("method", ["COPY", "MOVE"])
@pytest.mark.parametrize(
    "source,destination",
    [("/a/b/c.txt", "/a"), ("/a/b/c.txt", "/a/b/"), ("/a/b/", "/a"), ("/a/b/", "/")],
)
def test_copy_move_onto_parent_is_rejected(root, method, source, destination):
    """The destination is removed first, which would delete the source too."""
    client = make_client(root)
    client.request(
        source, method=method, headers={"Destination": destination}, status=403
    )
    assert (root / "a" / "b" / "c.txt").read_text() == "source"
    assert (root / "a" / "keep.txt").read_text() == "keep"


def test_move_to_sibling_still_works(root):
    client = make_client(root)
    client.request(
        "/a/b/c.txt", method="MOVE", headers={"Destination": "/a/c.txt"}, status=201
    )
    assert (root / "a" / "c.txt").read_text() == "source"
    client.request(
        "/a/c.txt", method="MOVE", headers={"Destination": "/a/keep.txt"}, status=204
    )
    assert (root / "a" / "keep.txt").read_text() == "source"


# --- Properties -------------------------------------------------------------


def test_proppatch_and_property_limit(root):
    client = make_client(root, max_dead_props_per_resource=2)
    for name in ("p1", "p2"):
        res = client.request(
            "/a/keep.txt", method="PROPPATCH", body=proppatch_body(name)
        )
        assert "200 OK" in res.text
    res = client.request("/a/keep.txt", method="PROPPATCH", body=proppatch_body("p3"))
    assert res.status_int == 207
    assert "507" in res.text and "200 OK" not in res.text
    # Existing properties can still be updated
    res = client.request("/a/keep.txt", method="PROPPATCH", body=proppatch_body("p1"))
    assert "200 OK" in res.text
    # ... and other resources are not affected
    res = client.request("/a/b/c.txt", method="PROPPATCH", body=proppatch_body("p3"))
    assert "200 OK" in res.text


def test_move_properties_only_replaces_the_prefix():
    pm = PropertyManager()
    for url in ("/a/", "/a/x/a/f.txt", "/ab/f.txt"):
        pm.write_property(url, "{urn:x}p", "v")
    pm.move_properties("/a/", "/b/", with_children=True)
    assert sorted(pm._dict) == ["/ab/f.txt", "/b/", "/b/x/a/f.txt"]


@pytest.mark.parametrize(
    "uri,old,new,expected",
    [
        ("/a/x/a/f", "/a/", "/b/", "/b/x/a/f"),
        ("/a/", "/a/", "/b/", "/b/"),
        ("/a/", "/a", "/b/", "/b/"),
        ("/a", "/a", "/b", "/b"),
        ("/a/f", "/", "/b/", "/b/a/f"),
    ],
)
def test_replace_uri_prefix(uri, old, new, expected):
    assert util.replace_uri_prefix(uri, old, new) == expected


def test_replace_uri_prefix_rejects_other_paths():
    with pytest.raises(ValueError):
        util.replace_uri_prefix("/ab/f", "/a/", "/b/")


# --- Locks ------------------------------------------------------------------


def test_refused_lock_does_not_leave_an_empty_file(root):
    client = make_client(root)
    client.request(
        "/a/", method="LOCK", body=LOCK_BODY, headers={"Depth": "infinity"}, status=200
    )
    client.request("/a/new.txt", method="LOCK", body=LOCK_BODY, status=423)
    assert not (root / "a" / "new.txt").exists()
    # A granted lock on an unmapped URL still creates the resource
    client.request("/new.txt", method="LOCK", body=LOCK_BODY, status=201)
    assert (root / "new.txt").exists()


def test_lock_limit_per_user(root):
    client = make_client(root, max_locks_per_user=2)
    client.request("/a/keep.txt", method="LOCK", body=LOCK_BODY, status=200)
    res = client.request("/a/b/c.txt", method="LOCK", body=LOCK_BODY, status=200)
    client.request("/l3.txt", method="LOCK", body=LOCK_BODY, status=507)
    assert not (root / "l3.txt").exists()
    # Releasing a lock makes room again
    client.request(
        "/a/b/c.txt",
        method="UNLOCK",
        headers={"Lock-Token": res.headers["Lock-Token"]},
        status=204,
    )
    client.request("/l3.txt", method="LOCK", body=LOCK_BODY, status=201)


# --- Shares -----------------------------------------------------------------


def test_mixed_case_share_names(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "f.txt").write_text("x")
    app = WsgiDAVApp(
        {
            "provider_mapping": {"/": str(tmp_path), "/Docs": str(docs)},
            "simple_dc": {"user_mapping": {"*": True}},
            "logging": {"enable": False},
        }
    )
    assert app.resolve_provider("/docs/f.txt")[0] == "/Docs"
    assert app.resolve_provider("/DOCS")[1] is app.provider_map["/Docs"]
    client = webtest.TestApp(app)
    assert client.get("/Docs/f.txt").text == "x"
    assert client.get("/docs/f.txt").text == "x"
    client.request(
        "/Docs/f.txt", method="COPY", headers={"Destination": "/Docs/g.txt"}, status=201
    )
    assert (docs / "g.txt").read_text() == "x"


def test_share_names_must_be_unique_ignoring_case(tmp_path):
    with pytest.raises(ValueError, match="not case-sensitive"):
        WsgiDAVApp(
            {
                "provider_mapping": {"/Docs": str(tmp_path), "/docs": str(tmp_path)},
                "simple_dc": {"user_mapping": {"*": True}},
                "logging": {"enable": False},
            }
        )


# --- Symlinks ---------------------------------------------------------------


@pytest.mark.skipif(not hasattr(os, "O_NOFOLLOW"), reason="requires O_NOFOLLOW")
def test_open_file_does_not_follow_symlinks(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("secret")
    share = tmp_path / "share"
    share.mkdir()
    (share / "f.txt").write_text("x")
    link = share / "link.txt"
    link.symlink_to(secret)

    provider = FilesystemProvider(str(share), fs_opts={"follow_symlinks": False})
    with provider._open_file(str(share / "f.txt"), "rb") as f:
        assert f.read() == b"x"
    for mode in ("rb", "wb"):
        with pytest.raises(DAVError) as exc:
            provider._open_file(str(link), mode)
        assert exc.value.value == 403
    assert secret.read_text() == "secret"

    provider = FilesystemProvider(str(share), fs_opts={"follow_symlinks": True})
    with provider._open_file(str(link), "rb") as f:
        assert f.read() == b"secret"


# --- Web UI -----------------------------------------------------------------


def test_dir_browser_escapes_office_links(root):
    name = "x'onmouseover='alert(1)'.docx"
    (root / name).write_text("x")
    client = make_client(
        root, dir_browser={"enable": True}, dav_explorer={"enable": False}
    )
    html = client.get("/").text
    link = next(line for line in html.splitlines() if "libreoffice" in line)
    assert "ofv|u|x&#x27;onmouseover%3D&#x27;alert(1)&#x27;.docx'>Edit</a>" in link
    assert "u|x'" not in link


# --- Logging ----------------------------------------------------------------


def test_debug_filter_redacts_credentials(caplog):
    def app(environ, start_response):
        start_response("200 OK", [("Content-Length", "2")])
        return [b"OK"]

    config = {"verbose": 5, "logging": {}}
    mw = WsgiDavDebugFilter(None, app, config)
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": "/",
        "HTTP_AUTHORIZATION": "Basic dGVzdGVyOnNlY3JldA==",
        "HTTP_PROXY_AUTHORIZATION": "Digest username=tester, response=abcdef",
        "HTTP_COOKIE": "session=topsecret",
        "HTTP_USER_AGENT": "pytest",
    }
    logger = logging.getLogger("wsgidav")
    logger.addHandler(caplog.handler)
    old_level = logger.level
    logger.setLevel(logging.DEBUG)
    try:
        assert list(mw(environ, lambda *args: None)) == [b"OK"]
    finally:
        logger.setLevel(old_level)
        logger.removeHandler(caplog.handler)

    assert "'Basic <redacted>'" in caplog.text
    assert "'Digest <redacted>'" in caplog.text
    assert "pytest" in caplog.text
    for secret in ("dGVzdGVyOnNlY3JldA", "abcdef", "topsecret"):
        assert secret not in caplog.text
