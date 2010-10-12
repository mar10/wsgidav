# -*- coding: iso-8859-1 -*-
"""
run_server
==========

:Author: Ho Chun Wei, fuzzybr80(at)gmail.com (author of original PyFileServer)
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

See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
"""
from optparse import OptionParser
from pprint import pprint
from inspect import isfunction
from wsgidav.wsgidav_app import DEFAULT_CONFIG
import traceback
import sys
import os

from wsgidav import util

try:
    from wsgidav.version import __version__
    from wsgidav.wsgidav_app import WsgiDAVApp
    from wsgidav.fs_dav_provider import FilesystemProvider
except ImportError, e:
    raise RuntimeError("Could not import wsgidav package:\n%s\nSee http://wsgidav.googlecode.com/." % e)

__docformat__ = "reStructuredText"

# Use this config file, if no --config_file option is specified
DEFAULT_CONFIG_FILE = "wsgidav.conf"


def _initCommandLineOptions():
    """Parse command line options into a dictionary."""
    
    usage = """\
%prog [options]

Examples:
Share filesystem folder '/temp': 
  wsgidav --port=80 --host=0.0.0.0 --root=/temp
Run using a configuration file: 
  wsgidav --port=80 --host=0.0.0.0 --config=~/wsgidav.conf

If no config file is specified, the application will look for a file named
'wsgidav.conf' in the current directory.
See sample_wsgidav.conf for some explanation of the configuration file format.
If no config file is found, a default FilesystemProvider is used."""

#    description = """\
#%prog is a standalone server for WsgiDAV.
#It tries to use pre-installed WSGI servers (cherrypy.wsgiserver,
#paste.httpserver, wsgiref.simple_server) or uses our built-in
#ext_wsgiutils_server.py."""

#    epilog = """Licensed under the MIT license.
#See http://wsgidav.googlecode.com for additional information."""
            
    parser = OptionParser(usage=usage, 
                          version=__version__,
#                          conflict_handler="error",
                          description=None, #description,
                          add_help_option=True,
#                          prog="wsgidav",
#                          epilog=epilog # TODO: Not available on Python 2.4?
                          )    
 
    parser.add_option("-p", "--port", 
                      dest="port",
                      type="int",
                      default=8080,
                      help="port to serve on (default: %default)")
    parser.add_option("-H", "--host", # '-h' conflicts with --help  
                      dest="host",
                      default="localhost",
                      help="host to serve from (default: %default). 'localhost' is only accessible from the local computer. Use 0.0.0.0 to make your application public"),
    parser.add_option("-r", "--root",
                      dest="root_path", 
                      help="Path to a file system folder to publish as share '/'.")

    parser.add_option("-q", "--quiet",
                      action="store_const", const=0, dest="verbose",
                      help="suppress any output except for errors.")
    parser.add_option("-v", "--verbose",
                      action="store_const", const=2, dest="verbose", default=1,
                      help="Set verbose = 2: print informational output.")
    parser.add_option("-d", "--debug",
                      action="store_const", const=3, dest="verbose",
                      help="Set verbose = 3: print requests and responses.")
    
    parser.add_option("-c", "--config",
                      dest="config_file", 
                      help="Configuration file (default: %s in current directory)." % DEFAULT_CONFIG_FILE)

    parser.add_option("", "--reload",
                      action="store_true", dest="reload", 
                      help="Restart server when source files are changed. Used by run_reloading_server. (Requires paste.reloader.)")

#    parser.add_option("", "--profile",
#                      action="store_true", dest="profile", 
#                      help="Profile ")

   
    (options, args) = parser.parse_args()

    if len(args) > 0:
        parser.error("Too many arguments")

    if options.config_file is None:
        # If --config was omitted, use default (if it exists)
        defPath = os.path.abspath(DEFAULT_CONFIG_FILE)
        if os.path.exists(defPath):
            if options.verbose >= 2:
                print "Using default configuration file: %s" % defPath
            options.config_file = defPath
    else:
        # If --config was specified convert to absolute path and assert it exists
        options.config_file = os.path.abspath(options.config_file)
        if not os.path.exists(options.config_file):
            parser.error("Could not open specified configuration file: %s" % options.config_file)

    # Convert options object to dictionary
    cmdLineOpts = options.__dict__.copy()
    if options.verbose >= 3:
        print "Command line options:"
        for k, v in cmdLineOpts.items():
            print "    %-12s: %s" % (k, v)
    return cmdLineOpts




def _readConfigFile(config_file, verbose):
    """Read configuration file options into a dictionary."""

    if not os.path.exists(config_file):
        raise RuntimeError("Couldn't open configuration file '%s'." % config_file)
    
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
    except Exception, e:
#        if verbose >= 1:
#            traceback.print_exc() 
        exceptioninfo = traceback.format_exception_only(sys.exc_type, sys.exc_value) #@UndefinedVariable
        exceptiontext = ""
        for einfo in exceptioninfo:
            exceptiontext += einfo + "\n"   
#        raise RuntimeError("Failed to read configuration file: " + config_file + "\nDue to " + exceptiontext)
        print >>sys.stderr, "Failed to read configuration file: " + config_file + "\nDue to " + exceptiontext
        raise
    
    return conf




def _initConfig():
    """Setup configuration dictionary from default, command line and configuration file."""
    cmdLineOpts = _initCommandLineOptions()

    # Set config defaults
    config = DEFAULT_CONFIG.copy()

    # Configuration file overrides defaults
    config_file = cmdLineOpts.get("config_file")
    if config_file: 
        verbose = cmdLineOpts.get("verbose", 2)
        fileConf = _readConfigFile(config_file, verbose)
        config.update(fileConf)
    else:
        if cmdLineOpts["verbose"] >= 2:
            print "Running without configuration file."
    
    # Command line overrides file
    if cmdLineOpts.get("port"):
        config["port"] = cmdLineOpts.get("port")
    if cmdLineOpts.get("host"):
        config["host"] = cmdLineOpts.get("host")
    if cmdLineOpts.get("verbose") is not None:
        config["verbose"] = cmdLineOpts.get("verbose")
    if cmdLineOpts.get("profile") is not None:
        config["profile"] = True

    if cmdLineOpts.get("root_path"):
        root_path = os.path.abspath(cmdLineOpts.get("root_path"))
        config["provider_mapping"]["/"] = FilesystemProvider(root_path)
    
    if cmdLineOpts["verbose"] >= 3:
        print "Configuration(%s):" % cmdLineOpts["config_file"]
        pprint(config)

    if not config["provider_mapping"]:
        print >>sys.stderr, "ERROR: No DAV provider defined. Try --help option."
        sys.exit(-1)
#        raise RuntimeWarning("At least one DAV provider must be specified by a --root option, or in a configuration file.")

    if cmdLineOpts.get("reload"):
        print >>sys.stderr, "Installing paste.reloader."
        from paste import reloader  #@UnresolvedImport
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
    _logger = util.getModuleLogger(__name__, True)
    try:
        from paste import httpserver
        version = "WsgiDAV/%s %s" % (__version__, httpserver.WSGIHandler.server_version)
        if config["verbose"] >= 1:
            print "Running %s..." % version

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

        if config["verbose"] >=3:
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
        if host == '0.0.0.0':
            print 'serving on 0.0.0.0:%s view at %s://127.0.0.1:%s' % \
                (port, 'http', port)
        else:
            print "serving on %s://%s:%s" % ('http', host, port)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            # allow CTRL+C to shutdown
            pass
    except ImportError, e:
        if config["verbose"] >= 1:
            print "Could not import paste.httpserver."
        return False
    return True




def _runCherryPy(app, config, mode):
    """Run WsgiDAV using cherrypy.wsgiserver, if CherryPy is installed."""
    assert mode in ("cherrypy", "cherrypy-bundled")
    try:
        if mode == "cherrypy-bundled":
            from wsgidav.server import cherrypy_wsgiserver as wsgiserver
        else:
            # http://cherrypy.org/apidocs/3.0.2/cherrypy.wsgiserver-module.html  
            from cherrypy import wsgiserver, __version__ as cp_version
        version = "WsgiDAV/%s %s" % (__version__, wsgiserver.CherryPyWSGIServer.version)
        wsgiserver.CherryPyWSGIServer.version = version
        if config["verbose"] >= 1:
#            print "Running %s..." % version
            print("Runing %s, listening on %s://%s:%s" 
                  % (version, 'http', config["host"], config["port"]))
        server = wsgiserver.CherryPyWSGIServer(
            (config["host"], config["port"]), 
            app,
#            server_name=version
            )
        server.start()
    except ImportError, e:
        if config["verbose"] >= 1:
            print "Could not import wsgiserver.CherryPyWSGIServer."
        return False
    return True




def _runFlup(app, config, mode):
    """Run WsgiDAV using flup.server.fcgi, if Flup is installed."""
    try:
        # http://trac.saddi.com/flup/wiki/FlupServers
        if mode == "flup-fcgi":
            from flup.server.fcgi import WSGIServer, __version__ as flupver
        elif mode == "flup-fcgi_fork":
            from flup.server.fcgi_fork import WSGIServer, __version__ as flupver
        else:
            raise ValueError    

        if config["verbose"] >= 2:
            print "Running WsgiDAV/%s %s/%s..." % (__version__,
                                                   WSGIServer.__module__,
                                                   flupver)
        server = WSGIServer(app,
                            bindAddress=(config["host"], config["port"]),
#                            bindAddress=("127.0.0.1", 8001),
#                            debug=True,
                            )
        server.run()
    except ImportError, e:
        if config["verbose"] >= 1:
            print "Could not import flup.server.fcgi", e
        return False
    return True




def _runSimpleServer(app, config, mode):
    """Run WsgiDAV using wsgiref.simple_server, on Python 2.5+."""
    try:
        # http://www.python.org/doc/2.5.2/lib/module-wsgiref.html
        from wsgiref.simple_server import make_server, software_version
#        if config["verbose"] >= 1:
#            print "Running WsgiDAV %s on wsgiref.simple_server (single threaded)..." % __version__
        version = "WsgiDAV/%s %s" % (__version__, software_version)
        if config["verbose"] >= 1:
            print "Running %s..." % version
        httpd = make_server(config["host"], config["port"], app)
#        print "Serving HTTP on port 8000..."
        httpd.serve_forever()
    except ImportError, e:
        if config["verbose"] >= 1:
            print "Could not import wsgiref.simple_server (part of standard lib since Python 2.5)."
        return False
    return True




def _runBuiltIn(app, config, mode):
    """Run WsgiDAV using ext_wsgiutils_server from the wsgidav package."""
    try:
        import ext_wsgiutils_server
        if config["verbose"] >= 2:
            print "Running WsgiDAV %s on wsgidav.ext_wsgiutils_server..." % __version__
        ext_wsgiutils_server.serve(config, app)
    except ImportError, e:
        if config["verbose"] >= 1:
            print "Could not import wsgidav.ext_wsgiutils_server (part of WsgiDAV)."
        return False
    return True


SUPPORTED_SERVERS = {"paste": _runPaste,
                     "cherrypy": _runCherryPy,
                     "cherrypy-bundled": _runCherryPy,
                     "wsgiref": _runSimpleServer,
                     "flup-fcgi": _runFlup,
                     "flup-fcgi_fork": _runFlup,
                     "wsgidav": _runBuiltIn,
                     }


#def _run_real(config):
#    app = WsgiDAVApp(config)
#    
#    # Try running WsgiDAV inside the following external servers:
#    res = False
#    for e in config["ext_servers"]:
#        fn = SUPPORTED_SERVERS.get(e)
#        if fn is None:
#            print "Invalid external server '%s'. (expected: '%s')" % (e, "', '".join(SUPPORTED_SERVERS.keys()))
#            
#        elif fn(app, config, e):
#            res = True
#            break
#    
#    if not res:
#        print "No supported WSGI server installed."   
#
#    
#def run():
#    config = _initConfig()
#    if config.get("profile"):
#        import cProfile, pstats, StringIO
#        prof = cProfile.Profile()
#        prof = prof.runctx("_run_real(config)", globals(), locals())
#        stream = StringIO.StringIO()
#        stats = pstats.Stats(prof, stream=stream)
#        stats.sort_stats("time")  # Or cumulative
#        stats.print_stats(80)  # 80 = how many to print
#        # The rest is optional.
#        # stats.print_callees()
#        # stats.print_callers()
##        logging.info("Profile data:\n%s", stream.getvalue())
#        print stream.getvalue()
#        return
#    return _real_run(config) 


def run():
    config = _initConfig()
    
    app = WsgiDAVApp(config)
    
    # Try running WsgiDAV inside the following external servers:
    res = False
    for e in config["ext_servers"]:
        fn = SUPPORTED_SERVERS.get(e)
        if fn is None:
            print "Invalid external server '%s'. (expected: '%s')" % (e, "', '".join(SUPPORTED_SERVERS.keys()))
            
        elif fn(app, config, e):
            res = True
            break
    
    if not res:
        print "No supported WSGI server installed."   

    
if __name__ == "__main__":
    run()
