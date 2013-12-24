# -*- coding: iso-8859-1 -*-
# (c) 2009-2013 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
    Run litmus against WsgiDAV server.
"""
from tempfile import gettempdir
from wsgidav.wsgidav_app import DEFAULT_CONFIG, WsgiDAVApp
from wsgidav.fs_dav_provider import FilesystemProvider
import os
import unittest
import subprocess
from multiprocessing.process import Process
import time



def run_wsgidav_server(with_auth, with_ssl):
    """
    """
    rootpath = os.path.join(gettempdir(), "wsgidav-test")
    if not os.path.exists(rootpath):
        os.mkdir(rootpath)

    provider = FilesystemProvider(rootpath)

    config = DEFAULT_CONFIG.copy()
    config.update({
        "host": "localhost",
        "port": 8080,
        "provider_mapping": {"/": provider},
        "domaincontroller": None, # None: domain_controller.WsgiDAVDomainController(user_mapping)
        "user_mapping": {},
        "verbose": 0,
        "enable_loggers": [],
        "propsmanager": True,      # None: no property manager
        "locksmanager": True,      # True: use lock_manager.LockManager
        "domaincontroller": None,  # None: domain_controller.WsgiDAVDomainController(user_mapping)
        })

    if with_auth:
        config.update({
            "user_mapping": {"/": {"tester": {"password": "tester",
                                                   "description": "",
                                                   "roles": [],
                                                   },
                                        },
                                  },
            "acceptbasic": True,
            "acceptdigest": False,
            "defaultdigest": False,
            })

    if with_ssl:
        config.update({
            "ssl_certificate": "wsgidav/server/sample_bogo_server.crt",
            "ssl_private_key": "wsgidav/server/sample_bogo_server.key",
            "ssl_certificate_chain": None,
            })
    app = WsgiDAVApp(config)

    from wsgidav.server.run_server import _runBuiltIn
    _runBuiltIn(app, config, None)
    # blocking...



#===============================================================================
# WsgiDAVServerTest
#===============================================================================

class WsgiDAVLitmusTest(unittest.TestCase):
    """Test the built-in WsgiDAV server with cadaver."""

    def setUp(self):
        pass


    def tearDown(self):
        pass


    def test_litmus_with_authentication(self):
        """Run litmus test suite on HTTP with authentication."""
        try:
            proc = Process(target=run_wsgidav_server, args=(True, False))
            proc.daemon = True
            proc.start()
            time.sleep(1)

            try:
                self.assertEqual(subprocess.call(["litmus", "http://localhost:8080/", "tester", "tester"]),
                                 0,
                                 "litmus suite failed: check the log")
            except OSError:
                print "*" * 70
                print "This test requires the litmus test suite."
                print "See http://www.webdav.org/neon/litmus/"
                print "*" * 70
                raise

        finally:
            proc.terminate()
            proc.join()
#             time.sleep(0.5)


    # This test with anonymous access fails here:
    #
#  0. init.................. pass
#  1. begin................. pass
#  2. expect100............. FAIL (timeout waiting for interim response)
#  3. finish................ pass

    # def test_litmus_anonymous(self):
    #     """Run litmus test suite as anonymous."""
    #     try:
    #         proc = Process(target=run_wsgidav_server, args=(False, False))
    #         proc.daemon = True
    #         proc.start()
    #         time.sleep(1)

    #         try:
    #             self.assertEqual(subprocess.call(["litmus", "http://localhost:8080/"]),
    #                              0,
    #                              "litmus suite failed: check the log")
    #         except OSError:
    #             print "This test requires the litmus test suite."
    #             print "See http://www.webdav.org/neon/litmus/"
    #             raise

    #     finally:
    #         proc.terminate()
    #         proc.join()


    def test_litmus_with_ssl_and_authentication(self):
        """Run litmus test suite on HTTP with authentication."""
        try:
            proc = Process(target=run_wsgidav_server, args=(True, True))
            proc.daemon = True
            proc.start()
            time.sleep(1)

            try:
                self.assertEqual(subprocess.call(["litmus", "https://localhost:8080/", "tester", "tester"]),
                                 0,
                                 "litmus suite failed: check the log")
            except OSError:
                print "*" * 70
                print "This test requires the litmus test suite."
                print "See http://www.webdav.org/neon/litmus/"
                print "*" * 70
                raise

        finally:
            proc.terminate()
            proc.join()
#             time.sleep(0.5)



#===============================================================================
# suite
#===============================================================================

if __name__ == "__main__":
    unittest.main()
