# (c) 2009-2011 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
WSGI middleware to catch application thrown DAVErrors and return proper 
responses.

See `Developers info`_ for more information about the WsgiDAV architecture.

.. _`Developers info`: http://docs.wsgidav.googlecode.com/hg/html/develop.html  
"""
__docformat__ = "reStructuredText"

import util
from dav_error import DAVError, getHttpStatusString, asDAVError,\
    HTTP_INTERNAL_ERROR, HTTP_NOT_MODIFIED, HTTP_NO_CONTENT
import traceback
import sys

_logger = util.getModuleLogger(__name__)

#===============================================================================
# ErrorPrinter
#===============================================================================
class ErrorPrinter(object):
#    def __init__(self, application, server_descriptor=None, catchall=False):
    def __init__(self, application, catchall=False):
        self._application = application
#        self._server_descriptor = server_descriptor
        self._catch_all_exceptions = catchall

    def __call__(self, environ, start_response):      
        try:
            try:
                # request_server app may be a generator (for example the GET handler)
                # So we must iterate - not return self._application(..)!
                # Otherwise the we could not catch exceptions here. 
                for v in self._application(environ, start_response):
                    yield v
            except DAVError, e:
                _logger.debug("re-raising %s" % e)
                raise
            except Exception, e:
                # Caught a non-DAVError 
                if self._catch_all_exceptions:
                    # Catch all exceptions to return as 500 Internal Error
                    traceback.print_exc(10, environ.get("wsgi.errors") or sys.stderr)
                    raise asDAVError(e)
                else:
                    util.warn("ErrorPrinter: caught Exception")
                    traceback.print_exc(10, sys.stderr) 
                    raise
        except DAVError, e:
            _logger.debug("caught %s" % e)

            status = getHttpStatusString(e)
            # Dump internal errors to console
            if e.value == HTTP_INTERNAL_ERROR:
                print >>sys.stdout, "ErrorPrinter: caught HTTPRequestException(HTTP_INTERNAL_ERROR)"
                traceback.print_exc(10, environ.get("wsgi.errors") or sys.stdout)
                print >>sys.stdout, "e.srcexception:\n%s" % e.srcexception
            elif e.value in (HTTP_NOT_MODIFIED, HTTP_NO_CONTENT):
#                util.log("ErrorPrinter: forcing empty error response for %s" % e.value)
                # See paste.lint: these code don't have content
                start_response(status, [("Content-Length", "0"),
                                        ("Date", util.getRfc1123Time()),
                                        ])
                yield ""
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
