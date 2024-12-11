# (c) 2009-2024 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
WSGI middleware used for debugging (optional).

This module dumps request and response information to the console, depending
on current debug configuration.

On init:
    Define HTTP methods and litmus tests, that should turn on the verbose mode
    (currently hard coded).
For every request:
    Increase value of ``environ['verbose']``, if the request should be debugged.
    Also dump request and response headers and body.

    Then pass the request to the next middleware.

These configuration settings are evaluated:

*verbose*
    This is also used by other modules. This filter adds additional information
    depending on the value.

    =======  ===================================================================
    verbose  Effect
    =======  ===================================================================
     <= 3     No additional output (only standard request logging).
     4        Dump headers of all requests and responses.
     5        Dump headers and bodies of all requests and responses.
    =======  ===================================================================

*debug_methods*
    Boost verbosity to 3 while processing certain request methods. This option
    is ignored, when ``verbose < 2``.

    Configured like::

        debug_methods = ["PROPPATCH", "PROPFIND", "GET", "HEAD", "DELETE",
                         "PUT", "COPY", "MOVE", "LOCK", "UNLOCK",
                         ]

*debug_litmus*
    Boost verbosity to 3 while processing litmus tests that contain certain
    substrings. This option is ignored, when ``verbose < 2``.

    Configured like::

        debug_litmus = ["notowner_modify", "props: 16", ]

"""

import sys
import threading

from wsgidav import util
from wsgidav.mw.base_mw import BaseMiddleware
from wsgidav.util import safe_re_encode

__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)


class WsgiDavDebugFilter(BaseMiddleware):
    def __init__(self, wsgidav_app, next_app, config):
        super().__init__(wsgidav_app, next_app, config)
        self._config = config
        log_opts = config.get("logging") or {}
        # self.out = sys.stdout
        self.passedLitmus = {}
        # These methods boost verbose=2 to verbose=3
        self.debug_methods = log_opts.get("debug_methods", [])
        # Litmus tests containing these string boost verbose=2 to verbose=3
        self.debug_litmus = log_opts.get("debug_litmus", [])
        # Exit server, as soon as this litmus test has finished
        self.break_after_litmus = [
            # "locks: 15",
        ]

    def __call__(self, environ, start_response):
        """ """
        # srvcfg = environ["wsgidav.config"]
        verbose = self._config.get("verbose", 3)

        method = environ["REQUEST_METHOD"]

        debugBreak = False
        dumpRequest = False
        dumpResponse = False

        if verbose >= 5:
            dumpRequest = dumpResponse = True

        # Process URL commands
        if "dump_storage" in environ.get("QUERY_STRING", ""):
            dav = environ.get("wsgidav.provider")
            if dav.lock_manager:
                dav.lock_manager._dump()
            if dav.prop_manager:
                dav.prop_manager._dump()

        # Turn on max. debugging for selected litmus tests
        litmusTag = environ.get("HTTP_X_LITMUS", environ.get("HTTP_X_LITMUS_SECOND"))
        if litmusTag and verbose >= 3:
            _logger.info(f"----\nRunning litmus test {litmusTag!r}...")
            for litmusSubstring in self.debug_litmus:
                if litmusSubstring in litmusTag:
                    verbose = 5
                    debugBreak = True
                    dumpRequest = True
                    dumpResponse = True
                    break
            for litmusSubstring in self.break_after_litmus:
                if (
                    litmusSubstring in self.passedLitmus
                    and litmusSubstring not in litmusTag
                ):
                    _logger.info(f" *** break after litmus {litmusTag}")
                    sys.exit(-1)
                if litmusSubstring in litmusTag:
                    self.passedLitmus[litmusSubstring] = True

        # Turn on max. debugging for selected request methods
        if verbose >= 3 and method in self.debug_methods:
            verbose = 5
            debugBreak = True
            dumpRequest = True
            dumpResponse = True

        # Set debug options to environment
        environ["wsgidav.verbose"] = verbose
        # environ["wsgidav.debug_methods"] = self.debug_methods
        environ["wsgidav.debug_break"] = debugBreak
        environ["wsgidav.dump_request_body"] = dumpRequest
        environ["wsgidav.dump_response_body"] = dumpResponse

        # Dump request headers
        if dumpRequest:
            _logger.info(f"{method} Request ---")
            # _logger.info("<{}> --- {} Request ---".format(
            #         threading.current_thread().ident, method))
            for k, v in environ.items():
                try:
                    v = safe_re_encode(v, "utf8")
                except Exception:
                    pass
                _logger.info(f"{k:<20}: {v!r}")
            _logger.info("\n")

        # Intercept start_response
        #
        sub_app_start_response = util.SubAppStartResponse()

        nbytes = 0
        first_yield = True
        app_iter = self.next_app(environ, sub_app_start_response)

        for v in app_iter:
            # Start response (the first time)
            if first_yield:
                # Success!
                start_response(
                    sub_app_start_response.status,
                    sub_app_start_response.response_headers,
                    sub_app_start_response.exc_info,
                )

            # Dump response headers
            if first_yield and dumpResponse:
                _logger.info(
                    f"<{threading.current_thread().ident}> ---{method}  Response({sub_app_start_response.status}): ---"
                )
                headersdict = dict(sub_app_start_response.response_headers)
                for envitem in headersdict.keys():
                    _logger.info(f"{envitem}: {repr(headersdict[envitem])}")
                _logger.info("")

            # Check, if response is a binary string, otherwise we probably have
            # calculated a wrong content-length
            assert util.is_bytes(v), v

            # Dump response body
            drb = environ.get("wsgidav.dump_response_body")
            if util.is_basestring(drb):
                # Middleware provided a formatted body representation
                _logger.info(drb)
                drb = environ["wsgidav.dump_response_body"] = None
            elif drb is True:
                # Else dump what we get, (except for long GET responses)
                if method == "GET":
                    if first_yield:
                        _logger.info(f"{v[:50]}...")
                elif len(v) > 0:
                    _logger.info(v)

            nbytes += len(v)
            first_yield = False
            yield v
        if hasattr(app_iter, "close"):
            app_iter.close()

        # Start response (if it hasn't been done yet)
        if first_yield:
            # Success!
            start_response(
                sub_app_start_response.status,
                sub_app_start_response.response_headers,
                sub_app_start_response.exc_info,
            )

        if dumpResponse:
            _logger.info(
                f"<{threading.current_thread().ident}> --- End of {method} Response ({nbytes:d} bytes) ---"
            )
        return
