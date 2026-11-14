# (c) 2009-2026 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Functional test suite for WsgiDAV.

This test suite uses requests to generate HTTP requests.
"""

import json
import re
import unittest

import requests

from tests.util import WsgiDavTestServer

_test_server = None


def setUpModule():
    global _test_server
    _test_server = WsgiDavTestServer(
        with_auth=True,
        with_ssl=False,
        web_ui="dav_explorer",
    )
    _test_server.start()


def tearDownModule():
    if _test_server:
        _test_server.stop()


# ========================================================================
# ServerTest
# ========================================================================


class DavExplorerTest(unittest.TestCase):
    """Test wsgidav_app using requests."""

    def setUp(self):
        self.url = "http://127.0.0.1:8080/"
        self.auth = ("tester", "secret")

    def tearDown(self):
        pass

    def test_get(self):
        res = requests.get(self.url, auth=self.auth)
        assert res.status_code == 200
        assert '<meta name="generator" content="WsgiDAV/' in res.text
        assert res.encoding == "utf-8"
        assert "WsgiDAV" in res.headers["Server"]
        assert res.headers["Content-Type"] == "text/html; charset=utf-8"
        assert "<!-- WsgiDAV-UI: dav_explorer -->" in res.text

    def test_get_resources(self):
        """Server must respond to GET on a collection."""

        # Access collection (expect '200 Ok' with HTML response)
        res = requests.get(self.url, auth=self.auth)

        assert "<!-- WsgiDAV-UI: dav_explorer -->" in res.text, (
            "DAV Explorer UI not rendered"
        )
        assert "WsgiDAV - Index of /" in res.text, "Could not list root share"

        # Access unmapped resource (expect '404 Not Found')
        res = requests.get(self.url + "not-existing-124/", auth=self.auth)
        assert res.status_code == 404

        res = requests.get(self.url + "subfolder/", auth=self.auth)
        assert res.status_code == 200

        # seems to follow redirects?
        res = requests.get(self.url + "subfolder", auth=self.auth)
        assert res.status_code == 200

    def test_headers(self):
        res = requests.get(self.url, auth=self.auth)
        assert res.headers["X-Content-Type-Options"] == "nosniff"

        res = requests.head(self.url, auth=self.auth)
        assert res.status_code == 200
        assert res.text == ""

    def test_context_data(self):
        """The page passes a JSON config to the JavaScript app."""
        res = requests.get(self.url, auth=self.auth)
        config = get_context_data(res.text)
        assert config["readonly"] is False
        assert ".DS_Store" in config["ignore_list"]
        assert config["htdocs"] == "/:dav_explorer"
        # Not needed by the frontend
        assert "page_trailer" not in config

    def test_non_get_requests_pass_through(self):
        """WebDAV methods on collections must not be handled by the web UI."""
        res = requests.request(
            "PROPFIND", self.url, auth=self.auth, headers={"Depth": "1"}
        )
        assert res.status_code == 207
        assert "<!-- WsgiDAV-UI" not in res.text

    def test_assets_are_anonymous(self):
        """The JS/CSS assets are served without authentication."""
        for name in ("app.js", "util.js", "app.css"):
            res = requests.get(self.url + ":dav_explorer/" + name)
            assert res.status_code == 200, name

        # Removed dead module
        res = requests.get(self.url + ":dav_explorer/actions.js")
        assert res.status_code == 404


def get_context_data(html: str) -> dict:
    """Return the JSON config that the DAV Explorer page passes to JavaScript."""
    m = re.search(
        r'<script id="context-data" type="application/json">(.*?)</script>',
        html,
        re.DOTALL,
    )
    assert m, "context-data not found"
    return json.loads(m.group(1))
