# (c) 2009-2024 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Simple example how to a run WsgiDAV in a 3rd-party WSGI server.
"""

from cheroot import wsgi

from wsgidav import util
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.wsgidav_app import WsgiDAVApp


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
        "verbose": 4,
        "logging": {
            "enable": True,
            "enable_loggers": [],
        },
        "property_manager": True,  # True: use property_manager.PropertyManager
        "lock_storage": True,  # True: use LockManager(lock_storage.LockStorageDict)
    }
    app = WsgiDAVApp(config)

    # For an example, use cheroot:
    version = (
        f"{util.public_wsgidav_info} {wsgi.Server.version} {util.public_python_info}"
    )

    server = wsgi.Server(
        bind_addr=(config["host"], config["port"]),
        wsgi_app=app,
        server_name=version,
        # "numthreads": 50,
    )

    app.logger.info(f"Running {version}")
    app.logger.info(f"Serving on http://{config['host']}:{config['port']}/ ...")
    try:
        server.start()
    except KeyboardInterrupt:
        app.logger.info("Received Ctrl-C: stopping...")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
