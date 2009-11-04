"""
error_printer
=============

:Author: Ho Chun Wei, fuzzybr80(at)gmail.com (author of original PyFileServer)
:Author: Martin Wendt, moogle(at)wwwendt.de 
:Copyright: Lesser GNU Public License, see LICENSE file attached with package


WSGI middleware to catch application thrown DAVErrors and return proper 
responses.

+-------------------------------------------------------------------------------+
| The following documentation was taken over from PyFileServer and is outdated! |
+-------------------------------------------------------------------------------+

Usage::

   from wsgidav.processrequesterrorhandler import ErrorPrinter
   WSGIApp = ErrorPrinter(ProtectedWSGIApp, server_descriptor, catchall)

   where:
      ProtectedWSGIApp is the application throwing HTTPRequestExceptions, 
   
      server_descriptor is an optional html string to be included as the 
      footer of any html response sent  
   
      catchall is an optional boolean. if True, ErrorPrinter will catch all
      other exceptions and print a trace to sys.stderr stream before sending
      a 500 Internal Server Error response (default = False)


   Within ProtectedWSGIApp:
   
      from pyfileserver import processrequesterrorhandler
      from wsgidav.processrequesterrorhandler import HTTPRequestException
      ...
      ...
      raise HTTPRequestException(404)
         or
      raise HTTPRequestException(processrequesterrorhandler.HTTP_BAD_REQUEST)
      #escape the existing application and return the 404 Bad Request immediately

Occasionally it may be useful for an internal ProtectedWSGIApp method to catch the
HTTPRequestException (for compiling into a multi-status, for example). The response 
code of the error can be returned as:: 
   
   from pyfileserver import processrequesterrorhandler
   from wsgidav.processrequesterrorhandler import HTTPRequestException
   
   try:
      ...
      raise HTTPRequestException(processrequesterrorhandler.HTTP_BAD_REQUEST)
      ...
   except HTTPRequestException, e:
      numberCode = processrequesterrorhandler.getErrorCodeFromException(e)
      textCode = processrequesterrorhandler.getHttpStatusString(e)

Interface
---------

Classes:

+ 'ErrorPrinter': WSGI Middleware to catch HTTPRequestExceptions and return 
  proper responses 

Exception(s):

+ 'HTTPRequestException': Raised with error code integer (1xx-5xx) within protected 
  application to be caught by ErrorPrinter

Function(s):

+ 'getHttpStatusString(e)': Returns response code string for HTTPRequestException
  e. 

+ 'getErrorCodeFromException(e)': Returns the response code number (1xx-5xx) for 
  HTTPRequestException e

See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
"""

__docformat__ = "reStructuredText"

import util
from dav_error import DAVError, getHttpStatusString, asDAVError,\
    HTTP_INTERNAL_ERROR, ERROR_RESPONSES
import traceback
import sys


#===============================================================================
# ErrorPrinter
#===============================================================================
class ErrorPrinter(object):
    def __init__(self, application, server_descriptor=None, catchall=False):
        self._application = application
        self._server_descriptor = server_descriptor
        self._catch_all_exceptions = catchall

    def __call__(self, environ, start_response):      
        try:
            try:
                # request_server app may be a generator (for example the GET handler)
                # So we must iterate - not return self._application(..)!
                # Otherwise the we could not catch exceptions here. 
#                return self._application(environ, start_response)
                for v in self._application(environ, start_response):
                    util.debug("sc", "ErrorPrinter: yield start")
                    yield v
                    util.debug("sc", "ErrorPrinter: yield end")
#            except GeneratorExit:
#                # TODO: required?
#                util.debug("sc", "GeneratorExit")
#                raise
            except DAVError, e:
                util.debug("sc", "re-raising %s" % e)
                raise
            except Exception, e:
                util.debug("sc", "re-raising 2 - %s" % e)
                if self._catch_all_exceptions:
                    # Catch all exceptions to return as 500 Internal Error
#                    traceback.print_exc(10, sys.stderr) 
                    traceback.print_exc(10, environ.get("wsgi.errors") or sys.stderr) 
                    raise asDAVError(e)               
                else:
                    util.log("ErrorPrinter: caught Exception")
                    traceback.print_exc(10, sys.stderr) # TODO: inserted this for debugging 
                    raise
        except DAVError, e:
            util.debug("sc", "caught %s" % e)
            evalue = e.value
            respcode = getHttpStatusString(e)
            datestr = util.getRfc1123Time()
            
            if evalue == HTTP_INTERNAL_ERROR:# and e.srcexception:
                print >>sys.stderr, "ErrorPrinter: caught HTTPRequestException(HTTP_INTERNAL_ERROR)"
                traceback.print_exc(10, environ.get("wsgi.errors") or sys.stderr) # TODO: inserted this for debugging
                print >>sys.stderr, "e.srcexception:\n%s" % e.srcexception

            if evalue in ERROR_RESPONSES:                  
                respbody = "<html><head><title>" + respcode + "</title></head><body><h1>" + respcode + "</h1>" 
                respbody = respbody + "<p>" + ERROR_RESPONSES[evalue] + "</p>"         
                if e.contextinfo:
                    respbody +=  "%s\n" % e.contextinfo
                respbody += "<hr>\n"
                if self._server_descriptor:
                    respbody = respbody + self._server_descriptor + "<hr>"
                respbody = respbody + datestr + "</body></html>"        
            else:
                # TODO: added html body, to see if this fixes 'connection closed' bug  
                respbody = "<html><head><title>" + respcode + "</title></head><body><h1>" + respcode + "</h1></body></html>"

            util.debug("sc", "Return error html %s: %s" % (respcode, respbody))
            start_response(respcode, 
                           [("Content-Type", "text/html"), 
                            ("Date", datestr)
                            ],
#                           sys.exc_info() # TODO: Always provide exc_info when beginning an error response?
                           ) 
            yield respbody
