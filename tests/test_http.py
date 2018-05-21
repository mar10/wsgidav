# -*- coding: iso-8859-1 -*-
# (c) 2009-2018 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
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
    _test_server = WsgiDavTestServer(with_auth=True, with_ssl=False)
    _test_server.start()


def tearDownModule():
    global _test_server

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

    def testGetPut(self):
        res = requests.get(self.url, auth=self.auth)
        assert res.status_code == 200
        assert "<meta name='generator' content='WsgiDAV" in res.text