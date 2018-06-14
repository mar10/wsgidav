# -*- coding: iso-8859-1 -*-
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
import io
import json
import logging
import os
import sys
import traceback
from inspect import isfunction
from pprint import pformat

from jsmin import jsmin
import yaml

from wsgidav import __version__, util
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.wsgidav_app import DEFAULT_CONFIG, WsgiDAVApp
from wsgidav.xml_tools import useLxml

__docformat__ = "reStructuredText"

#: Try this config files if no --config_file option is specified
DEFAULT_CONFIG_FILES = ("wsgidav.yaml", "wsgidav.json", "wsgidav.conf")

_logger = logging.getLogger("wsgidav")


def _get_checked_path(path, mustExist=True, allowNone=True):
    """Convert path to absolute if not None."""
    if path in (None, ""):
        if allowNone:
            return None
        else:
            raise ValueError("Invalid path {!r}".format(path))
    path = os.path.abspath(path)
    if mustExist and not os.path.exists(path):
        raise ValueError("Invalid path {!r}".format(path))
    return path


class FullExpandedPath(argparse.Action):
    """Expand user- and relative-paths"""
    def __call__(self, parser, namespace, values, option_string=None):
        new_val = os.path.abspath(os.path.expanduser(values))
        setattr(namespace, self.dest, new_val)


def _initCommandLineOptions():
    """Parse command line options into a dictionary."""

    description = """\

Run a WEBDAV server to share file system folders.

Examples:

  Share filesystem folder '/temp':
    wsgidav --port=80 --host=0.0.0.0 --root=/temp

  Run using a specific configuration file:
    wsgidav --port=80 --host=0.0.0.0 --config=~/wsgidav.conf

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

    parser = argparse.ArgumentParser(prog="wsgidav",
                                     description=description,
                                     epilog=epilog,
                                     # allow_abbrev=False,  # Py3.5+
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     )
    parser.add_argument("-p", "--port",
                        dest="port",
                        type=int,
                        # default=8080,
                        help="port to serve on (default: 8080)")
    parser.add_argument("-H", "--host",  # '-h' conflicts with --help
                        dest="host",
                        # default="localhost",
                        help=("host to serve from (default: localhost). 'localhost' is only "
                              "accessible from the local computer. Use 0.0.0.0 to make your "
                              "application public")),
    parser.add_argument("-r", "--root",
                        dest="root_path",
                        action=FullExpandedPath,
                        # type=arg_is_dir,
                        help="path to a file system folder to publish as share '/'.")
    parser.add_argument("--server",
                        choices=("cheroot", "cherrypy-wsgiserver", "ext-wsgiutils", "flup-fcgi",
                                 "flup-fcgi-fork", "paste", "wsgiref"),
                        default="cheroot",
                        help="type of pre-installed WSGI server to use (default: %(default)s).")
    parser.add_argument("--ssl-adapter",
                        choices=("builtin", "pyopenssl"),
                        default="builtin",
                        help="used by 'cheroot' server if SSL certificates are configured "
                             "(default: %(default)s.")

    parser.add_argument("-v", "--verbose", action="count", default=3,
                        help="increment verbosity by one (default: %(default)s, range: 0..5)")
    parser.add_argument("-q", "--quiet", default=0,
                        action="count",
                        help="decrement verbosity by one")

    parser.add_argument("-c", "--config",
                        dest="config_file",
                        action=FullExpandedPath,
                        help=("configuration file (default: {} in current directory)"
                              .format(DEFAULT_CONFIG_FILES)))
    parser.add_argument("--no-config",
                        action="store_true", dest="no_config",
                        help="do not try to load default {}".format(DEFAULT_CONFIG_FILES))

    parser.add_argument("-V", "--version",
                        # action="version",
                        # version=__version__,
                        action="store_true",
                        help="print version info and exit (may be combined with --verbose)",
                        )

    args = parser.parse_args()

    if args.quiet and args.verbose > 3:
        parser.error("-v and -q are mutually exclusive")

    args.verbose -= args.quiet
    del args.quiet

#    if args.verbose >= 4:
#        print("Verbosity: {}".format(args.verbose))

    if args.root_path and not os.path.isdir(args.root_path):
        msg = "{} is not a directory".format(args.root_path)
        raise parser.error(msg)

    if args.version:
        if args.verbose >= 4:
            import platform
            msg = "WsgiDAV/{} Python/{} {}".format(
                    __version__, util.PYTHON_VERSION, platform.platform())
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
            parser.error("Could not find specified configuration file: {}"
                         .format(args.config_file))

    # Convert args object to dictionary
    cmdLineOpts = args.__dict__.copy()
    if args.verbose >= 4:
        print("Command line args:")
        for k, v in cmdLineOpts.items():
            print("    {:>12}: {}".format(k, v))
    return cmdLineOpts


def _readConfigFile(config_file, verbose):
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
        # if verbose >= 1:
        #    traceback.print_exc()
        exceptioninfo = traceback.format_exception_only(sys.exc_type, sys.exc_value)
        exceptiontext = ""
        for einfo in exceptioninfo:
            exceptiontext += einfo + "\n"
#        raise RuntimeError("Failed to read configuration file: " + config_file + "\nDue to "
#            + exceptiontext)
        print("Failed to read configuration file: " + config_file +
              "\nDue to " + exceptiontext, file=sys.stderr)
        raise

    return conf


def _initConfig():
    """Setup configuration dictionary from default, command line and configuration file."""
    cmdLineOpts = _initCommandLineOptions()

    # Set config defaults
    config = DEFAULT_CONFIG.copy()
    if cmdLineOpts["verbose"] is None:
        temp_verbose = config["verbose"]
    else:
        temp_verbose = cmdLineOpts["verbose"]

    # print "verbose #1: ", temp_verbose

    # Configuration file overrides defaults
    config_file = cmdLineOpts.get("config_file")
    if config_file:
        fileConf = _readConfigFile(config_file, temp_verbose)
        config.update(fileConf)
    else:
        if temp_verbose >= 2:
            print("Running without configuration file.")

    # print "verbose #2: ", config.get("verbose")

    # Command line overrides file
    if cmdLineOpts.get("port"):
        config["port"] = cmdLineOpts.get("port")
    if cmdLineOpts.get("host"):
        config["host"] = cmdLineOpts.get("host")
    if cmdLineOpts.get("verbose") is not None:
        config["verbose"] = cmdLineOpts.get("verbose")
    if cmdLineOpts.get("profile") is not None:
        config["profile"] = True
    if cmdLineOpts.get("server") is not None:
        config["server"] = cmdLineOpts.get("server")
    if cmdLineOpts.get("ssl_adapter") is not None:
        config["ssl_adapter"] = cmdLineOpts.get("ssl_adapter")

    if cmdLineOpts.get("root_path"):
        root_path = os.path.abspath(cmdLineOpts.get("root_path"))
        config["provider_mapping"]["/"] = FilesystemProvider(root_path)

    if config["verbose"] >= 4:
        print("Configuration({}):\n{}"
              .format(cmdLineOpts["config_file"], pformat(config)))

    # if not useLxml and config["verbose"] >= 1:
    #     print("WARNING: Could not import lxml: using xml instead (slower). Consider installing"
    #         "lxml from http://codespeak.net/lxml/.")

    # print "verbose #3: ", config.get("verbose")

    if not config["provider_mapping"]:
        print("ERROR: No DAV provider defined. Try --help option.", file=sys.stderr)
        sys.exit(-1)
#        raise RuntimeWarning("At least one DAV provider must be specified by a --root option,"
#             or in a configuration file.")

    if cmdLineOpts.get("reload"):
        print("Installing paste.reloader.", file=sys.stderr)
        from paste import reloader  # @UnresolvedImport
        reloader.install()
        if config_file:
            # Add config file changes
            reloader.watch_file(config_file)
#        import pydevd
#        pydevd.settrace()

    return config


def _runPaste(app, config, mode):
    """Run WsgiDAV using paste.httpserver, if Paste is installed.

    See http://pythonpaste.org/modules/httpserver.html for more options
    """
    from paste import httpserver
    version = "WsgiDAV/{} {} Python {}".format(
        __version__, httpserver.WSGIHandler.server_version, util.PYTHON_VERSION)
    _logger.info("Running {}...".format(version))

    # See http://pythonpaste.org/modules/httpserver.html for more options
    server = httpserver.serve(app,
                              host=config["host"],
                              port=config["port"],
                              server_version=version,
                              # This option enables handling of keep-alive
                              # and expect-100:
                              protocol_version="HTTP/1.1",
                              start_loop=False
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

        __handle = server.RequestHandlerClass.handle

        def handle(self):
            _logger.debug("open HTTP connection")
            __handle(self)

        server.RequestHandlerClass.handle_one_request = handle_one_request

    host, port = server.server_address
    if host == "0.0.0.0":
        _logger.info("Serving on 0.0.0.0:{} view at {}://127.0.0.1:{}".format(port, "http", port))
    else:
        _logger.info("Serving on {}://{}:{}".format("http", host, port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        _logger.warn("Caught Ctrl-C, shutting down...")
    return


def _runCherryPy(app, config, mode):
    """Run WsgiDAV using cherrypy.wsgiserver if CherryPy is installed."""
    assert mode == "cherrypy-wsgiserver"

    try:
        from cherrypy import wsgiserver
        from cherrypy.wsgiserver.ssl_builtin import BuiltinSSLAdapter

        _logger.warn("WARNING: cherrypy.wsgiserver is deprecated.")
        _logger.warn(
                "         Starting with CherryPy 9.0 the functionality from cherrypy.wsgiserver")
        _logger.warn("         was moved to the cheroot project.")
        _logger.warn("         Consider using --server=cheroot.")
    except ImportError:
        _logger.error("*" * 78)
        _logger.error("ERROR: Could not import cherrypy.wsgiserver.")
        _logger.error(
                "Try `pip install cherrypy` or specify another server using the --server option.")
        _logger.error("Note that starting with CherryPy 9.0, the server was moved to")
        _logger.error("the cheroot project, so it is recommended to use `-server=cheroot`")
        _logger.error("and run `pip install cheroot` instead.")
        _logger.error("*" * 78)
        raise

    server_name = "WsgiDAV/{} {} Python/{}".format(
        __version__,
        wsgiserver.CherryPyWSGIServer.version,
        util.PYTHON_VERSION)
    wsgiserver.CherryPyWSGIServer.version = server_name

    # Support SSL
    ssl_certificate = _get_checked_path(config.get("ssl_certificate"))
    ssl_private_key = _get_checked_path(config.get("ssl_private_key"))
    ssl_certificate_chain = _get_checked_path(config.get("ssl_certificate_chain"))
    protocol = "http"
    if ssl_certificate:
        assert ssl_private_key
        wsgiserver.CherryPyWSGIServer.ssl_adapter = BuiltinSSLAdapter(
            ssl_certificate, ssl_private_key, ssl_certificate_chain)
        protocol = "https"
        _logger.info("SSL / HTTPS enabled.")

    _logger.info("Running {}".format(server_name))
    _logger.info("Serving on {}://{}:{} ...".format(protocol, config["host"], config["port"]))

    server_args = {"bind_addr": (config["host"], config["port"]),
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


def _runCheroot(app, config, mode):
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
                "Try `pip install cheroot` or specify another server using the --server option.")
        _logger.error("*" * 78)
        raise

    server_name = "WsgiDAV/{} {} Python/{}".format(
        __version__,
        wsgi.Server.version,
        util.PYTHON_VERSION)
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
            ssl_certificate, ssl_private_key, ssl_certificate_chain)
        protocol = "https"
        _logger.info("SSL / HTTPS enabled. Adapter: {}".format(ssl_adapter))
    elif ssl_certificate or ssl_private_key:
        raise RuntimeError("Option 'ssl_certificate' and 'ssl_private_key' must be used together.")
#     elif ssl_adapter:
#         print("WARNING: Ignored option 'ssl_adapter' (requires 'ssl_certificate').")

    _logger.info("Running {}".format(server_name))
    _logger.info("Serving on {}://{}:{} ...".format(protocol, config["host"], config["port"]))

    server_args = {"bind_addr": (config["host"], config["port"]),
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


def _runFlup(app, config, mode):
    """Run WsgiDAV using flup.server.fcgi, if Flup is installed."""
    # http://trac.saddi.com/flup/wiki/FlupServers
    if mode == "flup-fcgi":
        from flup.server.fcgi import WSGIServer, __version__ as flupver
    elif mode == "flup-fcgi-fork":
        from flup.server.fcgi_fork import WSGIServer, __version__ as flupver
    else:
        raise ValueError

    _logger.info("Running WsgiDAV/{} {}/{}..."
                 .format(__version__, WSGIServer.__module__, flupver))
    server = WSGIServer(app,
                        bindAddress=(config["host"], config["port"]),
                        # debug=True,
                        )
    try:
        server.run()
    except KeyboardInterrupt:
        _logger.warn("Caught Ctrl-C, shutting down...")
    return


def _runWsgiref(app, config, mode):
    """Run WsgiDAV using wsgiref.simple_server, on Python 2.5+."""
    # http://www.python.org/doc/2.5.2/lib/module-wsgiref.html
    from wsgiref.simple_server import make_server, software_version
    version = "WsgiDAV/{} {}".format(__version__, software_version)
    _logger.info("Running {}...".format(version))
    _logger.warn("WARNING: This single threaded server (wsgiref) is not meant for production.")
    httpd = make_server(config["host"], config["port"], app)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        _logger.warn("Caught Ctrl-C, shutting down...")
    return


def _runExtWsgiutils(app, config, mode):
    """Run WsgiDAV using ext_wsgiutils_server from the wsgidav package."""
    from wsgidav.server import ext_wsgiutils_server
    _logger.info("Running WsgiDAV {} on wsgidav.ext_wsgiutils_server...".format(__version__))
    _logger.warn(
            "WARNING: This single threaded server (ext-wsgiutils) is not meant for production.")
    try:
        ext_wsgiutils_server.serve(config, app)
    except KeyboardInterrupt:
        _logger.warn("Caught Ctrl-C, shutting down...")
    return


def run():
    SUPPORTED_SERVERS = {"paste": _runPaste,
                         "cheroot": _runCheroot,
                         "cherrypy": _runCherryPy,
                         "ext-wsgiutils": _runExtWsgiutils,
                         "flup-fcgi": _runFlup,
                         "flup-fcgi_fork": _runFlup,
                         "wsgiref": _runWsgiref,
                         }
    config = _initConfig()

    util.initLogging(config["verbose"], config.get("enable_loggers", []))

    app = WsgiDAVApp(config)

    server = config["server"]
    handler = SUPPORTED_SERVERS.get(server)
    if not handler:
        raise RuntimeError("Unsupported server type {!r} (expected {!r})"
                           .format(server, "', '".join(SUPPORTED_SERVERS.keys())))

    if not useLxml:  # and config["verbose"] >= 1:
        _logger.warn("WARNING: Could not import lxml: using xml instead (slower). "
                     "Consider installing lxml https://pypi.python.org/pypi/lxml.")

    handler(app, config, server)


if __name__ == "__main__":
    # Just in case...
    from multiprocessing import freeze_support
    freeze_support()

    run()
