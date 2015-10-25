# -*- coding: iso-8859-1 -*-
# (c) 2009-2015 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
    Functional test suite for WsgiDAV.

    This test suite uses davclient to generate WebDAV requests.

    See http://chandlerproject.org/Projects/Davclient
        http://svn.osafoundation.org/tools/davclient/trunk/src/davclient/davclient.py
"""
from __future__ import print_function

import os
import time
from tempfile import gettempdir
from threading import Thread
import unittest

from tests import davclient
from wsgidav import compat
from wsgidav.wsgidav_app import DEFAULT_CONFIG, WsgiDAVApp
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.server.ext_wsgiutils_server import ExtServer


#===============================================================================
# EXTERNAL_SERVER_ADDRESS
# <None> means 'start WsgiDAV as parallel thread'
#
# When the PyDev Debugger is running, then davclient requests will block
# (i.e. will not be handled by WsgiDAVServerThread)
# In this case, run WsgiDAV as external process and specify the URL here.
# This is also recommended when doing benchmarks
#===============================================================================
EXTERNAL_SERVER_ADDRESS = None
#EXTERNAL_SERVER_ADDRESS = "http://127.0.0.1:8080"

#===============================================================================
# WsgiDAVServerThread
#===============================================================================
class WsgiDAVServerThread(Thread):
    """WsgiDAV server that can be run in a parallel thread."""
    def __init__ (self):
        Thread.__init__(self)
        self.ext_server = None

    def __del__(self):
        self.shutdown()

    def run(self):
        withAuthentication = True
        self.rootpath = os.path.join(gettempdir(), "wsgidav-test")
        if not os.path.exists(self.rootpath):
            os.mkdir(self.rootpath)
        provider = FilesystemProvider(self.rootpath)

        config = DEFAULT_CONFIG.copy()
        config.update({
            "provider_mapping": {"/": provider},
            "user_mapping": {},
            "host": "localhost",
            "port": 8080,
            "enable_loggers": [
#                               "http_authenticator",
#                               "lock_manager",
                               ],
            "debug_methods": [ ],
            "propsmanager": True,      # True: use lock_manager.LockManager
            "locksmanager": True,      # True: use lock_manager.LockManager
            "domaincontroller": None,  # None: domain_controller.WsgiDAVDomainController(user_mapping)
            "verbose": 2,
            })

        if withAuthentication:
            config["user_mapping"] = {"/": {"tester": {"password": "tester",
                                                       "description": "",
                                                       "roles": [],
                                                       },
                                            "tester2": {"password": "tester2",
                                                       "description": "",
                                                       "roles": [],
                                                       },
                                            },
                                      }
            config["acceptbasic"] = True
            config["acceptdigest"] = False
            config["defaultdigest"] = False

        app = WsgiDAVApp(config)

        self.ext_server = ExtServer((config["host"], config["port"]),
                                    {"": app})

        self.ext_server.serve_forever_stoppable()
        self.ext_server = None
#        print "WsgiDAVServerThread.run() terminated"

    def shutdown(self):
        if self.ext_server:
#            print "WsgiDAVServerThread.shutdown()..."
            # let server process pending requests, otherwise shutdown might lock
            time.sleep(.1)
            self.ext_server.stop_serve_forever()
#            try:
#                # since Python 2.6
#                self.ext_server.shutdown()
#            except AttributeError:
#                pass
            self.ext_server = None
#            print "WsgiDAVServerThread.shutdown()... complete"

#===============================================================================
# ServerTest
#===============================================================================
class ServerTest(unittest.TestCase):
    """Test wsgidav_app using davclient."""

#     @classmethod
#     def suite(cls):
#         """Return test case suite (so we can control the order)."""
#         suite = unittest.TestSuite()
#         suite.addTest(cls("testPreconditions"))
# #        suite.addTest(cls("testGetPut"))
#         suite.addTest(cls("testLocking"))
#         return suite


    def setUp(self):
#        print "setUp"
        if EXTERNAL_SERVER_ADDRESS:
            self.server_thread = None
            self.client = davclient.DAVClient(EXTERNAL_SERVER_ADDRESS)
        else:
            self.server_thread = WsgiDAVServerThread()
            self.server_thread.start()
            # let server start the loop, otherwise shutdown might lock
            time.sleep(.1)
            self.client = davclient.DAVClient("http://127.0.0.1:8080/")

        self.client.set_basic_auth("tester", "tester")
#        self.client.headers['new_header_for_session'] = "useful_example"


    def tearDown(self):
#        print "tearDown"
        del self.client
        if self.server_thread:
            self.server_thread.shutdown()
    #        print "tearDown join..."
            self.server_thread.join()
            self.server_thread = None
    #        print "tearDown joined"
#        os.rmdir(self.rootpath)


    def testPreconditions(self):
        """Environment must be set."""
        self.assertTrue(__debug__, "__debug__ must be True, otherwise asserts are ignored")


    def testGetPut(self):
        """Read and write file contents."""
        client = self.client

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

        # Cleanup
        client.delete("/test/")
        client.mkcol("/test/")
        client.checkResponse(201)

        # PUT files
        client.put("/test/file1.txt", data1)
        client.checkResponse(201)
        client.put("/test/file2.txt", data2)
        client.checkResponse(201)
        client.put("/test/bigfile.txt", data3)
        client.checkResponse(201)

        body = client.get("/test/file1.txt")
        client.checkResponse(200)
        assert body == data1, "Put/Get produced different bytes"


        # PUT with overwrite must return 204 No Content, instead of 201 Created
        client.put("/test/file2.txt", data2)
        client.checkResponse(204)

        client.mkcol("/test/folder")
        client.checkResponse(201)

        locks = client.set_lock("/test/lock-0",
                                owner="test-bench",
                                locktype="write",
                                lockscope="exclusive",
                                depth="infinity")
        client.checkResponse(201)
        assert len(locks) == 1, "LOCK failed"
        token = locks[0]
        client.refresh_lock("/test/lock-0", token)
        client.checkResponse()
        client.unlock("/test/lock-0", token)
        client.checkResponse(204)
        client.unlock("/test/lock-0", token)
#        client.checkResponse()

        client.proppatch("/test/file1.txt",
                         set_props=[("{testns:}testname", "testval"),
                                    ],
                         remove_props=None)
        client.checkResponse()

        client.copy("/test/file1.txt",
                    "/test/file2.txt",
                    depth='infinity', overwrite=True)
        client.checkResponse()

        client.move("/test/file2.txt",
                    "/test/file2_moved.txt",
                    depth='infinity', overwrite=True)
        client.checkResponse()

        client.propfind("/",
                        properties="allprop",
                        namespace='DAV:',
                        depth=None,
                        headers=None)
        client.checkResponse()

#        print client.response.tree

#        print dict(client.response.getheaders())

#        # Remove old test files
#
#        # Access unmapped resource (expect '404 Not Found')
#        app.delete("/file1.txt", status=404)
#        app.get("/file1.txt", status=404)
#
#        # PUT a small file (expect '201 Created')
#        app.put("/file1.txt", params=data1, status=201)
#
#        res = app.get("/file1.txt", status=200)
#        assert res.body == data1, "GET file content different from PUT"
#
#        # PUT overwrites a small file (expect '204 No Content')
#        app.put("/file1.txt", params=data2, status=204)
#
#        res = app.get("/file1.txt", status=200)
#        assert res.body == data2, "GET file content different from PUT"
#
#        # PUT writes a big file (expect '201 Created')
#        app.put("/file2.txt", params=data3, status=201)
#
#        res = app.get("/file2.txt", status=200)
#        assert res.body == data3, "GET file content different from PUT"
#
#        # Request must not contain a body (expect '415 Media Type Not Supported')
#        app.get("/file1.txt",
#                headers={"Content-Length": to_native(len(data1))},
#                params=data1,
#                status=415)
#
#        # Delete existing resource (expect '204 No Content')
#        app.delete("/file1.txt", status=204)
#        # Get deleted resource (expect '404 Not Found')
#        app.get("/file1.txt", status=404)
#
#        # PUT a small file (expect '201 Created')
#        app.put("/file1.txt", params=data1, status=201)


    def _prepareTree0(self):
        """Create a resource structure for testing.

        /test/a/
                b/
                  d
                c
              x/
                y
        """
        client = self.client
        data = "this is a file\nwith two lines"

        client.delete("/test/")
        client.mkcol("/test/")
        client.mkcol("/test/a")
        client.mkcol("/test/a/b")
        client.mkcol("/test/x")
        client.put("/test/a/c", data)
        client.put("/test/a/b/d", data)
        client.put("/test/x/y", data)
        client.checkResponse(201)


    def _checkCommonLock(self, client2):
        """Check for access when /test/a/ of our sample tree is locked.

        These operations must be protected when our sample tree is locked
        either 0 or infinite depth, so we expect '423 Locked'.

        Since all operations fail, the tree is unmodified.

        See http://www.webdav.org/specs/rfc4918.html#write.locks.and.collections
        """
        # DELETE a collection's direct internal member
        client2.delete("/test/a/b")
        client2.checkResponse(423)
        client2.delete("/test/a/c")
        client2.checkResponse(423)
        # MOVE an internal member out of the collection
        client2.move("/test/a/b", "/test/x/a")
        client2.checkResponse(423)
        client2.move("/test/a/c", "/test/x/c")
        client2.checkResponse(423)
        # MOVE an internal member into the collection
        client2.move("/test/x/y", "/test/a")
        client2.checkResponse(423)
        client2.move("/test/x/y", "/test/a/y")
        client2.checkResponse(423)
        # MOVE to rename an internal member within a collection
        client2.move("/test/a/c", "/test/a/c2")
        client2.checkResponse(423)
        # COPY an internal member into a collection
        client2.copy("/test/x/y", "/test/a/y")
        client2.checkResponse(423)
        # PUT or MKCOL request that would create a new internal member
        client2.put("/test/a/x", "data")
        client2.checkResponse(423)
        client2.mkcol("/test/a/e")
        client2.checkResponse(423)
        # LOCK must fail
        _locks = client2.set_lock("/test/a",
                                  owner="test-bench",
                                  depth="0")
        client2.checkResponse(423)
        _locks = client2.set_lock("/test/a",
                                  owner="test-bench",
                                  depth="infinity")
        client2.checkResponse(423)
        _locks = client2.set_lock("/test",
                                  owner="test-bench",
                                  depth="infinity")
        client2.checkResponse(423)
        # Modifying properties of the locked resource must fail
        client2.proppatch("/test/a",
                          set_props=[("{testns:}testname", "testval")])
        client2.checkResponse(423)


    def testLocking(self):
        """Locking."""
        client1 = self.client

        client2 = davclient.DAVClient("http://127.0.0.1:8080/")
        client2.set_basic_auth("tester2", "tester2")

        self._prepareTree0()

        # --- Check with deoth-infinity lock -----------------------------------
        # LOCK-infinity parent collection and try to access members
        locks = client1.set_lock("/test/a",
                                 owner="test-bench",
                                 locktype="write",
                                 lockscope="exclusive",
                                 depth="infinity")
        client1.checkResponse(200)
        assert len(locks) == 1, "LOCK failed"
        token = locks[0]

        # Unlock with correct token, but other principal: expect '403 Forbidden'
        client2.unlock("/test/a", token)
        client2.checkResponse(403)

        # Check that commonly protected operations fail
        self._checkCommonLock(client2)

        # Check operations that are only protected when /test/a is locked
        # with depth-infinity

        locks = client2.set_lock("/test/a/b/c",
                                 owner="test-bench",
                                 locktype="write",
                                 lockscope="exclusive",
                                 depth="0")
        client2.checkResponse(423)

        locks = client2.set_lock("/test/a/b/d",
                                 owner="test-bench",
                                 locktype="write",
                                 lockscope="exclusive",
                                 depth="infinity")
        client2.checkResponse(423)

        locks = client2.set_lock("/test/a/b/c",
                                 owner="test-bench",
                                 locktype="write",
                                 lockscope="exclusive",
                                 depth="0")
        client2.checkResponse(423)

        # client1 can LOCK /a and /a/b/d at the same time, but must
        # provide both tokens in order to access a/b/d
        # TODO: correct?
#        locks = client1.set_lock("/test/a/b/d",
#                                 owner="test-bench",
#                                 locktype="write",
#                                 lockscope="exclusive",
#                                 depth="0")
#        client1.checkResponse(200)
#        assert len(locks) == 1, "Locking inside below locked collection failed"
#        tokenABD = locks[0]


        # --- Check with depth-0 lock ------------------------------------------
        # LOCK-0 parent collection and try to access members
        client1.unlock("/test/a", token)
        client1.checkResponse(204)

        locks = client1.set_lock("/test/a",
                                 owner="test-bench",
                                 locktype="write",
                                 lockscope="exclusive",
                                 depth="0")
        client1.checkResponse(200)
        assert len(locks) == 1, "LOCK failed"
        token = locks[0]

        # Check that commonly protected operations fail
        self._checkCommonLock(client2)

        # These operations are allowed with depth-0
        # Modifying member properties is allowed
        client2.proppatch("/test/a/c",
                          set_props=[("{testns:}testname", "testval")])
        client2.checkMultiStatusResponse(200)
        # Modifying a member without creating a new resource is allowed
        client2.put("/test/a/c", "data")
        client2.checkResponse(204)
        # Modifying non-internal member resources is allowed
        client2.put("/test/a/b/f", "data")
        client2.checkResponse(201)
        client2.mkcol("/test/a/b/g")
        client2.checkResponse(201)
        client2.move("/test/a/b/g", "/test/a/b/g2")
        client2.checkResponse(201)
        client2.delete("/test/a/b/g2")
        client2.checkResponse(204)

        # --- Check root access, when a child is locked ------------------------
        client1.unlock("/test/a", token)
        client1.checkResponse(204)

        locks = client1.set_lock("/test/a/b/d",
                                 owner="test-bench",
                                 locktype="write",
                                 lockscope="exclusive",
                                 depth="0")
        client1.checkResponse(200)
        assert len(locks) == 1, "LOCK failed"
        token = locks[0]

        # LOCK /a/b/d, then DELETE /a/b/
        # --> Must delete all but a/b/d (expect 423 Locked inside Multistatus)
        client2.delete("/test/a/b")
#        print client2.response.body
        client2.checkMultiStatusResponse(423)


#===============================================================================
# suite
#===============================================================================
# def suite():
#     """Return suites of all test cases."""
#     return unittest.TestSuite([ServerTest.suite(),
#                                ])

# def main():
#     _suite = suite()
#     unittest.TextTestRunner(descriptions=1, verbosity=2).run(_suite)

if __name__ == "__main__":
    unittest.main()
# #    global EXTERNAL_SERVER_ADDRESS
# #    EXTERNAL_SERVER_ADDRESS = "http://127.0.0.1:8080"
# #    print "Using external server to enable debugging: ", EXTERNAL_SERVER_ADDRESS
#
#     main()
