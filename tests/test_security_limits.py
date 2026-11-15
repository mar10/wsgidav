# (c) 2009-2026 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Security regression tests: request limits and response hardening.

- XML request bodies, uploads and `Depth: infinity` can be limited.
- Unread request bodies are discarded in blocks (not read into memory at once).
- Files are served with `X-Content-Type-Options: nosniff`.
- A failed PUT must not destroy the previous content of a file.
"""

import io
import os
import shutil
import tempfile
import unittest

import webtest

from wsgidav import util
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.wsgidav_app import WsgiDAVApp

PROPFIND_BODY = (
    b'<?xml version="1.0"?><D:propfind xmlns:D="DAV:"><D:allprop/></D:propfind>'
)


class LimitsTest(unittest.TestCase):
    def setUp(self):
        self.root_path = tempfile.mkdtemp(prefix="wsgidav-test-")
        os.mkdir(os.path.join(self.root_path, "sub"))
        with open(os.path.join(self.root_path, "file.txt"), "wb") as f:
            f.write(b"original")

    def tearDown(self):
        shutil.rmtree(self.root_path, ignore_errors=True)

    def _app(self, wsgi_input=None, **options):
        config = {
            "provider_mapping": {"/": FilesystemProvider(self.root_path, fs_opts={})},
            "simple_dc": {"user_mapping": {"*": True}},  # anonymous access
            "verbose": 1,
            # Don't reconfigure the global logger (other tests rely on it)
            "logging": {"enable": False},
        }
        config.update(options)
        dav_app = WsgiDAVApp(config)
        if wsgi_input is None:
            return webtest.TestApp(dav_app)

        def app(environ, start_response):
            # Simulate a body that does not match the declared Content-Length
            environ["wsgi.input"] = wsgi_input
            return dav_app(environ, start_response)

        return webtest.TestApp(app)

    def _read(self, name="file.txt"):
        with open(os.path.join(self.root_path, name), "rb") as f:
            return f.read()

    # --- XML body -----------------------------------------------------------

    def test_xml_body_limit(self):
        app = self._app(max_xml_body_size=len(PROPFIND_BODY))
        headers = {"Depth": "0"}
        app.request("/", method="PROPFIND", body=PROPFIND_BODY, headers=headers)
        app.request(
            "/",
            method="PROPFIND",
            body=PROPFIND_BODY + b" ",
            headers=headers,
            status=413,
        )

    def test_xml_body_limit_default(self):
        app = self._app()
        body = PROPFIND_BODY + b" " * util.DEFAULT_MAX_XML_BODY_SIZE
        app.request(
            "/", method="PROPFIND", body=body, headers={"Depth": "0"}, status=413
        )
        # ... but can be disabled
        app = self._app(max_xml_body_size=None)
        app.request("/", method="PROPFIND", body=body, headers={"Depth": "0"})

    # --- PROPFIND depth -----------------------------------------------------

    def test_propfind_infinite(self):
        app = self._app()
        res = app.request("/", method="PROPFIND", headers={"Depth": "infinity"})
        assert res.status_int == 207

        app = self._app(allow_propfind_infinite=False)
        app.request("/", method="PROPFIND", headers={"Depth": "infinity"}, status=403)
        # A missing header means 'infinity'
        app.request("/", method="PROPFIND", status=403)
        res = app.request("/", method="PROPFIND", headers={"Depth": "1"})
        assert res.status_int == 207

    # --- Upload -------------------------------------------------------------

    def test_upload_limit(self):
        app = self._app(max_upload_size=10)
        app.put("/new.txt", params=b"0123456789", status=201)
        app.put("/file.txt", params=b"0123456789x", status=413)
        assert self._read() == b"original", "rejected before the file is touched"
        app.put("/new2.txt", params=b"0123456789x", status=413)
        assert not os.path.exists(os.path.join(self.root_path, "new2.txt"))

    def test_upload_limit_without_content_length(self):
        """The limit also applies if the declared length is wrong or missing."""
        app = self._app(io.BytesIO(b"x" * 100), max_upload_size=10)
        app.put("/file.txt", params=b"", status=413)
        assert self._read() == b"original"

    def test_no_upload_limit_by_default(self):
        app = self._app()
        app.put("/file.txt", params=b"x" * 100_000, status=204)
        assert len(self._read()) == 100_000

    # --- Failed upload ------------------------------------------------------

    def test_failed_put_keeps_previous_content(self):
        class BrokenInput:
            def __init__(self):
                self.count = 0

            def read(self, size=-1):
                self.count += 1
                if self.count > 2:
                    raise OSError("connection reset")
                return b"partial "

        app = self._app(BrokenInput())
        app.put("/file.txt", params=b"", status=500)
        assert self._read() == b"original"
        assert os.listdir(self.root_path).count("file.txt") == 1
        assert sorted(os.listdir(self.root_path)) == ["file.txt", "sub"]

    def test_put_replaces_content_and_keeps_mode(self):
        path = os.path.join(self.root_path, "file.txt")
        os.chmod(path, 0o640)
        app = self._app()
        app.put("/file.txt", params=b"new content", status=204)
        assert self._read() == b"new content"
        assert sorted(os.listdir(self.root_path)) == ["file.txt", "sub"]
        if os.name == "posix":
            assert os.stat(path).st_mode & 0o777 == 0o640

    # --- Response headers ---------------------------------------------------

    def test_files_are_served_with_nosniff(self):
        res = self._app().get("/file.txt")
        assert res.headers["X-Content-Type-Options"] == "nosniff"
        assert "Content-Security-Policy" not in res.headers

    def test_active_content_is_sandboxed(self):
        app = self._app()
        for name in ("x.html", "x.HTM", "x.svg", "x.xhtml", "x.xml"):
            app.put(f"/{name}", params=b"<script>alert(1)</script>", status=201)
            res = app.get(f"/{name}")
            assert res.headers["Content-Security-Policy"] == "sandbox", name
            assert res.headers["X-Content-Type-Options"] == "nosniff"
        for name in ("x.txt", "x.pdf", "x.png", "x.js", "x.unknown"):
            app.put(f"/{name}", params=b"<script>alert(1)</script>", status=201)
            assert "Content-Security-Policy" not in app.get(f"/{name}").headers, name

        app = self._app(sandbox_active_content=False)
        assert "Content-Security-Policy" not in app.get("/x.html").headers


class DiscardInputTest(unittest.TestCase):
    def test_discard_input_reads_in_blocks(self):
        class Input:
            def __init__(self, size):
                self.remaining = size
                self.max_requested = 0

            def read(self, size):
                self.max_requested = max(self.max_requested, size)
                n = min(size, self.remaining)
                self.remaining -= n
                return b"x" * n

        stream = Input(1_000_000)
        assert util.discard_input(stream, 1_000_000, block_size=4096) == 1_000_000
        assert stream.remaining == 0
        assert stream.max_requested == 4096

        # The declared length may be larger than what the client really sends
        stream = Input(10)
        assert util.discard_input(stream, 1_000_000, block_size=4096) == 10


if __name__ == "__main__":
    unittest.main()
