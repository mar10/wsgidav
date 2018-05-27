# -*- coding: utf-8 -*-
# (c) 2009-2018 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
    Unit test for wsgidav HTTP request functionality

    This test suite uses webtest.TestApp to send fake requests to the WSGI
    stack.

    See http://webtest.readthedocs.org/en/latest/
        (successor of http://pythonpaste.org/testing-applications.html)
"""
from __future__ import print_function

import os
import shutil
import sys
import unittest
from tempfile import gettempdir

from wsgidav import compat, util
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.wsgidav_app import WsgiDAVApp

try:
    import webtest
except ImportError:
    print("*" * 70, file=sys.stderr)
    print("Could not import webtest.TestApp: some tests will fail.", file=sys.stderr)
    print("Try 'pip install WebTest' or use 'python setup.py test' to run these tests.",
          file=sys.stderr)
    print("*" * 70, file=sys.stderr)
    raise

# ========================================================================
# ServerTest
# ========================================================================


class ServerTest(unittest.TestCase):
    """Test wsgidav_app using paste.fixture."""

    def _makeWsgiDAVApp(self, withAuthentication):
        self.rootpath = os.path.join(gettempdir(), "wsgidav-test")
        if not os.path.exists(self.rootpath):
            os.mkdir(self.rootpath)
        provider = FilesystemProvider(self.rootpath)

        # config = DEFAULT_CONFIG.copy()
        # config.update({
        config = {
            "provider_mapping": {"/": provider},
            "user_mapping": {},
            "verbose": 1,
            "enable_loggers": [],
            "property_manager": None,      # None: no property manager
            "lock_manager": True,      # True: use lock_manager.LockManager
            # None: domain_controller.WsgiDAVDomainController(user_mapping)
            "domain_controller": None,
            }

        if withAuthentication:
            config["user_mapping"] = {"/": {"tester": {"password": "secret",
                                                       "description": "",
                                                       "roles": [],
                                                       },
                                            },
                                      }
            config["accept_basic"] = True
            config["accept_digest"] = False
            config["default_to_digest"] = False

        return WsgiDAVApp(config)

    def setUp(self):
        wsgi_app = self._makeWsgiDAVApp(False)
        self.app = webtest.TestApp(wsgi_app)

    def tearDown(self):
        shutil.rmtree(compat.to_unicode(self.rootpath))
        del self.app

    def testPreconditions(self):
        """Environment must be set."""
        self.assertTrue(
            __debug__, "__debug__ must be True, otherwise asserts are ignored")

    def testDirBrowser(self):
        """Server must respond to GET on a collection."""
        app = self.app
        # Access collection (expect '200 Ok' with HTML response)
        res = app.get("/", status=200)
        assert "WsgiDAV - Index of /" in res, "Could not list root share"

        # Access unmapped resource (expect '404 Not Found')
        res = app.get("/not-existing-124/", status=404)

    def testGetPut(self):
        """Read and write file contents."""
        app = self.app

        # Prepare file content
        data1 = b"this is a file\nwith two lines"
        data2 = b"this is another file\nwith three lines\nsee?"
        # Big file with 10 MB
        lines = []
        line = "." * (1000 - 6 - len("\n"))
        for i in compat.xrange(10 * 1000):
            lines.append("%04i: %s\n" % (i, line))
        data3 = "".join(lines)
        data3 = compat.to_bytes(data3)

        # Remove old test files
        app.delete("/file1.txt", expect_errors=True)
        app.delete("/file2.txt", expect_errors=True)
        app.delete("/file3.txt", expect_errors=True)

        # Access unmapped resource (expect '404 Not Found')
        app.delete("/file1.txt", status=404)
        app.get("/file1.txt", status=404)

        # PUT a small file (expect '201 Created')
        app.put("/file1.txt", params=data1, status=201)

        res = app.get("/file1.txt", status=200)
        assert res.body == data1, "GET file content different from PUT"

        # PUT overwrites a small file (expect '204 No Content')
        app.put("/file1.txt", params=data2, status=204)

        res = app.get("/file1.txt", status=200)
        assert res.body == data2, "GET file content different from PUT"

        # PUT writes a big file (expect '201 Created')
        app.put("/file2.txt", params=data3, status=201)

        res = app.get("/file2.txt", status=200)
        assert res.body == data3, "GET file content different from PUT"

        # Request must not contain a body (expect '415 Media Type Not
        # Supported')
        app.request("/file1.txt",
                    method="GET",
                    headers={"Content-Length": compat.to_native(len(data1))},
                    body=data1,
                    status=415)

        # Delete existing resource (expect '204 No Content')
        app.delete("/file1.txt", status=204)
        # Get deleted resource (expect '404 Not Found')
        app.get("/file1.txt", status=404)

        # PUT a small file (expect '201 Created')
        app.put("/file1.txt", params=data1, status=201)

    def testEncoding(self):
        """Handle special characters."""
        app = self.app
        uniData = u"This is a file with special characters:\n" \
            + u"Umlaute(äöüß)\n" \
            + u"Euro(\u20AC)\n" \
            + u"Male(\u2642)"

        data = uniData.encode("utf8")

        # From PEP 3333:
        # enc, esc = sys.getfilesystemencoding(), 'surrogateescape'
        # def unicode_to_wsgi(u):
        #     # Convert an environment variable to a WSGI "bytes-as-unicode" string
        #     return u.encode(enc, esc).decode('iso-8859-1')
        # def wsgi_to_bytes(s):
        #     return s.encode('iso-8859-1')

        def __testrw(filename):
            # print(util.stringRepr(filename))
            app.delete(filename, expect_errors=True)
            app.put(filename, params=data, status=201)
            res = app.get(filename, status=200)
            assert res.body == data, "GET file content different from PUT"

        # filenames with umlauts äöüß
        #
        # See https://www.python.org/dev/peps/pep-3333/#unicode-issues
        # NOTE:
        #   Only latin-1 encoded bytestrings are allowed in filenames
        #
        # TODO: Py3: seems that webtest.TestApp
        #   - Py2: only supports latin-1 bytestrings?
        #   - Py3: only supports ascii

        def unicode_to_url(s):
            # TODO: Py3: Is this the correct way?
            return compat.quote(s.encode("utf8"))

        # äöüß: (part of latin1)
        __testrw(unicode_to_url(u"/file uml(\u00E4\u00F6\u00FC\u00DF).txt"))
        # Euro sign (not latin1, but Cp1252)
        __testrw(unicode_to_url(u"/file euro(\u20AC).txt"))
        # Male sign (only utf8)
        __testrw(unicode_to_url(u"/file male(\u2642).txt"))

    def testAuthentication(self):
        """Require login."""
        # Prepare file content (currently without authentication)
        data1 = b"this is a file\nwith two lines"
        app = self.app
        app.get("/file1.txt", status=404)  # not found
        app.put("/file1.txt", params=data1, status=201)
        app.get("/file1.txt", status=200)

        # Re-create test app with authentication
        wsgi_app = self._makeWsgiDAVApp(True)
        app = self.app = webtest.TestApp(wsgi_app)

        # Anonymous access must fail (expect 401 Not Authorized)
        # Existing resource
        app.get("/file1.txt", status=401)
        # Non-existing resource
        app.get("/not_existing_file.txt", status=401)
        # Root container
        app.get("/", status=401)

        # Try basic access authentication
        user = "tester"
        password = "secret"
        creds = util.calc_base64(user + ":" + password)
        headers = {"Authorization": "Basic %s" % creds,
                   }
        # Existing resource
        app.get("/file1.txt", headers=headers, status=200)
        # Non-existing resource (expect 404 NotFound)
        app.get("/not_existing_file.txt", headers=headers, status=404)


# ========================================================================


if __name__ == "__main__":
    unittest.main()
