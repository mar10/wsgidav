"""
server_cli
==========

:Author: Martin Wendt
:Copyright: Licensed under the MIT license, see LICENSE file in this package.

Standalone server that runs WsgiDAV.

These tasks are performed:

    - Set up the configuration from defaults, configuration file, and command line
      options.
    - Instantiate the WsgiDAVApp object (which is a WSGI application)
    - Start a WSGI server for this WsgiDAVApp object

Configuration is defined like this:

    1. Get the name of a configuration file from command line option
       ``--config-file=FILENAME`` (or short ``-cFILENAME``).
       If this option is omitted, we use ``wsgidav.yaml`` in the current
       directory.
    2. Set reasonable default settings.
    3. If configuration file exists: read and use it to overwrite defaults.
    4. If command line options are passed, use them to override settings:

       ``--host`` option overrides ``hostname`` setting.

       ``--port`` option overrides ``port`` setting.

       ``--root=FOLDER`` option creates a FilesystemProvider that publishes
       FOLDER on the '/' share.
"""

import argparse
import copy
import logging
import os
import platform
import sys
import webbrowser
from pprint import pformat
from threading import Timer

import yaml

from wsgidav import __version__, util
from wsgidav.default_conf import DEFAULT_CONFIG, DEFAULT_VERBOSE
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.wsgidav_app import WsgiDAVApp
from wsgidav.xml_tools import use_lxml

try:
    # Try pyjson5 first because it's faster than json5
    from pyjson5 import load as json_load
except ImportError:
    from json5 import load as json_load


__docformat__ = "reStructuredText"

#: Try this config files if no --config=... option is specified
DEFAULT_CONFIG_FILES = ("wsgidav.yaml", "wsgidav.json")

_logger = logging.getLogger("wsgidav")


def _get_common_info(config):
    """Calculate some common info."""
    # Support SSL
    ssl_certificate = util.fix_path(config.get("ssl_certificate"), config)
    ssl_private_key = util.fix_path(config.get("ssl_private_key"), config)
    ssl_certificate_chain = util.fix_path(config.get("ssl_certificate_chain"), config)
    ssl_adapter = config.get("ssl_adapter", "builtin")
    use_ssl = False
    if ssl_certificate and ssl_private_key:
        use_ssl = True
        # _logger.info("SSL / HTTPS enabled. Adapter: {}".format(ssl_adapter))
    elif ssl_certificate or ssl_private_key:
        raise RuntimeError(
            "Option 'ssl_certificate' and 'ssl_private_key' must be used together."
        )

    protocol = "https" if use_ssl else "http"
    url = f"{protocol}://{config['host']}:{config['port']}"
    info = {
        "use_ssl": use_ssl,
        "ssl_cert": ssl_certificate,
        "ssl_pk": ssl_private_key,
        "ssl_adapter": ssl_adapter,
        "ssl_chain": ssl_certificate_chain,
        "protocol": protocol,
        "url": url,
    }
    return info


class FullExpandedPath(argparse.Action):
    """Expand user- and relative-paths"""

    def __call__(self, parser, namespace, values, option_string=None):
        new_val = os.path.abspath(os.path.expanduser(values))
        setattr(namespace, self.dest, new_val)


def _init_command_line_options():
    """Parse command line options into a dictionary."""
    description = """\

Run a WEBDAV server to share file system folders.

Examples:

  Share filesystem folder '/temp' for anonymous access (no config file used):
    wsgidav --port=80 --host=0.0.0.0 --root=/temp --auth=anonymous

  Run using a specific configuration file:
    wsgidav --port=80 --host=0.0.0.0 --config=~/my_wsgidav.yaml

  If no config file is specified, the application will look for a file named
  'wsgidav.yaml' in the current directory.
  See
    http://wsgidav.readthedocs.io/en/latest/run-configure.html
  for some explanation of the configuration file format.
  """

    epilog = """\
Licensed under the MIT license.
See https://github.com/mar10/wsgidav for additional information.

"""

    parser = argparse.ArgumentParser(
        prog="wsgidav",
        description=description,
        epilog=epilog,
        allow_abbrev=False,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        # default=8080,
        help="port to serve on (default: 8080)",
    )
    parser.add_argument(
        "-H",  # '-h' conflicts with --help
        "--host",
        help=(
            "host to serve from (default: localhost). 'localhost' is only "
            "accessible from the local computer. Use 0.0.0.0 to make your "
            "application public"
        ),
    )
    parser.add_argument(
        "-r",
        "--root",
        dest="root_path",
        action=FullExpandedPath,
        help="path to a file system folder to publish for RW as share '/'.",
    )
    parser.add_argument(
        "--auth",
        choices=("anonymous", "nt", "pam-login"),
        help="quick configuration of a domain controller when no config file "
        "is used",
    )
    parser.add_argument(
        "--server",
        choices=SUPPORTED_SERVERS.keys(),
        # default="cheroot",
        help="type of pre-installed WSGI server to use (default: cheroot).",
    )
    parser.add_argument(
        "--ssl-adapter",
        choices=("builtin", "pyopenssl"),
        # default="builtin",
        help="used by 'cheroot' server if SSL certificates are configured "
        "(default: builtin).",
    )

    qv_group = parser.add_mutually_exclusive_group()
    qv_group.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=3,
        help="increment verbosity by one (default: %(default)s, range: 0..5)",
    )
    qv_group.add_argument(
        "-q", "--quiet", default=0, action="count", help="decrement verbosity by one"
    )

    qv_group = parser.add_mutually_exclusive_group()
    qv_group.add_argument(
        "-c",
        "--config",
        dest="config_file",
        action=FullExpandedPath,
        help=(
            f"configuration file (default: {DEFAULT_CONFIG_FILES} in current directory)"
        ),
    )

    qv_group.add_argument(
        "--no-config",
        action="store_true",
        help=f"do not try to load default {DEFAULT_CONFIG_FILES}",
    )

    parser.add_argument(
        "--browse",
        action="store_true",
        help="open browser on start",
    )

    parser.add_argument(
        "-V",
        "--version",
        action="store_true",
        help="print version info and exit (may be combined with --verbose)",
    )

    args = parser.parse_args()

    args.verbose -= args.quiet
    del args.quiet

    if args.root_path and not os.path.isdir(args.root_path):
        msg = f"{args.root_path} is not a directory"
        parser.error(msg)

    if args.version:
        if args.verbose >= 4:
            version_info = "WsgiDAV/{} {}/{}({} bit) {}".format(
                __version__,
                platform.python_implementation(),
                util.PYTHON_VERSION,
                "64" if sys.maxsize > 2**32 else "32",
                platform.platform(aliased=True),
            )
            version_info += f"\nPython from: {sys.executable}"
        else:
            version_info = f"{__version__}"
        print(version_info)
        sys.exit()

    if args.no_config:
        pass
        # ... else ignore default config files
    elif args.config_file is None:
        # If --config was omitted, use default (if it exists)
        for filename in DEFAULT_CONFIG_FILES:
            defPath = os.path.abspath(filename)
            if os.path.exists(defPath):
                if args.verbose >= 3:
                    print(f"Using default configuration file: {defPath}")
                args.config_file = defPath
                break
    else:
        # If --config was specified convert to absolute path and assert it exists
        args.config_file = os.path.abspath(args.config_file)
        if not os.path.isfile(args.config_file):
            parser.error(
                f"Could not find specified configuration file: {args.config_file}"
            )

    # Convert args object to dictionary
    cmdLineOpts = args.__dict__.copy()
    if args.verbose >= 5:
        print("Command line args:")
        for k, v in cmdLineOpts.items():
            print(f"    {k:>12}: {v}")
    return cmdLineOpts, parser


def _read_config_file(config_file, _verbose):
    """Read configuration file options into a dictionary."""

    config_file = os.path.abspath(config_file)

    if not os.path.exists(config_file):
        raise RuntimeError(f"Couldn't open configuration file {config_file!r}.")

    if config_file.endswith(".json"):
        with open(config_file, encoding="utf-8-sig") as fp:
            conf = json_load(fp)

    elif config_file.endswith(".yaml"):
        with open(config_file, encoding="utf-8-sig") as fp:
            conf = yaml.safe_load(fp)

    else:
        raise RuntimeError(
            f"Unsupported config file format (expected yaml or json): {config_file}"
        )

    conf["_config_file"] = config_file
    conf["_config_root"] = os.path.dirname(config_file)
    return conf


def _init_config():
    """Setup configuration dictionary from default, command line and configuration file."""
    cli_opts, parser = _init_command_line_options()
    cli_verbose = cli_opts["verbose"]

    # Set config defaults
    config = copy.deepcopy(DEFAULT_CONFIG)
    config["_config_file"] = None
    config["_config_root"] = os.getcwd()

    # Configuration file overrides defaults
    config_file = cli_opts.get("config_file")
    if config_file:
        file_opts = _read_config_file(config_file, cli_verbose)
        util.deep_update(config, file_opts)
        if cli_verbose != DEFAULT_VERBOSE and "verbose" in file_opts:
            if cli_verbose >= 2:
                print(
                    "Config file defines 'verbose: {}' but is overridden by command line: {}.".format(
                        file_opts["verbose"], cli_verbose
                    )
                )
            config["verbose"] = cli_verbose
    else:
        if cli_verbose >= 2:
            print("Running without configuration file.")

    # Command line overrides file
    if cli_opts.get("port"):
        config["port"] = cli_opts.get("port")
    if cli_opts.get("host"):
        config["host"] = cli_opts.get("host")
    if cli_opts.get("profile") is not None:
        config["profile"] = True
    if cli_opts.get("server") is not None:
        config["server"] = cli_opts.get("server")
    if cli_opts.get("ssl_adapter") is not None:
        config["ssl_adapter"] = cli_opts.get("ssl_adapter")

    # Command line overrides file only if -v or -q where passed:
    if cli_opts.get("verbose") != DEFAULT_VERBOSE:
        config["verbose"] = cli_opts.get("verbose")

    if cli_opts.get("root_path"):
        root_path = os.path.abspath(cli_opts.get("root_path"))
        config["provider_mapping"]["/"] = FilesystemProvider(
            root_path,
            fs_opts=config.get("fs_dav_provider"),
        )

    if config["verbose"] >= 5:
        # TODO: remove passwords from user_mapping
        config_cleaned = util.purge_passwords(config)
        print(
            "Configuration({}):\n{}".format(
                cli_opts["config_file"], pformat(config_cleaned)
            )
        )

    if not config["provider_mapping"]:
        parser.error("No DAV provider defined.")

    # Quick-configuration of DomainController
    auth = cli_opts.get("auth")
    auth_conf = util.get_dict_value(config, "http_authenticator", as_dict=True)
    if auth and auth_conf.get("domain_controller"):
        parser.error(
            "--auth option can only be used when no domain_controller is configured"
        )

    if auth == "anonymous":
        if config["simple_dc"]["user_mapping"]:
            parser.error(
                "--auth=anonymous can only be used when no user_mapping is configured"
            )
        auth_conf.update(
            {
                "domain_controller": "wsgidav.dc.simple_dc.SimpleDomainController",
                "accept_basic": True,
                "accept_digest": True,
                "default_to_digest": True,
            }
        )
        config["simple_dc"]["user_mapping"] = {"*": True}
    elif auth == "nt":
        if config.get("nt_dc"):
            parser.error(
                "--auth=nt can only be used when no nt_dc settings are configured"
            )
        auth_conf.update(
            {
                "domain_controller": "wsgidav.dc.nt_dc.NTDomainController",
                "accept_basic": True,
                "accept_digest": False,
                "default_to_digest": False,
            }
        )
        config["nt_dc"] = {}
    elif auth == "pam-login":
        if config.get("pam_dc"):
            parser.error(
                "--auth=pam-login can only be used when no pam_dc settings are configured"
            )
        auth_conf.update(
            {
                "domain_controller": "wsgidav.dc.pam_dc.PAMDomainController",
                "accept_basic": True,
                "accept_digest": False,
                "default_to_digest": False,
            }
        )
        config["pam_dc"] = {"service": "login"}
    # print(config)

    # if cli_opts.get("reload"):
    #     print("Installing paste.reloader.", file=sys.stderr)
    #     from paste import reloader  # @UnresolvedImport

    #     reloader.install()
    #     if config_file:
    #         # Add config file changes
    #         reloader.watch_file(config_file)
    #     # import pydevd
    #     # pydevd.settrace()

    if config["suppress_version_info"]:
        util.public_wsgidav_info = "WsgiDAV"
        util.public_python_info = f"Python/{sys.version_info[0]}"

    return cli_opts, config


def _run_cheroot(app, config, _server):
    """Run WsgiDAV using cheroot.server (https://cheroot.cherrypy.dev/)."""
    try:
        from cheroot import server, wsgi
    except ImportError:
        _logger.exception("Could not import Cheroot (https://cheroot.cherrypy.dev/).")
        _logger.error("Try `pip install cheroot`.")
        return False

    version = (
        f"{util.public_wsgidav_info} {wsgi.Server.version} {util.public_python_info}"
    )
    # wsgi.Server.version = version

    info = _get_common_info(config)

    # Support SSL
    if info["use_ssl"]:
        ssl_adapter = info["ssl_adapter"]
        ssl_adapter = server.get_ssl_adapter_class(ssl_adapter)
        wsgi.Server.ssl_adapter = ssl_adapter(
            info["ssl_cert"], info["ssl_pk"], info["ssl_chain"]
        )
        _logger.info(f"SSL / HTTPS enabled. Adapter: {ssl_adapter}")

    _logger.info(f"Running {version}")
    _logger.info(f"Serving on {info['url']} ...")

    server_args = {
        "bind_addr": (config["host"], config["port"]),
        "wsgi_app": app,
        "server_name": version,
        # File Explorer needs lot of threads (see issue #149):
        "numthreads": 50,  # TODO: still required?
    }
    # Override or add custom args
    custom_args = util.get_dict_value(config, "server_args", as_dict=True)
    server_args.update(custom_args)

    class PatchedServer(wsgi.Server):
        STARTUP_NOTIFICATION_DELAY = 0.5

        def serve(self, *args, **kwargs):
            _logger.error("wsgi.Server.serve")
            if startup_event and not startup_event.is_set():
                Timer(self.STARTUP_NOTIFICATION_DELAY, startup_event.set).start()
                _logger.error("wsgi.Server is ready")
            return super().serve(*args, **kwargs)

    # If the caller passed a startup event, monkey patch the server to set it
    # when the request handler loop is entered
    startup_event = config.get("startup_event")
    if startup_event:
        server = PatchedServer(**server_args)
    else:
        server = wsgi.Server(**server_args)

    try:
        server.start()
    except KeyboardInterrupt:
        _logger.warning("Caught Ctrl-C, shutting down...")
    finally:
        server.stop()

    return


def _run_ext_wsgiutils(app, config, _server):
    """Run WsgiDAV using ext_wsgiutils_server from the wsgidav package."""
    from wsgidav.server import ext_wsgiutils_server

    _logger.warning(
        "WARNING: This single threaded server (ext-wsgiutils) is not meant for production."
    )
    try:
        ext_wsgiutils_server.serve(config, app)
    except KeyboardInterrupt:
        _logger.warning("Caught Ctrl-C, shutting down...")
    return


def _run_gevent(app, config, server):
    """Run WsgiDAV using gevent if gevent (https://www.gevent.org).

    See
      https://github.com/gevent/gevent/blob/master/src/gevent/pywsgi.py#L1356
      https://github.com/gevent/gevent/blob/master/src/gevent/server.py#L38
    for more options.
    """
    try:
        import gevent
        import gevent.monkey
        from gevent.pywsgi import WSGIServer
    except ImportError:
        _logger.exception("Could not import gevent (http://www.gevent.org).")
        _logger.error("Try `pip install gevent`.")
        return False

    gevent.monkey.patch_all()

    info = _get_common_info(config)
    version = f"gevent/{gevent.__version__}"
    version = f"{util.public_wsgidav_info} {version} {util.public_python_info}"

    # Override or add custom args
    server_args = {
        "wsgi_app": app,
        "bind_addr": (config["host"], config["port"]),
    }
    custom_args = util.get_dict_value(config, "server_args", as_dict=True)
    server_args.update(custom_args)

    if info["use_ssl"]:
        dav_server = WSGIServer(
            server_args["bind_addr"],
            app,
            keyfile=info["ssl_pk"],
            certfile=info["ssl_cert"],
            ca_certs=info["ssl_chain"],
        )
    else:
        dav_server = WSGIServer(server_args["bind_addr"], app)

    # If the caller passed a startup event, monkey patch the server to set it
    # when the request handler loop is entered
    startup_event = config.get("startup_event")
    if startup_event:

        def _patched_start():
            dav_server.start_accepting = org_start  # undo the monkey patch
            org_start()
            _logger.info("gevent is ready")
            startup_event.set()

        org_start = dav_server.start_accepting
        dav_server.start_accepting = _patched_start

    _logger.info(f"Running {version}")
    _logger.info(f"Serving on {info['url']} ...")
    try:
        gevent.spawn(dav_server.serve_forever())
    except KeyboardInterrupt:
        _logger.warning("Caught Ctrl-C, shutting down...")
    return


def _run_gunicorn(app, config, server):
    """Run WsgiDAV using Gunicorn (https://gunicorn.org)."""
    try:
        import gunicorn.app.base
    except ImportError:
        _logger.exception("Could not import Gunicorn (https://gunicorn.org).")
        _logger.error("Try `pip install gunicorn` (UNIX only).")
        return False

    info = _get_common_info(config)

    class GunicornApplication(gunicorn.app.base.BaseApplication):
        def __init__(self, app, options=None):
            self.options = options or {}
            self.application = app
            super().__init__()

        def load_config(self):
            config = {
                key: value
                for key, value in self.options.items()
                if key in self.cfg.settings and value is not None
            }
            for key, value in config.items():
                self.cfg.set(key.lower(), value)

        def load(self):
            return self.application

    # See https://docs.gunicorn.org/en/latest/settings.html
    server_args = {
        "bind": "{}:{}".format(config["host"], config["port"]),
        "threads": 50,
        "timeout": 1200,
    }
    if info["use_ssl"]:
        server_args.update(
            {
                "keyfile": info["ssl_pk"],
                "certfile": info["ssl_cert"],
                "ca_certs": info["ssl_chain"],
                # "ssl_version": ssl_version
                # "cert_reqs": ssl_cert_reqs
                # "ciphers": ssl_ciphers
            }
        )
    # Override or add custom args
    custom_args = util.get_dict_value(config, "server_args", as_dict=True)
    server_args.update(custom_args)

    version = f"gunicorn/{gunicorn.__version__}"
    version = f"{util.public_wsgidav_info} {version} {util.public_python_info}"
    _logger.info(f"Running {version} ...")

    GunicornApplication(app, server_args).run()


def _run_paste(app, config, server):
    """Run WsgiDAV using paste.httpserver, if Paste is installed.

    See http://pythonpaste.org/modules/httpserver.html for more options
    """
    try:
        from paste import httpserver
    except ImportError:
        _logger.exception(
            "Could not import paste.httpserver (https://github.com/cdent/paste)."
        )
        _logger.error("Try `pip install paste`.")
        return False

    info = _get_common_info(config)

    version = httpserver.WSGIHandler.server_version
    version = f"{util.public_wsgidav_info} {version} {util.public_python_info}"

    # See http://pythonpaste.org/modules/httpserver.html for more options
    server = httpserver.serve(
        app,
        host=config["host"],
        port=config["port"],
        server_version=version,
        # This option enables handling of keep-alive and expect-100:
        protocol_version="HTTP/1.1",
        start_loop=False,
    )

    if config["verbose"] >= 5:
        __handle_one_request = server.RequestHandlerClass.handle_one_request

        def handle_one_request(self):
            __handle_one_request(self)
            if self.close_connection == 1:
                _logger.debug("HTTP Connection : close")
            else:
                _logger.debug("HTTP Connection : continue")

        server.RequestHandlerClass.handle_one_request = handle_one_request

    _logger.info(f"Running {version} ...")
    host, port = server.server_address
    if host == "0.0.0.0":
        _logger.info(f"Serving on 0.0.0.0:{port} view at http://127.0.0.1:{port}")
    else:
        _logger.info(f"Serving on {info['url']}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _logger.warning("Caught Ctrl-C, shutting down...")
    return


def _run_uvicorn(app, config, server):
    """Run WsgiDAV using Uvicorn (https://www.uvicorn.org)."""
    try:
        import uvicorn
    except ImportError:
        _logger.exception("Could not import Uvicorn (https://www.uvicorn.org).")
        _logger.error("Try `pip install uvicorn`.")
        return False

    info = _get_common_info(config)

    # See https://www.uvicorn.org/settings/
    server_args = {
        "interface": "wsgi",
        "host": config["host"],
        "port": config["port"],
        # TODO: see _run_cheroot()
    }
    if info["use_ssl"]:
        server_args.update(
            {
                "ssl_keyfile": info["ssl_pk"],
                "ssl_certfile": info["ssl_cert"],
                "ssl_ca_certs": info["ssl_chain"],
                # "ssl_keyfile_password": ssl_keyfile_password
                # "ssl_version": ssl_version
                # "ssl_cert_reqs": ssl_cert_reqs
                # "ssl_ciphers": ssl_ciphers
            }
        )
    # Override or add custom args
    custom_args = util.get_dict_value(config, "server_args", as_dict=True)
    server_args.update(custom_args)

    version = f"uvicorn/{uvicorn.__version__}"
    version = f"{util.public_wsgidav_info} {version} {util.public_python_info}"
    _logger.info(f"Running {version} ...")

    uvicorn.run(app, **server_args)


def _run_wsgiref(app, config, _server):
    """Run WsgiDAV using wsgiref.simple_server (https://docs.python.org/3/library/wsgiref.html)."""
    from wsgiref.simple_server import WSGIRequestHandler, make_server

    version = WSGIRequestHandler.server_version
    version = f"{util.public_wsgidav_info} {version}"  # {util.public_python_info}"
    _logger.info(f"Running {version} ...")

    _logger.warning(
        "WARNING: This single threaded server (wsgiref) is not meant for production."
    )
    WSGIRequestHandler.server_version = version
    httpd = make_server(config["host"], config["port"], app)
    # httpd.RequestHandlerClass.server_version = version
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        _logger.warning("Caught Ctrl-C, shutting down...")
    return


SUPPORTED_SERVERS = {
    "cheroot": _run_cheroot,
    "ext-wsgiutils": _run_ext_wsgiutils,
    "gevent": _run_gevent,
    "gunicorn": _run_gunicorn,
    "paste": _run_paste,
    "uvicorn": _run_uvicorn,
    "wsgiref": _run_wsgiref,
}


def run():
    cli_opts, config = _init_config()

    # util.init_logging(config) # now handled in constructor:
    config["logging"]["enable"] = True

    info = _get_common_info(config)

    app = WsgiDAVApp(config)

    server = config["server"]
    handler = SUPPORTED_SERVERS.get(server)
    if not handler:
        raise RuntimeError(
            "Unsupported server type {!r} (expected {!r})".format(
                server, "', '".join(SUPPORTED_SERVERS.keys())
            )
        )

    if not use_lxml and config["verbose"] >= 3:
        _logger.warning(
            "Could not import lxml: using xml instead (up to 10% slower). "
            "Consider `pip install lxml`(see https://pypi.python.org/pypi/lxml)."
        )

    if cli_opts["browse"]:
        BROWSE_DELAY = 2.0

        def _worker():
            url = info["url"]
            url = url.replace("0.0.0.0", "127.0.0.1")
            _logger.info(f"Starting browser on {url} ...")
            webbrowser.open(url)

        Timer(BROWSE_DELAY, _worker).start()

    handler(app, config, server)
    return


if __name__ == "__main__":
    # Just in case...
    from multiprocessing import freeze_support

    freeze_support()

    run()
