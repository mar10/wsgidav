# -*- coding: iso-8859-1 -*-
# (c) 2009-2017 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
    Run litmus against WsgiDAV server.
"""
from __future__ import print_function

import subprocess
import unittest

from tests.util import WsgiDavTestServer


# ========================================================================
# WsgiDAVServerTest
# ========================================================================

class WsgiDAVLitmusTest(unittest.TestCase):
    """Run litmus test suite against builtin server."""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def _report_missing_litmus(self):
        print("*" * 70)
        print("This test requires the litmus test suite.")
        print("See http://www.webdav.org/neon/litmus/")
        print("*" * 70)
        raise unittest.SkipTest("Test requires litmus test suite")

    def test_litmus_with_authentication(self):
        """Run litmus test suite on HTTP with authentification."""
        with WsgiDavTestServer(with_auth=True, with_ssl=False):
            try:
                res = subprocess.call(
                    ["litmus", "http://127.0.0.1:8080/", "tester", "secret"])
                self.assertEqual(res, 0, "litmus suite failed: check the log")
            except OSError:
                self._report_missing_litmus()
                raise
        return

    def test_litmus_anonymous(self):
        """Run litmus test suite on HTTP with authentification."""
        with WsgiDavTestServer(with_auth=False, with_ssl=False):
            try:
                res = subprocess.call(["litmus", "http://127.0.0.1:8080/"])
                self.assertEqual(res, 0, "litmus suite failed: check the log")
            except OSError:
                self._report_missing_litmus()
                raise
        return

    def test_litmus_with_ssl_and_authentication(self):
        """Run litmus test suite on SSL / HTTPS with authentification."""
        with WsgiDavTestServer(with_auth=True, with_ssl=True):
            try:
                res = subprocess.call(
                    ["litmus", "https://127.0.0.1:8080/", "tester", "secret"])
                self.assertEqual(res, 0, "litmus suite failed: check the log")
            except OSError:
                self._report_missing_litmus()
                raise
        return


# ========================================================================
# suite
# ========================================================================

if __name__ == "__main__":
    unittest.main()
