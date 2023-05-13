# -*- coding: utf-8 -*-
# (c) 2009-2023 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Simple example how to a run WsgiDAV in a 3rd-party WSGI server.
"""
from wsgidav import __version__, util
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.wsgidav_app import WsgiDAVApp

__docformat__ = "reStructuredText"


def main():
    root_path = "."
    provider = FilesystemProvider(root_path, readonly=False, fs_opts={})

    config = {
        "host": "127.0.0.1",
        "port": 8080,
        "provider_mapping": {"/": provider},
        "http_authenticator": {
            "domain_controller": None  # None: dc.simple_dc.SimpleDomainController(user_mapping)
        },
        "simple_dc": {"user_mapping": {"*": True}},  # anonymous access
        "verbose": 1,
        "logging": {
            "enable_loggers": [],
        },
        "property_manager": True,  # True: use property_manager.PropertyManager
        "lock_storage": True,  # True: use LockManager(lock_storage.LockStorageDict)
    }
    app = WsgiDAVApp(config)

    # For an example, use cheroot:

    from cheroot import wsgi

    version = (
        f"WsgiDAV/{__version__} {wsgi.Server.version} Python/{util.PYTHON_VERSION}"
    )

    server = wsgi.Server(
        bind_addr=(config["host"], config["port"]),
        wsgi_app=app,
        server_name=version,
        # "numthreads": 50,
    )

    try:
        server.start()
    except KeyboardInterrupt:
        print("Caught Ctrl-C, shutting down...")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
