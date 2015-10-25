# (c) 2009-2015 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
WSGI middleware to catch application thrown DAVErrors and return proper 
responses.

See `Developers info`_ for more information about the WsgiDAV architecture.

.. _`Developers info`: http://wsgidav.readthedocs.org/en/latest/develop.html  
"""
from __future__ import print_function

import sys
import traceback

from wsgidav.dav_error import DAVError, getHttpStatusString, asDAVError,\
    HTTP_INTERNAL_ERROR, HTTP_NOT_MODIFIED, HTTP_NO_CONTENT
from wsgidav.middleware import BaseMiddleware
from wsgidav import util

__docformat__ = "reStructuredText"

_logger = util.getModuleLogger(__name__)

#===============================================================================
# ErrorPrinter
#===============================================================================
class ErrorPrinter(BaseMiddleware):

    def __init__(self, application, config):
        self._application = application
        self._catch_all_exceptions = config.get("catchall", False)

    def __call__(self, environ, start_response):      
        # Intercept start_response
        sub_app_start_response = util.SubAppStartResponse()

        try:
            try:
                # request_server app may be a generator (for example the GET handler)
                # So we must iterate - not return self._application(..)!
                # Otherwise the we could not catch exceptions here. 
                response_started = False
                app_iter = self._application(environ, sub_app_start_response)
                for v in app_iter:
                    # Start response (the first time)
                    if not response_started:
                        # Success!
                        start_response(sub_app_start_response.status,
                                       sub_app_start_response.response_headers,
                                       sub_app_start_response.exc_info)
                    response_started = True

                    yield v

                # Close out iterator
                if hasattr(app_iter, "close"):
                    app_iter.close()

                # Start response (if it hasn't been done yet)
                if not response_started:
                    # Success!
                    start_response(sub_app_start_response.status,
                                   sub_app_start_response.response_headers,
                                   sub_app_start_response.exc_info)

                return
            except DAVError as e:
                _logger.debug("re-raising %s" % e)
                raise
            except Exception as e:
                # Caught a non-DAVError 
                if self._catch_all_exceptions:
                    # Catch all exceptions to return as 500 Internal Error
                    traceback.print_exc(10, environ.get("wsgi.errors") or sys.stderr)
                    raise asDAVError(e)
                else:
                    util.warn("ErrorPrinter: caught Exception")
                    traceback.print_exc(10, sys.stderr) 
                    raise
        except DAVError as e:
            _logger.debug("caught %s" % e)

            status = getHttpStatusString(e)
            # Dump internal errors to console
            if e.value == HTTP_INTERNAL_ERROR:
                print("ErrorPrinter: caught HTTPRequestException(HTTP_INTERNAL_ERROR)", file=sys.stdout)
                traceback.print_exc(10, environ.get("wsgi.errors") or sys.stdout)
                print("e.srcexception:\n%s" % e.srcexception, file=sys.stdout)
            elif e.value in (HTTP_NOT_MODIFIED, HTTP_NO_CONTENT):
#                util.log("ErrorPrinter: forcing empty error response for %s" % e.value)
                # See paste.lint: these code don't have content
                start_response(status, [("Content-Length", "0"),
                                        ("Date", util.getRfc1123Time()),
                                        ])
                yield b""
                return

            # If exception has pre-/post-condition: return as XML response, 
            # else return as HTML 
            content_type, body = e.getResponsePage()            

            # TODO: provide exc_info=sys.exc_info()?
            start_response(status, [("Content-Type", content_type), 
                                    ("Content-Length", str(len(body))),
                                    ("Date", util.getRfc1123Time()),
                                    ])
            yield body 
            return
