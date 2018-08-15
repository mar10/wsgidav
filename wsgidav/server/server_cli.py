# -*- coding: utf-8 -*-
"""
server_cli
==========

:Author: Martin Wendt, moogle(at)wwwendt.de
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
       If this option is omitted, we use ``wsgidav.conf`` in the current
       directory.
    2. Set reasonable default settings.
    3. If configuration file exists: read and use it to overwrite defaults.
    4. If command line options are passed, use them to override settings:

       ``--host`` option overrides ``hostname`` setting.

       ``--port`` option overrides ``port`` setting.

       ``--root=FOLDER`` option creates a FilesystemProvider that publishes
       FOLDER on the '/' share.
"""
from __future__ import print_function

import argparse
import copy
import io
import json
import logging
import os
import platform
import sys
import traceback
from inspect import isfunction
from pprint import pformat

import yaml
from jsmin import jsmin

from wsgidav import __version__, util
from wsgidav.default_conf import DEFAULT_CONFIG, DEFAULT_VERBOSE
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.wsgidav_app import WsgiDAVApp
from wsgidav.xml_tools import use_lxml

__docformat__ = "reStructuredText"

#: Try this config files if no --config=... option is specified
DEFAULT_CONFIG_FILES = ("wsgidav.yaml", "wsgidav.json", "wsgidav.conf")

_logger = logging.getLogger("wsgidav")


def _get_checked_path(path, must_exist=True, allow_none=True):
    """Convert path to absolute if not None."""
    if path in (None, ""):
        if allow_none:
            return None
        else:
            raise ValueError("Invalid path {!r}".format(path))
    path = os.path.abspath(path)
    if must_exist and not os.path.exists(path):
        raise ValueError("Invalid path {!r}".format(path))
    return path


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

  Share filesystem folder '/temp':
    wsgidav --port=80 --host=0.0.0.0 --root=/temp

  Run using a specific configuration file:
    wsgidav --port=80 --host=0.0.0.0 --config=~/wsgidav.yaml

  If no config file is specified, the application will look for a file named
  'wsgidav.conf' in the current directory.
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
        # allow_abbrev=False,  # Py3.5+
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-p",
        "--port",
        dest="port",
        type=int,
        # default=8080,
        help="port to serve on (default: 8080)",
    )
    parser.add_argument(
        "-H",
        "--host",  # '-h' conflicts with --help
        dest="host",
        # default="localhost",
        help=(
            "host to serve from (default: localhost). 'localhost' is only "
            "accessible from the local computer. Use 0.0.0.0 to make your "
            "application public"
        ),
    ),
    parser.add_argument(
        "-r",
        "--root",
        dest="root_path",
        action=FullExpandedPath,
        # type=arg_is_dir,
        help="path to a file system folder to publish as share '/'.",
    )
    parser.add_argument(
        "--server",
        choices=SUPPORTED_SERVERS.keys(),
        default="cheroot",
        help="type of pre-installed WSGI server to use (default: %(default)s).",
    )
    parser.add_argument(
        "--ssl-adapter",
        choices=("builtin", "pyopenssl"),
        default="builtin",
        help="used by 'cheroot' server if SSL certificates are configured "
        "(default: %(default)s.",
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

    parser.add_argument(
        "-c",
        "--config",
        dest="config_file",
        action=FullExpandedPath,
        help=(
            "configuration file (default: {} in current directory)".format(
                DEFAULT_CONFIG_FILES
            )
        ),
    )
    parser.add_argument(
        "--no-config",
        action="store_true",
        dest="no_config",
        help="do not try to load default {}".format(DEFAULT_CONFIG_FILES),
    )

    parser.add_argument(
        "-V",
        "--version",
        # action="version",
        # version=__version__,
        action="store_true",
        help="print version info and exit (may be combined with --verbose)",
    )

    args = parser.parse_args()

    # if args.quiet and args.verbose > 3:
    #     parser.error("-v and -q are mutually exclusive")

    args.verbose -= args.quiet
    del args.quiet

    if args.root_path and not os.path.isdir(args.root_path):
        msg = "{} is not a directory".format(args.root_path)
        raise parser.error(msg)

    if args.version:
        if args.verbose >= 4:
            msg = "WsgiDAV/{} Python/{} {}".format(
                __version__, util.PYTHON_VERSION, platform.platform(aliased=True)
            )
        else:
            msg = "{}".format(__version__)
        print(msg)
        sys.exit()

    if args.no_config:
        if args.config_file:
            parser.error("--config and --no-config are mutually exclusive")
        # ... else ignore default config files
    elif args.config_file is None:
        # If --config was omitted, use default (if it exists)
        for filename in DEFAULT_CONFIG_FILES:
            defPath = os.path.abspath(filename)
            if os.path.exists(defPath):
                if args.verbose >= 3:
                    print("Using default configuration file: {}".format(defPath))
                args.config_file = defPath
                break
    else:
        # If --config was specified convert to absolute path and assert it exists
        args.config_file = os.path.abspath(args.config_file)
        if not os.path.isfile(args.config_file):
            parser.error(
                "Could not find specified configuration file: {}".format(
                    args.config_file
                )
            )

    # Convert args object to dictionary
    cmdLineOpts = args.__dict__.copy()
    if args.verbose >= 5:
        print("Command line args:")
        for k, v in cmdLineOpts.items():
            print("    {:>12}: {}".format(k, v))
    return cmdLineOpts


def _read_config_file(config_file, verbose):
    """Read configuration file options into a dictionary."""

    if not os.path.exists(config_file):
        raise RuntimeError("Couldn't open configuration file '{}'.".format(config_file))

    if config_file.endswith(".json"):
        with io.open(config_file, mode="r", encoding="utf-8") as json_file:
            # Minify the JSON file to strip embedded comments
            minified = jsmin(json_file.read())
        return json.loads(minified)

    elif config_file.endswith(".yaml"):
        with io.open(config_file, mode="r", encoding="utf-8") as yaml_file:
            return yaml.safe_load(yaml_file)

    try:
        import imp

        conf = {}
        configmodule = imp.load_source("configuration_module", config_file)

        for k, v in vars(configmodule).items():
            if k.startswith("__"):
                continue
            elif isfunction(v):
                continue
            conf[k] = v
    except Exception:
        exc_type, exc_value = sys.exc_info()[:2]
        exc_info_list = traceback.format_exception_only(exc_type, exc_value)
        exc_text = "\n".join(exc_info_list)
        print(
            "Failed to read configuration file: "
            + config_file
            + "\nDue to "
            + exc_text,
            file=sys.stderr,
        )
        raise

    return conf


def _init_config():
    """Setup configuration dictionary from default, command line and configuration file."""
    cli_opts = _init_command_line_options()
    cli_verbose = cli_opts["verbose"]

    # Set config defaults
    # config = DEFAULT_CONFIG.copy()
    config = copy.deepcopy(DEFAULT_CONFIG)

    # Configuration file overrides defaults
    config_file = cli_opts.get("config_file")
    if config_file:
        file_opts = _read_config_file(config_file, cli_verbose)
        # config.update(file_opts)
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
    if cli_opts.get("verbose") is not None:
        config["verbose"] = cli_opts.get("verbose")
    if cli_opts.get("profile") is not None:
        config["profile"] = True
    if cli_opts.get("server") is not None:
        config["server"] = cli_opts.get("server")
    if cli_opts.get("ssl_adapter") is not None:
        config["ssl_adapter"] = cli_opts.get("ssl_adapter")

    if cli_opts.get("root_path"):
        root_path = os.path.abspath(cli_opts.get("root_path"))
        config["provider_mapping"]["/"] = FilesystemProvider(root_path)

    if config["verbose"] >= 5:
        # TODO: remove passwords from user_mapping
        # config_cleaned = copy.deepcopy(config)
        print("Configuration({}):\n{}".format(cli_opts["config_file"], pformat(config)))

    if not config["provider_mapping"]:
        print("ERROR: No DAV provider defined. Try --help option.", file=sys.stderr)
        sys.exit(-1)

    if cli_opts.get("reload"):
        print("Installing paste.reloader.", file=sys.stderr)
        from paste import reloader  # @UnresolvedImport

        reloader.install()
        if config_file:
            # Add config file changes
            reloader.watch_file(config_file)
        # import pydevd
        # pydevd.settrace()

    return config


def _run_paste(app, config, mode):
    """Run WsgiDAV using paste.httpserver, if Paste is installed.

    See http://pythonpaste.org/modules/httpserver.html for more options
    """
    from paste import httpserver

    version = "WsgiDAV/{} {} Python {}".format(
        __version__, httpserver.WSGIHandler.server_version, util.PYTHON_VERSION
    )
    _logger.info("Running {}...".format(version))

    # See http://pythonpaste.org/modules/httpserver.html for more options
    server = httpserver.serve(
        app,
        host=config["host"],
        port=config["port"],
        server_version=version,
        # This option enables handling of keep-alive
        # and expect-100:
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

        # __handle = server.RequestHandlerClass.handle

        # def handle(self):
        #     _logger.debug("open HTTP connection")
        #     __handle(self)

        server.RequestHandlerClass.handle_one_request = handle_one_request

    host, port = server.server_address
    if host == "0.0.0.0":
        _logger.info(
            "Serving on 0.0.0.0:{} view at {}://127.0.0.1:{}".format(port, "http", port)
        )
    else:
        _logger.info("Serving on {}://{}:{}".format("http", host, port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _logger.warn("Caught Ctrl-C, shutting down...")
    return


def _run_gevent(app, config, mode):
    """Run WsgiDAV using gevent if gevent is installed.

    See
      https://github.com/gevent/gevent/blob/master/src/gevent/pywsgi.py#L1356
      https://github.com/gevent/gevent/blob/master/src/gevent/server.py#L38
     for more options
    """
    import gevent
    import gevent.monkey

    gevent.monkey.patch_all()
    from gevent.pywsgi import WSGIServer

    server_args = {
        "bind_addr": (config["host"], config["port"]),
        "wsgi_app": app,
        # TODO: SSL support
        "keyfile": None,
        "certfile": None,
    }
    protocol = "http"
    # Override or add custom args
    server_args.update(config.get("server_args", {}))

    dav_server = WSGIServer(server_args["bind_addr"], app)
    _logger.info("Running {}".format(dav_server))
    _logger.info(
        "Serving on {}://{}:{} ...".format(protocol, config["host"], config["port"])
    )
    try:
        gevent.spawn(dav_server.serve_forever())
    except KeyboardInterrupt:
        _logger.warn("Caught Ctrl-C, shutting down...")
    return


def _run__cherrypy(app, config, mode):
    """Run WsgiDAV using cherrypy.wsgiserver if CherryPy is installed."""
    assert mode == "cherrypy-wsgiserver"

    try:
        from cherrypy import wsgiserver
        from cherrypy.wsgiserver.ssl_builtin import BuiltinSSLAdapter

        _logger.warn("WARNING: cherrypy.wsgiserver is deprecated.")
        _logger.warn(
            "         Starting with CherryPy 9.0 the functionality from cherrypy.wsgiserver"
        )
        _logger.warn("         was moved to the cheroot project.")
        _logger.warn("         Consider using --server=cheroot.")
    except ImportError:
        _logger.error("*" * 78)
        _logger.error("ERROR: Could not import cherrypy.wsgiserver.")
        _logger.error(
            "Try `pip install cherrypy` or specify another server using the --server option."
        )
        _logger.error("Note that starting with CherryPy 9.0, the server was moved to")
        _logger.error(
            "the cheroot project, so it is recommended to use `-server=cheroot`"
        )
        _logger.error("and run `pip install cheroot` instead.")
        _logger.error("*" * 78)
        raise

    server_name = "WsgiDAV/{} {} Python/{}".format(
        __version__, wsgiserver.CherryPyWSGIServer.version, util.PYTHON_VERSION
    )
    wsgiserver.CherryPyWSGIServer.version = server_name

    # Support SSL
    ssl_certificate = _get_checked_path(config.get("ssl_certificate"))
    ssl_private_key = _get_checked_path(config.get("ssl_private_key"))
    ssl_certificate_chain = _get_checked_path(config.get("ssl_certificate_chain"))
    protocol = "http"
    if ssl_certificate:
        assert ssl_private_key
        wsgiserver.CherryPyWSGIServer.ssl_adapter = BuiltinSSLAdapter(
            ssl_certificate, ssl_private_key, ssl_certificate_chain
        )
        protocol = "https"
        _logger.info("SSL / HTTPS enabled.")

    _logger.info("Running {}".format(server_name))
    _logger.info(
        "Serving on {}://{}:{} ...".format(protocol, config["host"], config["port"])
    )

    server_args = {
        "bind_addr": (config["host"], config["port"]),
        "wsgi_app": app,
        "server_name": server_name,
    }
    # Override or add custom args
    server_args.update(config.get("server_args", {}))

    server = wsgiserver.CherryPyWSGIServer(**server_args)

    # If the caller passed a startup event, monkey patch the server to set it
    # when the request handler loop is entered
    startup_event = config.get("startup_event")
    if startup_event:

        def _patched_tick():
            server.tick = org_tick  # undo the monkey patch
            org_tick()
            _logger.info("CherryPyWSGIServer is ready")
            startup_event.set()

        org_tick = server.tick
        server.tick = _patched_tick

    try:
        server.start()
    except KeyboardInterrupt:
        _logger.warn("Caught Ctrl-C, shutting down...")
    finally:
        server.stop()
    return


def _run_cheroot(app, config, mode):
    """Run WsgiDAV using cheroot.server if Cheroot is installed."""
    assert mode == "cheroot"
    try:
        from cheroot import server, wsgi
    #         from cheroot.ssl.builtin import BuiltinSSLAdapter
    #         import cheroot.ssl.pyopenssl
    except ImportError:
        _logger.error("*" * 78)
        _logger.error("ERROR: Could not import Cheroot.")
        _logger.error(
            "Try `pip install cheroot` or specify another server using the --server option."
        )
        _logger.error("*" * 78)
        raise

    server_name = "WsgiDAV/{} {} Python/{}".format(
        __version__, wsgi.Server.version, util.PYTHON_VERSION
    )
    wsgi.Server.version = server_name

    # Support SSL
    ssl_certificate = _get_checked_path(config.get("ssl_certificate"))
    ssl_private_key = _get_checked_path(config.get("ssl_private_key"))
    ssl_certificate_chain = _get_checked_path(config.get("ssl_certificate_chain"))
    ssl_adapter = config.get("ssl_adapter", "builtin")
    protocol = "http"
    if ssl_certificate and ssl_private_key:
        ssl_adapter = server.get_ssl_adapter_class(ssl_adapter)
        wsgi.Server.ssl_adapter = ssl_adapter(
            ssl_certificate, ssl_private_key, ssl_certificate_chain
        )
        protocol = "https"
        _logger.info("SSL / HTTPS enabled. Adapter: {}".format(ssl_adapter))
    elif ssl_certificate or ssl_private_key:
        raise RuntimeError(
            "Option 'ssl_certificate' and 'ssl_private_key' must be used together."
        )
    #     elif ssl_adapter:
    #         print("WARNING: Ignored option 'ssl_adapter' (requires 'ssl_certificate').")

    _logger.info("Running {}".format(server_name))
    _logger.info(
        "Serving on {}://{}:{} ...".format(protocol, config["host"], config["port"])
    )

    server_args = {
        "bind_addr": (config["host"], config["port"]),
        "wsgi_app": app,
        "server_name": server_name,
    }
    # Override or add custom args
    server_args.update(config.get("server_args", {}))

    server = wsgi.Server(**server_args)

    # If the caller passed a startup event, monkey patch the server to set it
    # when the request handler loop is entered
    startup_event = config.get("startup_event")
    if startup_event:

        def _patched_tick():
            server.tick = org_tick  # undo the monkey patch
            _logger.info("wsgi.Server is ready")
            startup_event.set()
            org_tick()

        org_tick = server.tick
        server.tick = _patched_tick

    try:
        server.start()
    except KeyboardInterrupt:
        _logger.warn("Caught Ctrl-C, shutting down...")
    finally:
        server.stop()

    return


def _run_flup(app, config, mode):
    """Run WsgiDAV using flup.server.fcgi if Flup is installed."""
    # http://trac.saddi.com/flup/wiki/FlupServers
    if mode == "flup-fcgi":
        from flup.server.fcgi import WSGIServer, __version__ as flupver
    elif mode == "flup-fcgi-fork":
        from flup.server.fcgi_fork import WSGIServer, __version__ as flupver
    else:
        raise ValueError

    _logger.info(
        "Running WsgiDAV/{} {}/{}...".format(
            __version__, WSGIServer.__module__, flupver
        )
    )
    server = WSGIServer(
        app,
        bindAddress=(config["host"], config["port"]),
        # debug=True,
    )
    try:
        server.run()
    except KeyboardInterrupt:
        _logger.warn("Caught Ctrl-C, shutting down...")
    return


def _run_wsgiref(app, config, mode):
    """Run WsgiDAV using wsgiref.simple_server, on Python 2.5+."""
    # http://www.python.org/doc/2.5.2/lib/module-wsgiref.html
    from wsgiref.simple_server import make_server, software_version

    version = "WsgiDAV/{} {}".format(__version__, software_version)
    _logger.info("Running {}...".format(version))
    _logger.warn(
        "WARNING: This single threaded server (wsgiref) is not meant for production."
    )
    httpd = make_server(config["host"], config["port"], app)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        _logger.warn("Caught Ctrl-C, shutting down...")
    return


def _run_ext_wsgiutils(app, config, mode):
    """Run WsgiDAV using ext_wsgiutils_server from the wsgidav package."""
    from wsgidav.server import ext_wsgiutils_server

    _logger.info(
        "Running WsgiDAV {} on wsgidav.ext_wsgiutils_server...".format(__version__)
    )
    _logger.warn(
        "WARNING: This single threaded server (ext-wsgiutils) is not meant for production."
    )
    try:
        ext_wsgiutils_server.serve(config, app)
    except KeyboardInterrupt:
        _logger.warn("Caught Ctrl-C, shutting down...")
    return


SUPPORTED_SERVERS = {
    "paste": _run_paste,
    "gevent": _run_gevent,
    "cheroot": _run_cheroot,
    "cherrypy": _run__cherrypy,
    "ext-wsgiutils": _run_ext_wsgiutils,
    "flup-fcgi": _run_flup,
    "flup-fcgi_fork": _run_flup,
    "wsgiref": _run_wsgiref,
}


def run():
    config = _init_config()

    util.init_logging(config)

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
        _logger.warn(
            "Could not import lxml: using xml instead (up to 10% slower). "
            "Consider `pip install lxml`(see https://pypi.python.org/pypi/lxml)."
        )

    handler(app, config, server)


if __name__ == "__main__":
    # Just in case...
    from multiprocessing import freeze_support

    freeze_support()

    run()
