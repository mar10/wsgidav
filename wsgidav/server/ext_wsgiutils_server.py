# (c) 2009-2026 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
ext_wsgiutils_server.py is an extension of the wsgiutils server in Paste.
It supports passing all of the HTTP and WebDAV (rfc 2518) methods.

It includes code from the following sources:
``wsgiServer.py`` from wsgiKit <http://www.owlfish.com/software/wsgiutils/> under PSF license,
``wsgiutils_server.py`` from Paste <http://pythonpaste.org> under PSF license,
flexible handler method <http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/307618>
under public domain.


Running as standalone server
----------------------------

To run as a standalone server using the bundled ext_wsgiutils_server.py::

        usage: python ext_wsgiutils_server.py [options] [config-file]

        config-file:
          The configuration file for WsgiDAV. if omitted, the application
          will look for a file named 'WsgiDAV.conf' in the current directory

        options:
          --port=PORT  Port to serve on (default: 8080)
          --host=HOST  Host to serve from (default: localhost, which is only
                            accessible from the local computer; use 0.0.0.0 to make your
                            application public)
          -h, --help   show this help message and exit


Running using other web servers
-------------------------------

To run it with other WSGI web servers, you can::

        from wsgidav.mainappwrapper import PyFileApp
        publish_app = PyFileApp('WsgiDAV.conf')
        # construct the application with configuration file
        # if configuration file is omitted, the application
        # will look for a file named 'WsgiDAV.conf'
        # in the current directory

where ``publish_app`` is the WSGI application to be run, it will be called with
``publish_app(environ, start_response)`` for each incoming request, as described in
`WSGI <http://www.python.org/peps/pep-3333.html>`_

Note: if you are using the paster development server (from Paste <http://pythonpaste.org>), you
can copy ``ext_wsgi_server.py`` to ``<Paste-installation>/paste/servers`` and use this server to
run the application by specifying ``server='ext_wsgiutils'`` in the ``server.conf`` or appropriate
paste configuration.
"""

__docformat__ = "reStructuredText"

import logging
import socket
import socketserver
import sys
import threading
import time
import traceback
from http import client as http_client
from http import server as BaseHTTPServer
from io import StringIO
from urllib.parse import urlparse

from wsgidav import util

_logger = util.get_module_logger(__name__)

_version = 1.0

SERVER_ERROR = """\
<html>
  <head>
     <title>Server Error</title>
  </head>
  <body>
     <h1>Server Error</h1>
     A server error has occurred.  Please contact the system administrator for
     more information.
  </body>
</html>
"""


class ExtHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    _SUPPORTED_METHODS = [
        "HEAD",
        "GET",
        "PUT",
        "POST",
        "OPTIONS",
        "TRACE",
        "DELETE",
        "PROPFIND",
        "PROPPATCH",
        "MKCOL",
        "COPY",
        "MOVE",
        "LOCK",
        "UNLOCK",
    ]

    # Enable automatic keep-alive:
    protocol_version = "HTTP/1.1"

    server_version = f"{util.public_wsgidav_info} ExtServer/{_version} {BaseHTTPServer.BaseHTTPRequestHandler.server_version}"

    def log_message(self, *args):
        pass

    #        BaseHTTPServer.BaseHTTPRequestHandler.log_message(self, *args)

    def log_request(self, *args):
        pass

    #        BaseHTTPServer.BaseHTTPRequestHandler.log_request(self, *args)

    def get_app(self):
        # We want fragments to be returned as part of <path>
        _protocol, _host, path, _parameters, query, _fragment = urlparse(
            f"http://dummyhost{self.path}", allow_fragments=False
        )
        # Find any application we might have
        for app_path, app in self.server.wsgi_applications:
            if path.startswith(app_path):
                # We found the application to use - work out the script_name and path_info
                path_info = path[len(app_path) :]
                if len(path_info) > 0:
                    if not path_info.startswith("/"):
                        path_info = "/" + path_info
                if app_path.endswith("/"):
                    script_name = app_path[:-1]
                else:
                    script_name = app_path
                # Return all this
                return app, script_name, path_info, query
        return None, None, None, None

    def handler_function_closure(self, name):
        def handler_function(*args, **kwargs):
            self.do_method()

        return handler_function

    def do_method(self):
        app, script_name, path_info, query = self.get_app()
        if not app:
            self.send_error(404, "Application not found.")
            return
        self.run_wsgi_app(app, script_name, path_info, query)

    def __getattr__(self, name):
        if len(name) > 3 and name[0:3] == "do_" and name[3:] in self._SUPPORTED_METHODS:
            return self.handler_function_closure(name)
        elif name == "_headers_buffer":
            # 2015-10-22: py3: prevent recursion/stackovervlow
            raise AttributeError
        self.send_error(501, "Method Not Implemented.")
        return

    def run_wsgi_app(self, application, script_name, path_info, query):
        # logging.info ("Running application with SCRIPT_NAME {} PATH_INFO {}".format(
        #     script_name, path_info))

        if self.command == "PUT":
            pass  # breakpoint

        env = {
            "wsgi.version": (1, 0),
            "wsgi.url_scheme": "http",
            "wsgi.input": self.rfile,
            "wsgi.errors": sys.stderr,
            "wsgi.multithread": 1,
            "wsgi.multiprocess": 0,
            "wsgi.run_once": 0,
            "REQUEST_METHOD": self.command,
            "SCRIPT_NAME": script_name,
            "PATH_INFO": path_info,
            "QUERY_STRING": query,
            "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            "CONTENT_LENGTH": self.headers.get("Content-Length", ""),
            "REMOTE_ADDR": self.client_address[0],
            "SERVER_NAME": self.server.server_address[0],
            "SERVER_PORT": util.to_str(self.server.server_address[1]),
            "SERVER_PROTOCOL": self.request_version,
        }
        for http_header, http_value in self.headers.items():
            if http_header.lower() not in ("content-type", "content-length"):
                env["HTTP_{}".format(http_header.replace("-", "_").upper())] = (
                    http_value
                )

        # Setup the state
        self.wsgi_sent_headers = 0
        self.wsgi_headers = []

        try:
            # We have there environment, now invoke the application
            _logger.debug("run_wsgi_app application()...")
            result = application(env, self.wsgi_start_response)
            try:
                for data in result:
                    if data:
                        self.wsgi_write_data(data)
                    else:
                        _logger.debug("run_wsgi_app empty data")
            finally:
                _logger.debug("run_wsgi_app finally.")
                if hasattr(result, "close"):
                    result.close()
        except Exception:
            _logger.debug("run_wsgi_app caught exception...")
            error_msg = StringIO()
            traceback.print_exc(file=error_msg)
            logging.error(error_msg.getvalue())
            if not self.wsgi_sent_headers:
                self.wsgi_start_response(
                    "500 Server Error", [("Content-type", "text/html")]
                )
            self.wsgi_write_data(SERVER_ERROR)

        if not self.wsgi_sent_headers:
            # GC issue 29 sending one byte, when content-length is '0' seems wrong
            # We must write out something!
            #            self.wsgi_write_data (" ")
            self.wsgi_write_data(b"")
        return

    def wsgi_start_response(self, response_status, response_headers, exc_info=None):
        _logger.debug(
            f"wsgi_start_response({response_status}, {response_headers}, {exc_info})"
        )
        if self.wsgi_sent_headers:
            raise Exception("Headers already sent and start_response called again!")
        # Should really take a copy to avoid changes in the application....
        self.wsgi_headers = (response_status, response_headers)
        return self.wsgi_write_data

    def wsgi_write_data(self, data):
        if not self.wsgi_sent_headers:
            status, headers = self.wsgi_headers
            # Need to send header prior to data
            status_code = status[: status.find(" ")]
            status_msg = status[status.find(" ") + 1 :]
            _logger.debug(f"wsgi_write_data: send headers '{status!r}', {headers!r}")
            self.send_response(int(status_code), status_msg)
            for header, value in headers:
                self.send_header(header, value)
            self.end_headers()
            self.wsgi_sent_headers = 1
        # Send the data
        assert type(data) is bytes  # If not, Content-Length is probably wrong!
        _logger.debug(
            f"wsgi_write_data: write {len(data)} bytes: '{util.to_str(data[:50])!r}'..."
        )
        if util.is_str(data):  # If not, Content-Length is probably wrong!
            _logger.info(f"ext_wsgiutils_server: Got unicode data: {data!r}")
            # data = util.wsgi_to_bytes(data)
            data = util.to_bytes(data)

        try:
            self.wfile.write(data)
        except OSError as e:
            # Suppress stack trace when client aborts connection disgracefully:
            # 10053: Software caused connection abort
            # 10054: Connection reset by peer
            if e.args[0] in (10053, 10054):
                _logger.info("*** Caught socket.error: %s", e, file=sys.stderr)
            else:
                raise


class ExtServer(socketserver.ThreadingMixIn, BaseHTTPServer.HTTPServer):
    def handle_error(self, request, client_address):
        """Handle an error gracefully.  May be overridden.

        The default is to _logger.info a traceback and continue.

        """
        ei = sys.exc_info()
        e = ei[1]
        # Suppress stack trace when client aborts connection disgracefully:
        # 10053: Software caused connection abort
        # 10054: Connection reset by peer
        if e.args[0] in (10053, 10054):
            _logger.error(f"*** Caught socket.error: {e}")
            return
        # This is what BaseHTTPServer.HTTPServer.handle_error does, but with
        # added thread ID and using stderr
        _logger.error("-" * 40, file=sys.stderr)
        _logger.error(
            f"<{threading.current_thread().ident}> Exception happened during processing of request from {client_address}"
        )
        _logger.error(client_address, file=sys.stderr)
        traceback.print_exc()
        _logger.error("-" * 40, file=sys.stderr)
        _logger.error(request, file=sys.stderr)

    #        BaseHTTPServer.HTTPServer.handle_error(self, request, client_address)

    def stop_serve_forever(self):
        """Stop serve_forever_stoppable()."""
        assert hasattr(self, "stop_request"), (
            "serve_forever_stoppable() must be called before"
        )
        assert not self.stop_request, "stop_serve_forever() must only be called once"

        #        # Flag stop request
        self.stop_request = True
        time.sleep(0.1)
        if self.stopped:
            # _logger.info "stop_serve_forever() 'stopped'."
            return

        # Add a do_SHUTDOWN method to to the ExtHandler class
        def _shutdown_handler(self):
            """Send 200 OK response, and set server.stop_request to True.

            http://code.activestate.com/recipes/336012/
            """
            #            _logger.info "Handling do_SHUTDOWN request"
            self.send_response(200)
            self.end_headers()
            self.server.stop_request = True

        if not hasattr(ExtHandler, "do_SHUTDOWN"):
            ExtHandler.do_SHUTDOWN = _shutdown_handler

        # Send request, so socket is unblocked
        (host, port) = self.server_address
        #        _logger.info "stop_serve_forever() sending {}:{}/ SHUTDOWN...".format(host, port)
        conn = http_client.HTTPConnection(f"{host}:{port}")
        conn.request("SHUTDOWN", "/")
        #        _logger.info "stop_serve_forever() sent SHUTDOWN request, reading response..."
        conn.getresponse()
        #        _logger.info "stop_serve_forever() received SHUTDOWN response."
        assert self.stop_request

    def serve_forever_stoppable(self):
        """Handle one request at a time until stop_serve_forever().

        http://code.activestate.com/recipes/336012/
        """
        self.stop_request = False
        self.stopped = False

        while not self.stop_request:
            self.handle_request()

        #        _logger.info "serve_forever_stoppable() stopped."
        self.stopped = True

    def __init__(self, server_address, wsgi_applications, serve_files=1):
        BaseHTTPServer.HTTPServer.__init__(self, server_address, ExtHandler)
        app_list = []
        for url_path, wsgi_app in wsgi_applications.items():
            app_list.append((url_path, wsgi_app))
        self.wsgi_applications = app_list
        self.serve_files = serve_files
        self.server_shutting_down = 0


def serve(conf, app):
    host = conf.get("host", "localhost")
    port = int(conf.get("port", 8080))
    server = ExtServer((host, port), {"": app})
    server_version = ExtHandler.server_version
    if conf.get("verbose") >= 1:
        _logger.info(f"Running {server_version}")
        if host in ("", "0.0.0.0"):
            (hostname, _aliaslist, ipaddrlist) = socket.gethostbyname_ex(
                socket.gethostname()
            )
            _logger.info(
                f"Serving at {host}, port {port} (host={hostname!r} {ipaddrlist})..."
            )
        else:
            _logger.info(f"Serving at {host}, port {port}...")
    server.serve_forever()
    # server.serve_forever_stoppable()


if __name__ == "__main__":
    raise RuntimeError("Use run_server.py")
