# -*- coding: iso-8859-1 -*-
# (c) 2009-2016 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
    Test helpers.

Example:
    with WsgiDavTestServer(opts):
        ... test methods
"""
from __future__ import print_function

import os
import sys
import time
from multiprocessing import Process
from tempfile import gettempdir

from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.wsgidav_app import DEFAULT_CONFIG, WsgiDAVApp


# ========================================================================
# Timing
# ========================================================================

class Timing(object):
    """Print timing"""

    def __init__(self, name, count=None, fmt=None, count2=None, fmt2=None, stream=None):
        self.name = name
        self.count = count
        self.fmt = fmt
        self.count2 = count2
        self.fmt2 = fmt2
        self.stream = stream or sys.stdout

    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, type, value, traceback):
        elap = time.time() - self.start
        msg = ["Timing {:<20} took {:>6.3f} sec".format(repr(self.name), elap)]
        if self.count:
            fmt = self.fmt or "{:0,.1f} bytes/sec"
            msg.append(fmt.format(float(self.count) / elap))
        if self.count2:
            fmt = self.fmt2 or "{:0,.1f} bytes/sec"
            msg.append(fmt.format(float(self.count2) / elap))
        print(", ".join(msg))


# ========================================================================
# Timing
# ========================================================================

def run_wsgidav_server(with_auth, with_ssl):
    """Start blocking WsgiDAV server (called as a separate process)."""
    package_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), ".."))

    share_path = os.path.join(gettempdir(), "wsgidav-test")
    if not os.path.exists(share_path):
        os.mkdir(share_path)

    provider = FilesystemProvider(share_path)

    config = DEFAULT_CONFIG.copy()
    config.update({
        "host": "127.0.0.1",
        "port": 8080,
        "provider_mapping": {"/": provider},
        # None: domain_controller.WsgiDAVDomainController(user_mapping)
        "domaincontroller": None,
        "user_mapping": {},
        "verbose": 0,
        "enable_loggers": [],
        "propsmanager": True,      # None: no property manager
        "locksmanager": True,      # True: use lock_manager.LockManager
        # None: domain_controller.WsgiDAVDomainController(user_mapping)
        "domaincontroller": None,
    })

    if with_auth:
        config.update({
            "user_mapping": {"/": {"tester": {"password": "secret",
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
            "ssl_certificate": os.path.join(package_path, "wsgidav/server/sample_bogo_server.crt"),
            "ssl_private_key": os.path.join(package_path, "wsgidav/server/sample_bogo_server.key"),
            "ssl_certificate_chain": None,
            # "acceptdigest": True,
            # "defaultdigest": True,
        })

    app = WsgiDAVApp(config)

    # from wsgidav.server.run_server import _runBuiltIn
    # _runBuiltIn(app, config, None)
    from wsgidav.server.run_server import _runCherryPy
    _runCherryPy(app, config, "cherrypy-bundled")
    # blocking...


# ========================================================================
# WsgiDavTestServer
# ========================================================================

class WsgiDavTestServer(object):
    """Run wsgidav in a separate process."""

    def __init__(self, config=None, with_auth=False, with_ssl=False, profile=False):
        self.config = config
        self.with_auth = with_auth
        self.with_ssl = with_ssl
        self.start_delay = 1
        self.proc = None
        assert not profile, "Not yet implemented"

    def __enter__(self):
        kwargs = {
            "with_auth": self.with_auth,
            "with_ssl": self.with_ssl,
        }
        print("Starting WsgiDavTestServer...")
        self.proc = Process(target=run_wsgidav_server, kwargs=kwargs)
        self.proc.daemon = True
        self.proc.start()
        # print("Starting WsgiDavTestServer... waiting...")
        time.sleep(self.start_delay)
        # print("Starting WsgiDavTestServer... waiting... done.")
        return self

    def __exit__(self, type, value, traceback):
        # print("Stopping WsgiDAVAppavTestServer...")
        self.proc.terminate()
        self.proc.join()
        print("Stopping WsgiDavTestServer... done.")
