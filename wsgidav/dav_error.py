# (c) 2009-2024 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Implements a DAVError class that is used to signal WebDAV and HTTP errors.
"""

import datetime
from html import escape as html_escape

from wsgidav import xml_tools
from wsgidav.xml_tools import etree

__docformat__ = "reStructuredText"

# ========================================================================
# List of HTTP Response Codes.
# ========================================================================
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
HTTP_UNAUTHORIZED = 401
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


# ========================================================================
# if ERROR_DESCRIPTIONS exists for an error code, the error description will be
# sent as the error response code.
# Otherwise only the numeric code itself is sent.
# ========================================================================
# TODO: paste.httpserver may raise exceptions, if a status code is not
# followed by a description, so should define all of them.
ERROR_DESCRIPTIONS = {
    HTTP_OK: "200 OK",
    HTTP_CREATED: "201 Created",
    HTTP_NO_CONTENT: "204 No Content",
    HTTP_NOT_MODIFIED: "304 Not Modified",
    HTTP_BAD_REQUEST: "400 Bad Request",
    HTTP_UNAUTHORIZED: "401 Unauthorized",
    HTTP_FORBIDDEN: "403 Forbidden",
    HTTP_METHOD_NOT_ALLOWED: "405 Method Not Allowed",
    HTTP_NOT_FOUND: "404 Not Found",
    HTTP_CONFLICT: "409 Conflict",
    HTTP_PRECONDITION_FAILED: "412 Precondition Failed",
    HTTP_MEDIATYPE_NOT_SUPPORTED: "415 Media Type Not Supported",
    HTTP_RANGE_NOT_SATISFIABLE: "416 Range Not Satisfiable",
    HTTP_LOCKED: "423 Locked",
    HTTP_FAILED_DEPENDENCY: "424 Failed Dependency",
    HTTP_INTERNAL_ERROR: "500 Internal Server Error",
    HTTP_NOT_IMPLEMENTED: "501 Not Implemented",
    HTTP_BAD_GATEWAY: "502 Bad Gateway",
}

# ========================================================================
# if ERROR_RESPONSES exists for an error code, a html output will be sent as response
# body including the ERROR_RESPONSES value. Otherwise a null response body is sent.
# Mostly for browser viewing
# ========================================================================

ERROR_RESPONSES = {
    HTTP_BAD_REQUEST: "An invalid request was specified",
    HTTP_NOT_FOUND: "The specified resource was not found",
    HTTP_UNAUTHORIZED: "Invalid authentication credentials for the requested resource",
    HTTP_FORBIDDEN: "Access denied to the specified resource",
    HTTP_INTERNAL_ERROR: "An internal server error occurred",
    HTTP_NOT_IMPLEMENTED: "Not implemented",
}


# ========================================================================
# Condition codes
# http://www.webdav.org/specs/rfc4918.html#precondition.postcondition.xml.elements
# ========================================================================

PRECONDITION_CODE_ProtectedProperty = "{DAV:}cannot-modify-protected-property"
PRECONDITION_CODE_MissingLockToken = "{DAV:}lock-token-submitted"
PRECONDITION_CODE_LockTokenMismatch = "{DAV:}lock-token-matches-request-uri"
PRECONDITION_CODE_LockConflict = "{DAV:}no-conflicting-lock"
PRECONDITION_CODE_PropfindFiniteDepth = "{DAV:}propfind-finite-depth"


def to_bytes(s, encoding="utf8"):
    """Convert a text string (unicode) to bytestring (str on Py2 and bytes on Py3)."""
    if type(s) is not bytes:
        s = bytes(s, encoding)
    return s


def to_str(s, encoding="utf8"):
    """Convert data to native str type (bytestring on Py2 and unicode on Py3)."""
    if type(s) is bytes:
        s = str(s, encoding)
    elif type(s) is not str:
        s = str(s)
    return s


class DAVErrorCondition:
    """May be embedded in :class:`DAVError` instances to store additional data."""

    def __init__(self, condition_code):
        self.condition_code = condition_code
        self.hrefs = []

    def __str__(self):
        return f"{self.condition_code}({self.hrefs})"

    def add_href(self, href):
        assert href.startswith("/")
        assert self.condition_code in (
            PRECONDITION_CODE_LockConflict,
            PRECONDITION_CODE_MissingLockToken,
        )
        if href not in self.hrefs:
            self.hrefs.append(href)

    def as_xml(self):
        if self.condition_code == PRECONDITION_CODE_MissingLockToken:
            assert (
                len(self.hrefs) > 0
            ), "lock-token-submitted requires at least one href"
        error_el = etree.Element("{DAV:}error")
        cond_el = etree.SubElement(error_el, self.condition_code)
        for href in self.hrefs:
            etree.SubElement(cond_el, "{DAV:}href").text = href
        return error_el

    def as_string(self):
        return to_str(xml_tools.xml_to_bytes(self.as_xml(), pretty=True))


# ========================================================================
# DAVError
# ========================================================================
# @@: I prefer having a separate exception type for each response,
#     as in paste.httpexceptions.  This way you can catch just the exceptions
#     you want (or you can catch an abstract superclass to get any of them)


class DAVError(Exception):
    """General error class that is used to signal HTTP and WEBDAV errors.

    May contain a :class:`DAVErrorCondition`.
    """

    # TODO: Ian Bicking proposed to add an additional 'comment' arg, but
    #       couldn't we use the existing 'context_info'?
    # @@: This should also take some message value, for a detailed error message.
    #     This would be helpful for debugging.

    def __init__(
        self,
        status_code,
        context_info=None,
        *,
        src_exception=None,
        err_condition=None,
        add_headers=None,
    ):
        # allow passing of Pre- and Postconditions, see
        # http://www.webdav.org/specs/rfc4918.html#precondition.postcondition.xml.elements
        self.value = int(status_code)
        self.context_info = context_info
        self.src_exception = src_exception
        self.err_condition = err_condition
        self.add_headers = add_headers
        if isinstance(err_condition, str):
            self.err_condition = DAVErrorCondition(err_condition)
        assert (
            self.err_condition is None or type(self.err_condition) is DAVErrorCondition
        )

    def __repr__(self):
        return f"DAVError({self.get_user_info()})"

    def get_user_info(self):
        """Return readable string."""
        if self.value in ERROR_DESCRIPTIONS:
            s = f"{ERROR_DESCRIPTIONS[self.value]}"
        else:
            s = f"{self.value}"

        if self.context_info:
            s += f": {self.context_info}"
        elif self.value in ERROR_RESPONSES:
            s += f": {ERROR_RESPONSES[self.value]}"

        if self.src_exception:
            s += f"\n    Source exception: {self.src_exception!r}"

        if self.err_condition:
            s += f"\n    Error condition: {self.err_condition!r}"

        # if self.add_headers:
        #     s += f"\n    Add headers: {self.add_headers}"
        return s

    def get_response_page(self):
        """Return a tuple (content-type, response page)."""
        from wsgidav.util import public_wsgidav_info

        # If it has pre- or post-condition: return as XML response
        if self.err_condition:
            return (
                "application/xml; charset=utf-8",
                to_bytes(self.err_condition.as_string()),
            )

        # Else return as HTML
        status = get_http_status_string(self)
        html = []
        html.append(
            "<!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01//EN' "
            "'http://www.w3.org/TR/html4/strict.dtd'>"
        )
        html.append("<html><head>")
        html.append(
            "  <meta http-equiv='Content-Type' content='text/html; charset=utf-8'>"
        )
        html.append(f"  <title>{status}</title>")
        html.append("</head><body>")
        html.append(f"  <h1>{status}</h1>")
        html.append(f"  <p>{html_escape(self.get_user_info())}</p>")
        html.append("<hr/>")
        html.append(
            "<a href='https://github.com/mar10/wsgidav/'>{}</a> - {}".format(
                public_wsgidav_info,
                html_escape(str(datetime.datetime.now()), "utf-8"),
            )
        )
        html.append("</body></html>")
        html = "\n".join(html)
        return ("text/html; charset=utf-8", to_bytes(html))


def get_http_status_code(v):
    """Return HTTP response code as integer, e.g. 204."""
    if hasattr(v, "value"):
        return int(v.value)  # v is a DAVError
    return int(v)


def get_http_status_string(v):
    """Return HTTP response string, e.g. 204 -> ('204 No Content').
    The return string always includes descriptive text, to satisfy Apache mod_dav.

    `v`: status code or DAVError
    """
    code = get_http_status_code(v)
    try:
        return ERROR_DESCRIPTIONS[code]
    except KeyError:
        return f"{code} Status"


def get_response_page(v):
    v = as_DAVError(v)
    return v.get_response_page()


def as_DAVError(e):
    """Convert any non-DAVError exception to HTTP_INTERNAL_ERROR."""
    if isinstance(e, DAVError):
        return e
    elif isinstance(e, Exception):
        # traceback.print_exc()
        return DAVError(HTTP_INTERNAL_ERROR, src_exception=e)
    else:
        return DAVError(HTTP_INTERNAL_ERROR, f"{e}")
