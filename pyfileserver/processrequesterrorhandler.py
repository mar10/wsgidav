"""
processrequesterrorhandler
==========================

:Module: pyfileserver.processrequesterrorhandler
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com
:Project: PyFileServer, http://pyfilesync.berlios.de/
:Copyright: Lesser GNU Public License, see LICENSE file attached with package


WSGI Middleware to catch application thrown HTTPRequestExceptions and return 
proper responses

Usage::

   from pyfileserver.processrequesterrorhandler import ErrorPrinter
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
      from pyfileserver.processrequesterrorhandler import HTTPRequestException
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
   from pyfileserver.processrequesterrorhandler import HTTPRequestException
   
   try:
      ...
      raise HTTPRequestException(processrequesterrorhandler.HTTP_BAD_REQUEST)
      ...
   except HTTPRequestException, e:
      numberCode = processrequesterrorhandler.getErrorCodeFromException(e)
      textCode = processrequesterrorhandler.interpretErrorException(e)

Interface
---------

Classes:

+ 'ErrorPrinter': WSGI Middleware to catch HTTPRequestExceptions and return 
  proper responses 

Exception(s):

+ 'HTTPRequestException': Raised with error code integer (1xx-5xx) within protected 
  application to be caught by ErrorPrinter

Function(s):

+ 'interpretErrorException(e)': Returns response code string for HTTPRequestException
  e. 

+ 'getErrorCodeFromException(e)': Returns the response code number (1xx-5xx) for 
  HTTPRequestException e

Constants::

   HTTP_CONTINUE = 100
   HTTP_SWITCHING_PROTOCOLS = 101
   HTTP_PROCESSING = 102
   HTTP_OK = 200
   HTTP_CREATED = 201
   HTTP_ACCEPTED = 202
   HTTP_NON_AUTHORITATIVE_INFO = 203
   HTTP_NO_CONTENT = 204
   HTTP_RESET_CONTENT = 205
   HTTP_PARTIAL_CONTENT = 206
   HTTP_MULTI_STATUS = 207
   HTTP_IM_USED = 226
   HTTP_MULTIPLE_CHOICES = 300
   HTTP_MOVED = 301
   HTTP_FOUND = 302
   HTTP_SEE_OTHER = 303
   HTTP_NOT_MODIFIED = 304
   HTTP_USE_PROXY = 305
   HTTP_TEMP_REDIRECT = 307
   HTTP_BAD_REQUEST = 400
   HTTP_PAYMENT_REQUIRED = 402
   HTTP_FORBIDDEN = 403
   HTTP_NOT_FOUND = 404
   HTTP_METHOD_NOT_ALLOWED = 405
   HTTP_NOT_ACCEPTABLE = 406
   HTTP_PROXY_AUTH_REQUIRED = 407
   HTTP_REQUEST_TIMEOUT = 408
   HTTP_CONFLICT = 409
   HTTP_GONE = 410
   HTTP_LENGTH_REQUIRED = 411
   HTTP_PRECONDITION_FAILED = 412
   HTTP_REQUEST_ENTITY_TOO_LARGE = 413
   HTTP_REQUEST_URI_TOO_LONG = 414
   HTTP_MEDIATYPE_NOT_SUPPORTED = 415
   HTTP_RANGE_NOT_SATISFIABLE = 416
   HTTP_EXPECTATION_FAILED = 417
   HTTP_UNPROCESSABLE_ENTITY = 422
   HTTP_LOCKED = 423
   HTTP_FAILED_DEPENDENCY = 424
   HTTP_UPGRADE_REQUIRED = 426
   HTTP_INTERNAL_ERROR = 500
   HTTP_NOT_IMPLEMENTED = 501
   HTTP_BAD_GATEWAY = 502
   HTTP_SERVICE_UNAVAILABLE = 503
   HTTP_GATEWAY_TIMEOUT = 504
   HTTP_VERSION_NOT_SUPPORTED = 505
   HTTP_INSUFFICIENT_STORAGE = 507
   HTTP_NOT_EXTENDED = 510


"""
__docformat__ = 'reStructuredText'

import os
import time
import traceback
import sys

#List of HTTP Response Codes. 
HTTP_CONTINUE = 100
HTTP_SWITCHING_PROTOCOLS = 101
HTTP_PROCESSING = 102

HTTP_OK = 200
HTTP_CREATED = 201
HTTP_ACCEPTED = 202
HTTP_NON_AUTHORITATIVE_INFO = 203
HTTP_NO_CONTENT = 204
HTTP_RESET_CONTENT = 205
HTTP_PARTIAL_CONTENT = 206
HTTP_MULTI_STATUS = 207
HTTP_IM_USED = 226

HTTP_MULTIPLE_CHOICES = 300
HTTP_MOVED = 301
HTTP_FOUND = 302
HTTP_SEE_OTHER = 303
HTTP_NOT_MODIFIED = 304

HTTP_USE_PROXY = 305
HTTP_TEMP_REDIRECT = 307
HTTP_BAD_REQUEST = 400
HTTP_PAYMENT_REQUIRED = 402
HTTP_FORBIDDEN = 403
HTTP_NOT_FOUND = 404
HTTP_METHOD_NOT_ALLOWED = 405
HTTP_NOT_ACCEPTABLE = 406
HTTP_PROXY_AUTH_REQUIRED = 407
HTTP_REQUEST_TIMEOUT = 408
HTTP_CONFLICT = 409
HTTP_GONE = 410
HTTP_LENGTH_REQUIRED = 411
HTTP_PRECONDITION_FAILED = 412
HTTP_REQUEST_ENTITY_TOO_LARGE = 413
HTTP_REQUEST_URI_TOO_LONG = 414
HTTP_MEDIATYPE_NOT_SUPPORTED = 415
HTTP_RANGE_NOT_SATISFIABLE = 416
HTTP_EXPECTATION_FAILED = 417
HTTP_UNPROCESSABLE_ENTITY = 422
HTTP_LOCKED = 423
HTTP_FAILED_DEPENDENCY = 424
HTTP_UPGRADE_REQUIRED = 426

HTTP_INTERNAL_ERROR = 500
HTTP_NOT_IMPLEMENTED = 501
HTTP_BAD_GATEWAY = 502
HTTP_SERVICE_UNAVAILABLE = 503
HTTP_GATEWAY_TIMEOUT = 504
HTTP_VERSION_NOT_SUPPORTED = 505
HTTP_INSUFFICIENT_STORAGE = 507
HTTP_NOT_EXTENDED = 510

# if ERROR_DESCRIPTIONS exists for an error code, the error description will be sent as
# the error response code. Otherwise only the numeric code itself is sent.

ERROR_DESCRIPTIONS = dict()
ERROR_DESCRIPTIONS[HTTP_NOT_MODIFIED] = "304 Not Modified"
ERROR_DESCRIPTIONS[HTTP_BAD_REQUEST] = "400 Bad Request"
ERROR_DESCRIPTIONS[HTTP_FORBIDDEN] = "403 Forbidden"
ERROR_DESCRIPTIONS[HTTP_METHOD_NOT_ALLOWED] = "405 Method Not Allowed"
ERROR_DESCRIPTIONS[HTTP_NOT_FOUND] = "404 Not Found"
ERROR_DESCRIPTIONS[HTTP_CONFLICT] = '409 Conflict'
ERROR_DESCRIPTIONS[HTTP_PRECONDITION_FAILED] = "412 Precondition Failed"
ERROR_DESCRIPTIONS[HTTP_RANGE_NOT_SATISFIABLE] = "416 Range Not Satisfiable"
ERROR_DESCRIPTIONS[HTTP_MEDIATYPE_NOT_SUPPORTED] = "415 Media Type Not Supported"
ERROR_DESCRIPTIONS[HTTP_LOCKED] = "423 Locked"
ERROR_DESCRIPTIONS[HTTP_INTERNAL_ERROR] = "500 Internal Server Error"
ERROR_DESCRIPTIONS[HTTP_NOT_IMPLEMENTED] = "501 Not Implemented"

# if ERROR_RESPONSES exists for an error code, a html output will be sent as response
# body including the ERROR_RESPONSES value. Otherwise a null response body is sent.
# Mostly for browser viewing

ERROR_RESPONSES = dict()
ERROR_RESPONSES[HTTP_BAD_REQUEST] = "An invalid request was specified"
ERROR_RESPONSES[HTTP_NOT_FOUND] = "The specified resource was not found"
ERROR_RESPONSES[HTTP_FORBIDDEN] = "Access denied to the specified resource"
ERROR_RESPONSES[HTTP_INTERNAL_ERROR] = "An internal server error occured"


def interpretErrorException(e):
    if e.value in ERROR_DESCRIPTIONS:
        return ERROR_DESCRIPTIONS[e.value]
    else:
        return str(e.value)

def getErrorCodeFromException(e):
    return e.value


# @@: I prefer having a separate exception type for each response,
#     as in paste.httpexceptions.  This way you can catch just the exceptions
#     you want (or you can catch an abstract superclass to get any of them)

class HTTPRequestException(Exception):
    # @@: This should also take some message value, for a detailed error message.
    #     This would be helpful for debugging.
    def __init__(self, value, contextinfo=None, srcexception=None):
        self.value = value
        self.contextinfo = contextinfo
        self.srcexception = srcexception
    def __str__(self):
        return repr(self.value)             

class ErrorPrinter(object):
    def __init__(self, application, server_descriptor=None, catchall=False):
        self._application = application
        self._server_descriptor = server_descriptor
        self._catch_all_exceptions = catchall

    def __call__(self, environ, start_response):      
        try:
            try:
                for v in iter(self._application(environ, start_response)):
                    yield v
            except HTTPRequestException, e:
                raise
            except:
                if self._catch_all_exceptions:
                    #Catch all exceptions to return as 500 Internal Error
                    traceback.print_exc(10, sys.stderr) 
                    raise HTTPRequestException(HTTP_INTERNAL_ERROR)               
                else:
                    raise
        except HTTPRequestException, e:
            evalue = getErrorCodeFromException(e)
            respcode = interpretErrorException(e)
            datestr = time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())

            if evalue in ERROR_RESPONSES:                  
                start_response(respcode, [('Content-Type', 'text/html'), ('Date', datestr)])

                respbody = '<html><head><title>' + respcode + '</title></head><body><H1>' + respcode + '</H1>' 
                respbody = respbody + ERROR_RESPONSES[evalue] + '<HR>'         
                if self._server_descriptor:
                    respbody = respbody + self._server_descriptor + '<BR>'
                respbody = respbody + datestr + '</body></html>'        

                yield respbody 
            else:
                start_response(respcode, [('Content-Type', 'text/html'), ('Content-Length', '0'), ('Date', datestr)])
                yield ''
        return

