# -*- coding: utf-8 -*-
# (c) 2009-2015 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
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
from tempfile import gettempdir
import unittest

from wsgidav import compat
from wsgidav import util
from wsgidav.compat import to_unicode
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.wsgidav_app import DEFAULT_CONFIG, WsgiDAVApp

try:
    from webtest import TestApp
except ImportError:
    print("*" * 70, file=sys.stderr)
    print("Could not import webtest.TestApp: some tests will fail.", file=sys.stderr)
    print("Try 'pip install WebTest' or use 'python setup.py test' to run these tests.", file=sys.stderr)
    print("*" * 70, file=sys.stderr)
    raise

#===============================================================================
# ServerTest
#===============================================================================
class ServerTest(unittest.TestCase):
    """Test wsgidav_app using paste.fixture."""

    def _makeWsgiDAVApp(self, withAuthentication):
        self.rootpath = os.path.join(gettempdir(), "wsgidav-test")
        if not os.path.exists(self.rootpath):
            os.mkdir(self.rootpath)
        provider = FilesystemProvider(self.rootpath)

        config = DEFAULT_CONFIG.copy()
        config.update({
            "provider_mapping": {"/": provider},
            "user_mapping": {},
            "verbose": 1,
            "enable_loggers": [],
            "propsmanager": None,      # None: no property manager
            "locksmanager": True,      # True: use lock_manager.LockManager
            "domaincontroller": None,  # None: domain_controller.WsgiDAVDomainController(user_mapping)
            })

        if withAuthentication:
            config["user_mapping"] = {"/": {"tester": {"password": "secret",
                                                       "description": "",
                                                       "roles": [],
                                                       },
                                            },
                                      }
            config["acceptbasic"] = True
            config["acceptdigest"] = False
            config["defaultdigest"] = False

        return WsgiDAVApp(config)


    def setUp(self):
        wsgi_app = self._makeWsgiDAVApp(False)
        self.app = TestApp(wsgi_app)


    def tearDown(self):
        shutil.rmtree(to_unicode(self.rootpath))
        del self.app


    def testPreconditions(self):
        """Environment must be set."""
        self.assertTrue(__debug__, "__debug__ must be True, otherwise asserts are ignored")


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
        line = "." * (1000-6-len("\n"))
        for i in compat.xrange(10*1000):
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

        # Request must not contain a body (expect '415 Media Type Not Supported')
        # TODO: Py3: webtest.TestApp fails here
        app.get("/file1.txt",
                headers={"Content-Length": compat.to_native(len(data1))},
                params=data1,
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

        def __testrw(filename):
            # Write/read UTF-8 encoded file name
            # filename = compat.to_bytes(filename)
            # filename = compat.to_unicode(filename)
            print(util.stringRepr(filename))

            app.delete(filename, expect_errors=True)
            app.put(filename, params=data, status=201)
            res = app.get(filename, status=200)
            assert res.body == data, "GET file content different from PUT"

        # filenames with umlauts äöüß
        # TODO: Py3: seems that webtest.TestApp
        #   - Py2: only supports latin-1 bytestrings?
        #   - Py3: only supports ascii
        # __testrw(b"/file uml(\xE4\xF6\xFC\xDF).txt".decode("latin1"))
        __testrw(b"/file uml(\xE4\xF6\xFC\xDF).txt")
        __testrw(u"/file uml(\u00E4\u00F6\u00FC\u00DF).txt".encode("latin1"))
        # UTF-8 encoded filenames
        __testrw(b"/file euro(\xE2\x82\xAC).txt")
        __testrw(b"/file male(\xE2\x99\x82).txt")


    def testAuthentication(self):
        """Require login."""
        # Prepare file content (currently without authentication)
        data1 = b"this is a file\nwith two lines"
        app = self.app
        app.get("/file1.txt", status=404) # not found
        app.put("/file1.txt", params=data1, status=201)
        app.get("/file1.txt", status=200)

        # Re-create test app with authentication
        wsgi_app = self._makeWsgiDAVApp(True)
        app = self.app = TestApp(wsgi_app)

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


#===============================================================================


if __name__ == "__main__":
    unittest.main()
