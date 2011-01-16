# (c) 2009-2011 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Implements a DAVError class that is used to signal WebDAV and HTTP errors. 
"""
import traceback
import datetime
import cgi
import sys

import xml_tools
## Trick PyDev to do intellisense and don't produce warnings:
from xml_tools import etree #@UnusedImport
from wsgidav.version import __version__
if False: from xml.etree import ElementTree as etree     #@Reimport @UnresolvedImport

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
# Condition codes
# http://www.webdav.org/specs/rfc4918.html#precondition.postcondition.xml.elements
#===============================================================================

PRECONDITION_CODE_ProtectedProperty = "{DAV:}cannot-modify-protected-property"
PRECONDITION_CODE_MissingLockToken = "{DAV:}lock-token-submitted"
PRECONDITION_CODE_LockTokenMismatch = "{DAV:}lock-token-matches-request-uri"
PRECONDITION_CODE_LockConflict = "{DAV:}no-conflicting-lock"
PRECONDITION_CODE_PropfindFiniteDepth = "{DAV:}propfind-finite-depth"


class DAVErrorCondition(object):
    def __init__(self, conditionCode):
        self.conditionCode = conditionCode
        self.hrefs = []
        
    def __str__(self):
        return "%s(%s)" % (self.conditionCode, self.hrefs)
    
    def add_href(self, href):
        assert href.startswith("/")
        assert self.conditionCode in (PRECONDITION_CODE_LockConflict,
                                      PRECONDITION_CODE_MissingLockToken)
        if not href in self.hrefs:
            self.hrefs.append(href)
            
    def as_xml(self):
        if self.conditionCode == PRECONDITION_CODE_MissingLockToken:
            assert len(self.hrefs) > 0, "lock-token-submitted requires at least one href"
        errorEL = etree.Element("{DAV:}error")
        condEL = etree.SubElement(errorEL, self.conditionCode)
        for href in self.hrefs:
            etree.SubElement(condEL, "{DAV:}href").text = href
        return errorEL
    
    def as_string(self):
        return xml_tools.xmlToString(self.as_xml(), True)



#===============================================================================
# DAVError
#===============================================================================
# @@: I prefer having a separate exception type for each response,
#     as in paste.httpexceptions.  This way you can catch just the exceptions
#     you want (or you can catch an abstract superclass to get any of them)

class DAVError(Exception):
    # TODO: Ian Bicking proposed to add an additional 'comment' arg, but 
    #       couldn't we use the existing 'contextinfo'?
    # @@: This should also take some message value, for a detailed error message.
    #     This would be helpful for debugging.
    def __init__(self, 
                 statusCode, 
                 contextinfo=None, 
                 srcexception=None,
                 errcondition=None):  # allow passing of Pre- and Postconditions, see http://www.webdav.org/specs/rfc4918.html#precondition.postcondition.xml.elements
        self.value = int(statusCode)
        self.contextinfo = contextinfo
        self.srcexception = srcexception
        self.errcondition = errcondition
        if type(errcondition) is str:
            self.errcondition = DAVErrorCondition(errcondition)
        assert self.errcondition is None or type(self.errcondition) is DAVErrorCondition

    def __repr__(self):
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

        if self.errcondition:
            s += "\n    Error condition: '%s'" % self.errcondition
        return s

    def getResponsePage(self):
        """Return an tuple (content-type, response page)."""
        # If it has pre- or post-condition: return as XML response 
        if self.errcondition:
            return ("application/xml", self.errcondition.as_string())

        # Else return as HTML 
        status = getHttpStatusString(self)
        html = []
        html.append("<!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01//EN' 'http://www.w3.org/TR/html4/strict.dtd'>");
        html.append("<html><head>") 
        html.append("  <meta http-equiv='Content-Type' content='text/html; charset=UTF-8'>")
        html.append("  <title>%s</title>" % status) 
        html.append("</head><body>") 
        html.append("  <h1>%s</h1>" % status) 
        html.append("  <p>%s</p>" % cgi.escape(self.getUserInfo()))         
#        html.append("  <hr>")
#        html.append("  <p>%s</p>" % cgi.escape(str(datetime.datetime.now())))         
#        if self._server_descriptor:
#            respbody.append(self._server_descriptor + "<hr>")
        html.append("<hr/>") 
        html.append("<a href='http://wsgidav.googlecode.com/'>WsgiDAV/%s</a> - %s" 
                    % (__version__, cgi.escape(str(datetime.datetime.now()))))
        html.append("</body></html>")
        html = "\n".join(html)
        return ("text/html", html)


def getHttpStatusCode(v):
    """Return HTTP response code as integer, e.g. 204."""
    if hasattr(v, "value"):
        return int(v.value)  # v is a DAVError
    else:  
        return int(v)


def getHttpStatusString(v):
    """Return HTTP response string, e.g. 204 -> ('204 No Content').
    
    `v`: status code or DAVError 
    """
    code = getHttpStatusCode(v)
    try:
        return ERROR_DESCRIPTIONS[code]
    except:
        return str(code)


def getResponsePage(v):
    v = asDAVError(v)
    return v.getResponsePage()


def asDAVError(e):
    """Convert any non-DAVError exception to HTTP_INTERNAL_ERROR."""
    if isinstance(e, DAVError):
        return e
    elif isinstance(e, Exception):
#        print >>sys.stderr, "asDAVError: %s" % e
#        traceback.print_exception(type(e), e)
        traceback.print_exc()
        return DAVError(HTTP_INTERNAL_ERROR, srcexception=e)
    else:
        return DAVError(HTTP_INTERNAL_ERROR, "%s" % e)



if __name__ == "__main__":
    dec = DAVErrorCondition(PRECONDITION_CODE_LockConflict)
    print dec.as_string()
    dec.add_href("/dav/a")
    print dec.as_string()