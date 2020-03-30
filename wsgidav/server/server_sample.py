# -*- coding: utf-8 -*-
# (c) 2009-2020 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Simple example how to a run WsgiDAV in a 3rd-party WSGI server.
"""
from __future__ import print_function
from tempfile import gettempdir
from wsgidav import __version__
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.wsgidav_app import WsgiDAVApp


__docformat__ = "reStructuredText"


def main():
    root_path = gettempdir()
    provider = FilesystemProvider(root_path)

    config = {
        "provider_mapping": {"/": provider},
        "http_authenticator": {
            "domain_controller": None  # None: dc.simple_dc.SimpleDomainController(user_mapping)
        },
        "simple_dc": {"user_mapping": {"*": True}},  # anonymous access
        "verbose": 1,
        "enable_loggers": [],
        "property_manager": True,  # True: use property_manager.PropertyManager
        "lock_manager": True,  # True: use lock_manager.LockManager
    }
    app = WsgiDAVApp(config)

    # For an example, use CherryPy
    from cherrypy.wsgiserver import CherryPyWSGIServer

    server = CherryPyWSGIServer(
        bind_addr=(config["host"], config["port"]),
        wsgi_app=app,
        server_name="WsgiDAV/{} {}".format(__version__, CherryPyWSGIServer.version),
    )

    try:
        server.start()
    except KeyboardInterrupt:
        print("Caught Ctrl-C, shutting down...")
    finally:
        server.stop()

    # For an example, use paste.httpserver
    # (See http://pythonpaste.org/modules/httpserver.html for more options)


#    from paste import httpserver
#    httpserver.serve(app,
#                     host="localhost",
#                     port=8080,
#                     server_version="WsgiDAV/{}".format(__version__),
#                     )


if __name__ == "__main__":
    main()
