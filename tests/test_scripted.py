# -*- coding: iso-8859-1 -*-
# (c) 2009-2017 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
    Functional test suite for WsgiDAV.

    This test suite uses davclient to generate WebDAV requests.

    See http://chandlerproject.org/Projects/Davclient
        http://svn.osafoundation.org/tools/davclient/trunk/src/davclient/davclient.py
"""
from __future__ import print_function

import os
import time
import unittest
from tempfile import gettempdir
from threading import Thread

from tests import davclient
from tests.util import WsgiDavTestServer
from wsgidav import compat
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.server.ext_wsgiutils_server import ExtServer
from wsgidav.wsgidav_app import DEFAULT_CONFIG, WsgiDAVApp


# SERVER_ADDRESS
# (using localhost or mixing hostnames with IPs may be very slow!)
SERVER_ADDRESS = "http://127.0.0.1:8080"
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080

# RUN_OWN_SERVER
# When the PyDev Debugger is running, davclient requests will block
# (i.e. will not be handled by WsgiDAVServerThread)
# In this case, run WsgiDAV as external process and specify the URL here.
# This is also recommended when doing benchmarks:
RUN_OWN_SERVER = True

# RUN_SEPARATE_PROCESS
# False:
#    - Run ExtServer in a separate thread
#    - Cannot be debugged (requests and server locking each other)
#    - Logs to current console
# True:
#    - Run WsgiDavTestServer in a separate process
#    - Server log messages not visible 
RUN_SEPARATE_PROCESS = True

_test_server = None


def setUpModule():
    global _test_server
    if RUN_OWN_SERVER:
        if RUN_SEPARATE_PROCESS:
            _test_server = WsgiDavTestServer(with_auth=True, with_ssl=False)
            _test_server.start()            
        else:
            _test_server = WsgiDAVServerThread()
            _test_server.start()
            # let server start the loop, otherwise shutdown might lock
            time.sleep(.1)
    return


def tearDownModule():
    global _test_server
    
    if _test_server:
        if RUN_SEPARATE_PROCESS:
            _test_server.stop()            
        else:
            print("tearDownModule shutdown...")
            _test_server.shutdown()
            print("tearDownModule join...")
            _test_server.join()
            print("tearDownModule joined")
        _test_server = None
    return


# ========================================================================
# WsgiDAVServerThread
# ========================================================================
class WsgiDAVServerThread(Thread):
    """WsgiDAV server that can be run in a parallel thread."""

    def __init__(self):
        self.ext_server = None
        Thread.__init__(self)

    def __del__(self):
        self.shutdown()

    def run(self):
        print("WsgiDAVServerThread.run()...")
        withAuthentication = True
        self.rootpath = os.path.join(gettempdir(), "wsgidav-test")
        if not os.path.exists(self.rootpath):
            os.mkdir(self.rootpath)
        provider = FilesystemProvider(self.rootpath)

        config = DEFAULT_CONFIG.copy()
        config.update({
            "provider_mapping": {"/": provider},
            "user_mapping": {},
            "host": SERVER_HOST,
            "port": SERVER_PORT,
            "enable_loggers": [
                #                               "http_authenticator",
                #                               "lock_manager",
            ],
            "debug_methods": [],
            "propsmanager": True,      # True: use lock_manager.LockManager
            "locksmanager": True,      # True: use lock_manager.LockManager
            # None: domain_controller.WsgiDAVDomainController(user_mapping)
            "domaincontroller": None,
            "verbose": 2,
        })

        if withAuthentication:
            config["user_mapping"] = {"/": {"tester": {"password": "secret",
                                                       "description": "",
                                                       "roles": [],
                                                       },
                                            "tester2": {"password": "secret2",
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

        print("WsgiDAVServerThread ext_server.serve_forever_stoppable()...")
        self.ext_server.serve_forever_stoppable()
        print("WsgiDAVServerThread ext_server stopped.")
        self.ext_server = None
#        print "WsgiDAVServerThread.run() terminated"

    def shutdown(self):
        if self.ext_server:
            print("WsgiDAVServerThread.shutdown()...")
            # let server process pending requests, otherwise shutdown might
            # lock
            time.sleep(.1)
            self.ext_server.stop_serve_forever()
            self.ext_server = None
            print("WsgiDAVServerThread.shutdown()... complete")

# ========================================================================
# ServerTest
# ========================================================================


class ServerTest(unittest.TestCase):
    """Test wsgidav_app using davclient."""

    def setUp(self):
        self.client = davclient.DAVClient(SERVER_ADDRESS, logger=True)
        self.client.set_basic_auth("tester", "secret")
#        self.client.headers['new_header_for_session'] = "useful_example"

    def tearDown(self):
        del self.client

    def testPreconditions(self):
        """Environment must be set."""
        self.assertTrue(
            __debug__, "__debug__ must be True, otherwise asserts are ignored")

    def testGetPut(self):
        """Read and write file contents."""
        client = self.client

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
        client.checkResponse(201)  # created
        assert len(locks) == 1, "LOCK failed"
        token = locks[0]
        client.refresh_lock("/test/lock-0", token)
        client.checkResponse(200)  # ok
        client.unlock("/test/lock-0", token)
        client.checkResponse(204)  # no content
        client.unlock("/test/lock-0", token)
        # 409 Conflict, because resource was not locked
        # (http://www.webdav.org/specs/rfc4918.html#METHOD_UNLOCK)
        client.checkResponse(409)

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
#                headers={"Content-Length": compat.to_native(len(data1))},
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
        data = b"this is a file\nwith two lines"

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
        client2.put("/test/a/x", b"data")
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

        client2 = davclient.DAVClient(SERVER_ADDRESS, logger="DAVClient2")
        client2.set_basic_auth("tester2", "secret2")

        self._prepareTree0()

        # --- Check with deoth-infinity lock ----------------------------------
        # LOCK-infinity parent collection and try to access members
        locks = client1.set_lock("/test/a",
                                 owner="test-bench",
                                 locktype="write",
                                 lockscope="exclusive",
                                 depth="infinity")
        client1.checkResponse(200)
        assert len(locks) == 1, "LOCK failed"
        token = locks[0]

        # Unlock with correct token, but other principal: expect '403
        # Forbidden'
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

        # --- Check with depth-0 lock -----------------------------------------
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
        client2.put("/test/a/c", b"data")
        client2.checkResponse(204)
        # Modifying non-internal member resources is allowed
        client2.put("/test/a/b/f", b"data")
        client2.checkResponse(201)
        client2.mkcol("/test/a/b/g")
        client2.checkResponse(201)
        client2.move("/test/a/b/g", "/test/a/b/g2")
        client2.checkResponse(201)
        client2.delete("/test/a/b/g2")
        client2.checkResponse(204)

        # --- Check root access, when a child is locked -----------------------
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


# ========================================================================
# suite
# ========================================================================

if __name__ == "__main__":
    unittest.main()
