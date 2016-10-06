# (c) 2009-2016 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Simple example how to a run WsgiDAV in a 3rd-party WSGI server.
"""
from tempfile import gettempdir
from wsgidav import __version__
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.wsgidav_app import DEFAULT_CONFIG, WsgiDAVApp

__docformat__ = "reStructuredText"

def main():
    rootpath = gettempdir()
    provider = FilesystemProvider(rootpath)

    config = DEFAULT_CONFIG.copy()
    config.update({
        "provider_mapping": {"/": provider},
        "user_mapping": {},
        "verbose": 1,
        "enable_loggers": [],
        "propsmanager": True,      # True: use property_manager.PropertyManager
        "locksmanager": True,      # True: use lock_manager.LockManager
        "domaincontroller": None,  # None: domain_controller.WsgiDAVDomainController(user_mapping)
        })
    app = WsgiDAVApp(config)

    # For an example, use CherryPy
    from cherrypy.wsgiserver import CherryPyWSGIServer

    server = CherryPyWSGIServer(
        bind_addr=(config["host"], config["port"]),
        wsgi_app=app,
        server_name="WsgiDAV/%s %s" % (__version__, CherryPyWSGIServer.version),
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
#                     server_version="WsgiDAV/%s" % __version__,
#                     )


if __name__ == "__main__":
    main()
