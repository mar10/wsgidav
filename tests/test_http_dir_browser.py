# (c) 2009-2024 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Functional test suite for WsgiDAV.

This test suite uses requests to generate HTTP requests.
"""

import unittest

import requests

from tests.util import WsgiDavTestServer

_test_server = None


def setUpModule():
    global _test_server
    _test_server = WsgiDavTestServer(
        with_auth=True,
        with_ssl=False,
        web_ui="dir_browser",
    )
    _test_server.start()


def tearDownModule():
    if _test_server:
        _test_server.stop()


# ========================================================================
# ServerTest
# ========================================================================


class DirbrowserTest(unittest.TestCase):
    """Test wsgidav_app using requests."""

    def setUp(self):
        self.url = "http://127.0.0.1:8080/"
        self.auth = ("tester", "secret")

    def tearDown(self):
        pass

    def testGet(self):
        res = requests.get(self.url, auth=self.auth)
        assert res.status_code == 200
        assert '<meta name="generator" content="WsgiDAV/' in res.text
        assert res.encoding == "utf-8"
        assert "WsgiDAV" in res.headers["Server"]
        assert res.headers["Content-Type"] == "text/html; charset=utf-8"

        res = requests.get(self.url, auth=self.auth)
        assert res.status_code == 200
        assert "<!-- WsgiDAV-UI: dir_browser -->" in res.text

    def testGetResources(self):
        """Server must respond to GET on a collection."""
        # Access collection (expect '200 Ok' with HTML response)
        res = requests.get(self.url, auth=self.auth)
        assert res.status_code == 200
        assert "<!-- WsgiDAV-UI: dir_browser -->" in res.text

        assert "WsgiDAV - Index of /" in res.text, "Could not list root share"
        assert "readme.txt" in res.text, "Fixture content"
        assert "Lotosblütenstengel (蓮花莖).docx" in res.text, "Encoded fixture content"

        # Access unmapped resource (expect '404 Not Found')
        res = requests.get(self.url + "not-existing-124/", auth=self.auth)
        assert res.status_code == 404

        res = requests.get(self.url + "subfolder/", auth=self.auth)
        assert res.status_code == 200
        # res = requests.get(self.url + "subfolder", auth=self.auth)
        # seems to follow redirects?
        res = requests.get(self.url + "subfolder", auth=self.auth)

    def testGetDavMount(self):
        res = requests.get(self.url, auth=self.auth)
        assert res.status_code == 200
        assert '<meta name="generator" content="WsgiDAV/' in res.text
        assert res.encoding == "utf-8"
        assert "WsgiDAV" in res.headers["Server"]
        assert res.headers["Content-Type"] == "text/html; charset=utf-8"

        res = requests.get(self.url + "?davmount", auth=self.auth)
        assert res.status_code == 200
        assert '<dm:mount xmlns:dm="http://purl.org/NET/webdav/mount">' in res.text
        assert res.headers["Content-Type"] == "application/davmount+xml"
