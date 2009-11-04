"""
dav_error
=========
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com (author of original PyFileServer)
:Author: Martin Wendt, moogle(at)wwwendt.de 
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

Implements a DAVError class that is used to signal WebDAV and HTTP errors. 

See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
"""
import sys
__docformat__ = "reStructuredText"

#===============================================================================
# List of HTTP Response Codes. 
#===============================================================================
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


#===============================================================================
# if ERROR_DESCRIPTIONS exists for an error code, the error description will be 
# sent as the error response code. 
# Otherwise only the numeric code itself is sent.
#===============================================================================
# TODO: paste.httpserver may raise exceptions, if a status code is not followed by a description, so should define all of them.
ERROR_DESCRIPTIONS = {
    HTTP_OK: "200 OK",
    HTTP_CREATED: "201 Created",
    HTTP_NO_CONTENT: "204 No Content",
    HTTP_NOT_MODIFIED: "304 Not Modified",
    HTTP_BAD_REQUEST: "400 Bad Request",
    HTTP_FORBIDDEN: "403 Forbidden",
    HTTP_METHOD_NOT_ALLOWED: "405 Method Not Allowed",
    HTTP_NOT_FOUND: "404 Not Found",
    HTTP_CONFLICT: "409 Conflict",
    HTTP_PRECONDITION_FAILED: "412 Precondition Failed",
    HTTP_RANGE_NOT_SATISFIABLE: "416 Range Not Satisfiable",
    HTTP_MEDIATYPE_NOT_SUPPORTED: "415 Media Type Not Supported",
    HTTP_LOCKED: "423 Locked",
    HTTP_FAILED_DEPENDENCY: "424 Failed Dependency",
    HTTP_INTERNAL_ERROR: "500 Internal Server Error",
    HTTP_NOT_IMPLEMENTED: "501 Not Implemented",
    HTTP_BAD_GATEWAY: "502 Bad Gateway",
    }

#===============================================================================
# if ERROR_RESPONSES exists for an error code, a html output will be sent as response
# body including the ERROR_RESPONSES value. Otherwise a null response body is sent.
# Mostly for browser viewing
#===============================================================================

ERROR_RESPONSES = {
    HTTP_BAD_REQUEST: "An invalid request was specified",
    HTTP_NOT_FOUND: "The specified resource was not found",
    HTTP_FORBIDDEN: "Access denied to the specified resource",
    HTTP_INTERNAL_ERROR: "An internal server error occurred",
    HTTP_NOT_IMPLEMENTED: "Not Implemented",
    }


#===============================================================================
# @see: http://www.webdav.org/specs/rfc4918.html#precondition.postcondition.xml.elements
#===============================================================================
PRECONDITION_CODE_ProtectedProperty = "cannot-modify-protected-property"
PRECONDITION_CODE_MissingLockToken = "lock-token-submitted"
PRECONDITION_CODE_LockTokenMismatch = "lock-token-matches-request-uri"
PRECONDITION_CODE_LockConflict = "no-conflicting-lock"
PRECONDITION_CODE_PropfindFiniteDepth = "propfind-finite-depth"


def makePreconditionError(preconditionCode):
    return """<error><%s/></error>""" % preconditionCode


def getHttpStatusString(v):
    """Return string representation, that can be used as HTTP response status."""
    if hasattr(v, "value"):
        status = str(v.value)  # v is a DAVError
    else:  
        status = str(v)
    try:
        return ERROR_DESCRIPTIONS[int(status)]
    except:
        return status


def asDAVError(e):
    """Convert any non-DAVError exception to HTTP_INTERNAL_ERROR."""
    if isinstance(e, DAVError):
        return e
    elif isinstance(e, Exception):
        print >>sys.stderr, "asHTTPRequestException: %s" % e
        return DAVError(HTTP_INTERNAL_ERROR, srcexception=e)
    else:
        return DAVError(HTTP_INTERNAL_ERROR, "%s" % e)



# @@: I prefer having a separate exception type for each response,
#     as in paste.httpexceptions.  This way you can catch just the exceptions
#     you want (or you can catch an abstract superclass to get any of them)

class DAVError(Exception):
    # TODO: Ian Bicking proposed to add an additional 'comment' arg, but couldn't we use the existing 'contextinfo'?
    # @@: This should also take some message value, for a detailed error message.
    #     This would be helpful for debugging.
    def __init__(self, 
                 statusCode, 
                 contextinfo=None, 
                 srcexception=None,
                 preconditionCode=None):  # allow passing of Pre- and Postconditions, see http://www.webdav.org/specs/rfc4918.html#precondition.postcondition.xml.elements
        self.value = int(statusCode)
        self.contextinfo = contextinfo
        self.srcexception = srcexception
        self.preconditionCode = preconditionCode
        
    def __repr__(self):
#        return repr(self.value)
        return "DAVError(%s)" % self.getUserInfo()
    
    def __str__(self): # Required for 2.4
        return self.__repr__()

    def getUserInfo(self):
        """Return readable string."""
        if self.value in ERROR_DESCRIPTIONS:
            s = "%s" % ERROR_DESCRIPTIONS[self.value]
        else:
            s = "%s" % self.value

        if self.contextinfo:
            s+= ": %s" % self.contextinfo
        elif self.value in ERROR_RESPONSES:
            s += ": %s" % ERROR_RESPONSES[self.value]
        
        if self.srcexception:
            s += "\n    Source exception: '%s'" % self.srcexception

        return s
