# -*- coding: utf-8 -*-
# (c) 2009-2019 Martin Wendt and contributors; see WsgiDAV https://github.com/m ar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Miscellaneous support functions for WsgiDAV.
"""
from email.utils import formatdate, parsedate
from hashlib import md5
from pprint import pformat
from wsgidav import compat
from wsgidav.dav_error import (
    as_DAVError,
    DAVError,
    get_http_status_string,
    HTTP_BAD_REQUEST,
    HTTP_CREATED,
    HTTP_NO_CONTENT,
    HTTP_NOT_MODIFIED,
    HTTP_OK,
    HTTP_PRECONDITION_FAILED,
)
from wsgidav.xml_tools import etree, is_etree_element, make_sub_element, xml_to_bytes

import calendar
import logging
import mimetypes
import os
import re
import socket
import stat
import sys
import time


__docformat__ = "reStructuredText"

#: The base logger (silent by default)
BASE_LOGGER_NAME = "wsgidav"
_logger = logging.getLogger(BASE_LOGGER_NAME)

PYTHON_VERSION = "{}.{}.{}".format(
    sys.version_info[0], sys.version_info[1], sys.version_info[2]
)


# ========================================================================
# Time tools
# ========================================================================


def get_rfc1123_time(secs=None):
    """Return <secs> in rfc 1123 date/time format (pass secs=None for current date)."""
    # GC issue #20: time string must be locale independent
    return formatdate(timeval=secs, localtime=False, usegmt=True)


def get_rfc3339_time(secs=None):
    """Return <secs> in RFC 3339 date/time format (pass secs=None for current date).

    RFC 3339 is a subset of ISO 8601, used for '{DAV:}creationdate'.
    See http://tools.ietf.org/html/rfc3339
    """
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(secs))


def get_log_time(secs=None):
    """Return <secs> in log time format (pass secs=None for current date)."""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(secs))


def parse_time_string(timestring):
    """Return the number of seconds since the epoch, for a date/time string.

    Returns None for invalid input

    The following time type strings are supported:

    Sun, 06 Nov 1994 08:49:37 GMT  ; RFC 822, updated by RFC 1123
    Sunday, 06-Nov-94 08:49:37 GMT ; RFC 850, obsoleted by RFC 1036
    Sun Nov  6 08:49:37 1994       ; ANSI C's asctime() format
    """
    result = _parse_gmt_time(timestring)
    if result:
        return calendar.timegm(result)
    return None


def _parse_gmt_time(timestring):
    """Return a standard time tuple (see time and calendar), for a date/time string."""
    # Sun, 06 Nov 1994 08:49:37 GMT  ; RFC 822, updated by RFC 1123
    try:
        return time.strptime(timestring, "%a, %d %b %Y %H:%M:%S GMT")
    except Exception:
        pass

    # Sunday, 06-Nov-94 08:49:37 GMT ; RFC 850, obsoleted by RFC 1036
    try:
        return time.strptime(timestring, "%A %d-%b-%y %H:%M:%S GMT")
    except Exception:
        pass

    # Sun Nov  6 08:49:37 1994       ; ANSI C's asctime() format
    try:
        return time.strptime(timestring, "%a %b %d %H:%M:%S %Y")
    except Exception:
        pass

    # Sun Nov  6 08:49:37 1994 +0100      ; ANSI C's asctime() format with
    # timezon
    try:
        return parsedate(timestring)
    except Exception:
        pass

    return None


# ========================================================================
# Logging
# ========================================================================


def init_logging(config):
    """Initialize base logger named 'wsgidav'.

    The base logger is filtered by the `verbose` configuration option.
    Log entries will have a time stamp and thread id.

    :Parameters:
        verbose : int
            Verbosity configuration (0..5)
        enable_loggers : string list
            List of module logger names, that will be switched to DEBUG level.

    Module loggers
    ~~~~~~~~~~~~~~
    Module loggers (e.g 'wsgidav.lock_manager') are named loggers, that can be
    independently switched to DEBUG mode.

    Except for verbosity, they will inherit settings from the base logger.

    They will suppress DEBUG level messages, unless they are enabled by passing
    their name to util.init_logging().

    If enabled, module loggers will print DEBUG messages, even if verbose == 3.

    Example initialize and use a module logger, that will generate output,
    if enabled (and verbose >= 2)::

        _logger = util.get_module_logger(__name__)
        [..]
        _logger.debug("foo: '{}'".format(s))

    This logger would be enabled by passing its name to init_logging()::

        enable_loggers = ["lock_manager",
                          "property_manager",
                         ]
        util.init_logging(2, enable_loggers)


    Log Level Matrix
    ~~~~~~~~~~~~~~~~

    +---------+--------+---------------------------------------------------------------+
    | Verbose | Option |                       Log level                               |
    | level   |        +-------------+------------------------+------------------------+
    |         |        | base logger | module logger(default) | module logger(enabled) |
    +=========+========+=============+========================+========================+
    |    0    | -qqq   | CRITICAL    | CRITICAL               | CRITICAL               |
    +---------+--------+-------------+------------------------+------------------------+
    |    1    | -qq    | ERROR       | ERROR                  | ERROR                  |
    +---------+--------+-------------+------------------------+------------------------+
    |    2    | -q     | WARN        | WARN                   | WARN                   |
    +---------+--------+-------------+------------------------+------------------------+
    |    3    |        | INFO        | INFO                   | **DEBUG**              |
    +---------+--------+-------------+------------------------+------------------------+
    |    4    | -v     | DEBUG       | DEBUG                  | DEBUG                  |
    +---------+--------+-------------+------------------------+------------------------+
    |    5    | -vv    | DEBUG       | DEBUG                  | DEBUG                  |
    +---------+--------+-------------+------------------------+------------------------+

    """
    verbose = config.get("verbose", 3)

    enable_loggers = config.get("enable_loggers", [])
    if enable_loggers is None:
        enable_loggers = []

    logger_date_format = config.get("logger_date_format", "%Y-%m-%d %H:%M:%S")
    logger_format = config.get(
        "logger_format",
        "%(asctime)s.%(msecs)03d - <%(thread)d> %(name)-27s %(levelname)-8s:  %(message)s",
    )

    formatter = logging.Formatter(logger_format, logger_date_format)

    # Define handlers
    consoleHandler = logging.StreamHandler(sys.stdout)
    #    consoleHandler = logging.StreamHandler(sys.stderr)
    consoleHandler.setFormatter(formatter)
    # consoleHandler.setLevel(logging.DEBUG)

    # Add the handlers to the base logger
    logger = logging.getLogger(BASE_LOGGER_NAME)

    if verbose >= 4:  # --verbose
        logger.setLevel(logging.DEBUG)
    elif verbose == 3:  # default
        logger.setLevel(logging.INFO)
    elif verbose == 2:  # --quiet
        logger.setLevel(logging.WARN)
        # consoleHandler.setLevel(logging.WARN)
    elif verbose == 1:  # -qq
        logger.setLevel(logging.ERROR)
        # consoleHandler.setLevel(logging.WARN)
    else:  # -qqq
        logger.setLevel(logging.CRITICAL)
        # consoleHandler.setLevel(logging.ERROR)

    # Don't call the root's handlers after our custom handlers
    logger.propagate = False

    # Remove previous handlers
    for hdlr in logger.handlers[:]:  # Must iterate an array copy
        try:
            hdlr.flush()
            hdlr.close()
        except Exception:
            pass
        logger.removeHandler(hdlr)

    logger.addHandler(consoleHandler)

    if verbose >= 3:
        for e in enable_loggers:
            if not e.startswith(BASE_LOGGER_NAME + "."):
                e = BASE_LOGGER_NAME + "." + e
            lg = logging.getLogger(e.strip())
            lg.setLevel(logging.DEBUG)


def get_module_logger(moduleName, defaultToVerbose=False):
    """Create a module logger, that can be en/disabled by configuration.

    @see: unit.init_logging
    """
    # moduleName = moduleName.split(".")[-1]
    if not moduleName.startswith(BASE_LOGGER_NAME + "."):
        moduleName = BASE_LOGGER_NAME + "." + moduleName
    logger = logging.getLogger(moduleName)
    # if logger.level == logging.NOTSET and not defaultToVerbose:
    #     logger.setLevel(logging.INFO)  # Disable debug messages by default
    return logger


def deep_update(d, u):
    for k, v in u.items():
        if isinstance(v, compat.collections_abc.Mapping):
            d[k] = deep_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d


# ========================================================================
# Module Import
# ========================================================================


def dynamic_import_class(name):
    """Import a class from a module string, e.g. ``my.module.ClassName``."""
    import importlib

    module_name, class_name = name.rsplit(".", 1)
    try:
        module = importlib.import_module(module_name)
    except Exception as e:
        _logger.exception("Dynamic import of {!r} failed: {}".format(name, e))
        raise
    the_class = getattr(module, class_name)
    return the_class


def dynamic_instantiate_middleware(name, args, expand=None):
    """Import a class and instantiate with custom args.

    Example:
        name = "my.module.Foo"
        args_dict = {
            "bar": 42,
            "baz": "qux"
            }
        =>
        from my.module import Foo
        return Foo(bar=42, baz="qux")
    """

    def _expand(v):
        """Replace some string templates with defined values."""
        if expand and compat.is_basestring(v) and v.lower() in expand:
            return expand[v]
        return v

    try:
        the_class = dynamic_import_class(name)
        inst = None
        if type(args) in (tuple, list):
            args = tuple(map(_expand, args))
            inst = the_class(*args)
        else:
            assert type(args) is dict
            args = {k: _expand(v) for k, v in args.items()}
            inst = the_class(**args)

        _logger.debug("Instantiate {}({}) => {}".format(name, args, inst))
    except Exception:
        _logger.exception("ERROR: Instantiate {}({}) => {}".format(name, args, inst))

    return inst


# ========================================================================
# Strings
# ========================================================================


def lstripstr(s, prefix, ignoreCase=False):
    if ignoreCase:
        if not s.lower().startswith(prefix.lower()):
            return s
    else:
        if not s.startswith(prefix):
            return s
    return s[len(prefix) :]


def save_split(s, sep, maxsplit):
    """Split string, always returning n-tuple (filled with None if necessary)."""
    tok = s.split(sep, maxsplit)
    while len(tok) <= maxsplit:
        tok.append(None)
    return tok


def pop_path(path):
    """Return '/a/b/c' -> ('a', '/b/c')."""
    if path in ("", "/"):
        return ("", "")
    assert path.startswith("/")
    first, _sep, rest = path.lstrip("/").partition("/")
    return (first, "/" + rest)


def pop_path2(path):
    """Return '/a/b/c' -> ('a', 'b', '/c')."""
    if path in ("", "/"):
        return ("", "", "")
    first, rest = pop_path(path)
    second, rest = pop_path(rest)
    return (first, second, "/" + rest)


def shift_path(script_name, path_info):
    """Return ('/a', '/b/c') -> ('b', '/a/b', 'c')."""
    segment, rest = pop_path(path_info)
    return (segment, join_uri(script_name.rstrip("/"), segment), rest.rstrip("/"))


def split_namespace(clarkName):
    """Return (namespace, localname) tuple for a property name in Clark Notation.

    Namespace defaults to ''.
    Example:
    '{DAV:}foo'  -> ('DAV:', 'foo')
    'bar'  -> ('', 'bar')
    """
    if clarkName.startswith("{") and "}" in clarkName:
        ns, localname = clarkName.split("}", 1)
        return (ns[1:], localname)
    return ("", clarkName)


def to_unicode_safe(s):
    """Convert a binary string to Unicode using UTF-8 (fallback to ISO-8859-1)."""
    try:
        u = compat.to_unicode(s, "utf8")
    except ValueError:
        _logger.error(
            "to_unicode_safe({!r}) *** UTF-8 failed. Trying ISO-8859-1".format(s)
        )
        u = compat.to_unicode(s, "ISO-8859-1")
    return u


def safe_re_encode(s, encoding_to, errors="backslashreplace"):
    """Re-encode str or binary so that is compatible with a given encoding (replacing
    unsupported chars).

    We use ASCII as default, which gives us some output that contains \x99 and \u9999
    for every character > 127, for easier debugging.
    (e.g. if we don't know the encoding, see #87, #96)
    """
    # prev = s
    if not encoding_to:
        encoding_to = "ASCII"
    if compat.is_bytes(s):
        s = s.decode(encoding_to, errors=errors).encode(encoding_to)
    else:
        s = s.encode(encoding_to, errors=errors).decode(encoding_to)
    # print("safe_re_encode({}, {}) => {}".format(prev, encoding_to, s))
    return s


def string_repr(s):
    """Return a string as hex dump."""
    if compat.is_bytes(s):
        res = "{!r}: ".format(s)
        for b in s:
            if type(b) is str:  # Py2
                b = ord(b)
            res += "%02x " % b
        return res
    return "{}".format(s)


def get_file_extension(path):
    ext = os.path.splitext(path)[1]
    return ext


def byte_number_string(
    number, thousandsSep=True, partition=False, base1024=True, appendBytes=True
):
    """Convert bytes into human-readable representation."""
    magsuffix = ""
    bytesuffix = ""

    if partition:
        magnitude = 0
        if base1024:
            while number >= 1024:
                magnitude += 1
                number = number >> 10
        else:
            while number >= 1000:
                magnitude += 1
                number /= 1000.0
        # TODO: use "9 KB" instead of "9K Bytes"?
        # TODO use 'kibi' for base 1024?
        # http://en.wikipedia.org/wiki/Kibi-#IEC_standard_prefixes
        magsuffix = ["", "K", "M", "G", "T", "P"][magnitude]

    if appendBytes:
        if number == 1:
            bytesuffix = " Byte"
        else:
            bytesuffix = " Bytes"

    if thousandsSep and (number >= 1000 or magsuffix):
        # locale.setlocale(locale.LC_ALL, "")
        # # TODO: make precision configurable
        # snum = locale.format("%d", number, thousandsSep)
        snum = "{:,d}".format(number)
    else:
        snum = str(number)

    return "{}{}{}".format(snum, magsuffix, bytesuffix)


# ========================================================================
# WSGI
# ========================================================================
def get_content_length(environ):
    """Return a positive CONTENT_LENGTH in a safe way (return 0 otherwise)."""
    # TODO: http://www.wsgi.org/wsgi/WSGI_2.0
    try:
        return max(0, int(environ.get("CONTENT_LENGTH", 0)))
    except ValueError:
        return 0


# def readAllInput(environ):
#    """Read and discard all from from wsgi.input, if this has not been done yet."""
#    cl = get_content_length(environ)
#    if environ.get("wsgidav.all_input_read") or cl == 0:
#        return
#    assert not environ.get("wsgidav.some_input_read")
#    write("Reading and discarding %s bytes input." % cl)
#    environ["wsgi.input"].read(cl)
#    environ["wsgidav.all_input_read"] = 1


def read_and_discard_input(environ):
    """Read 1 byte from wsgi.input, if this has not been done yet.

    Returning a response without reading from a request body might confuse the
    WebDAV client.
    This may happen, if an exception like '401 Not authorized', or
    '500 Internal error' was raised BEFORE anything was read from the request
    stream.

    See GC issue 13, issue 23
    See http://groups.google.com/group/paste-users/browse_frm/thread/fc0c9476047e9a47?hl=en

    Note that with persistent sessions (HTTP/1.1) we must make sure, that the
    'Connection: closed' header is set with the response, to prevent reusing
    the current stream.
    """
    if environ.get("wsgidav.some_input_read") or environ.get("wsgidav.all_input_read"):
        return
    cl = get_content_length(environ)
    assert cl >= 0
    if cl == 0:
        return

    READ_ALL = True

    environ["wsgidav.some_input_read"] = 1
    if READ_ALL:
        environ["wsgidav.all_input_read"] = 1

    wsgi_input = environ["wsgi.input"]

    # TODO: check if still required after GC issue 24 is fixed
    if hasattr(wsgi_input, "_consumed") and hasattr(wsgi_input, "length"):
        # Seems to be Paste's httpserver.LimitedLengthFile
        # see http://groups.google.com/group/paste-users/browse_thread/thread/fc0c9476047e9a47/aa4a3aa416016729?hl=en&lnk=gst&q=.input#aa4a3aa416016729  # noqa
        # Consume something if nothing was consumed *and* work
        # around a bug where paste.httpserver allows negative lengths
        if wsgi_input._consumed == 0 and wsgi_input.length > 0:
            # This seems to work even if there's 10K of input.
            if READ_ALL:
                n = wsgi_input.length
            else:
                n = 1
            body = wsgi_input.read(n)
            _logger.debug(
                "Reading {} bytes from potentially unread httpserver.LimitedLengthFile: '{}'...".format(
                    n, body[:50]
                )
            )

    elif hasattr(wsgi_input, "_sock") and hasattr(wsgi_input._sock, "settimeout"):
        # Seems to be a socket
        try:
            # Set socket to non-blocking
            sock = wsgi_input._sock
            timeout = sock.gettimeout()
            sock.settimeout(0)
            # Read one byte
            try:
                if READ_ALL:
                    n = cl
                else:
                    n = 1
                body = wsgi_input.read(n)
                _logger.debug(
                    "Reading {} bytes from potentially unread POST body: '{}'...".format(
                        n, body[:50]
                    )
                )
            except socket.error as se:
                # se(10035, 'The socket operation could not complete without blocking')
                _logger.error("-> read {} bytes failed: {}".format(n, se))
            # Restore socket settings
            sock.settimeout(timeout)
        except Exception:
            _logger.error("--> wsgi_input.read(): {}".format(sys.exc_info()))


def fail(value, context_info=None, src_exception=None, err_condition=None):
    """Wrapper to raise (and log) DAVError."""
    if isinstance(value, Exception):
        e = as_DAVError(value)
    else:
        e = DAVError(value, context_info, src_exception, err_condition)
    _logger.debug("Raising DAVError {}".format(e.get_user_info()))
    raise e


# ========================================================================
# SubAppStartResponse
# ========================================================================
class SubAppStartResponse(object):
    def __init__(self):
        self.__status = ""
        self.__response_headers = []
        self.__exc_info = None

        super(SubAppStartResponse, self).__init__()

    @property
    def status(self):
        return self.__status

    @property
    def response_headers(self):
        return self.__response_headers

    @property
    def exc_info(self):
        return self.__exc_info

    def __call__(self, status, response_headers, exc_info=None):
        self.__status = status
        self.__response_headers = response_headers
        self.__exc_info = exc_info


# ========================================================================
# URLs
# ========================================================================


def join_uri(uri, *segments):
    """Append segments to URI.

    Example: join_uri("/a/b", "c", "d")
    """
    sub = "/".join(segments)
    if not sub:
        return uri
    return uri.rstrip("/") + "/" + sub


def get_uri_name(uri):
    """Return local name, i.e. last segment of URI."""
    return uri.strip("/").split("/")[-1]


def get_uri_parent(uri):
    """Return URI of parent collection with trailing '/', or None, if URI is top-level.

    This function simply strips the last segment. It does not test, if the
    target is a 'collection', or even exists.
    """
    if not uri or uri.strip() == "/":
        return None
    return uri.rstrip("/").rsplit("/", 1)[0] + "/"


def is_child_uri(parentUri, childUri):
    """Return True, if childUri is a child of parentUri.

    This function accounts for the fact that '/a/b/c' and 'a/b/c/' are
    children of '/a/b' (and also of '/a/b/').
    Note that '/a/b/cd' is NOT a child of 'a/b/c'.
    """
    return (
        parentUri
        and childUri
        and childUri.rstrip("/").startswith(parentUri.rstrip("/") + "/")
    )


def is_equal_or_child_uri(parentUri, childUri):
    """Return True, if childUri is a child of parentUri or maps to the same resource.

    Similar to <util.is_child_uri>_ ,  but this method also returns True, if parent
    equals child. ('/a/b' is considered identical with '/a/b/').
    """
    return (
        parentUri
        and childUri
        and (childUri.rstrip("/") + "/").startswith(parentUri.rstrip("/") + "/")
    )


def make_complete_url(environ, localUri=None):
    """URL reconstruction according to PEP 333.
    @see https://www.python.org/dev/peps/pep-3333/#url-reconstruction
    """
    url = environ["wsgi.url_scheme"] + "://"

    if environ.get("HTTP_HOST"):
        url += environ["HTTP_HOST"]
    else:
        url += environ["SERVER_NAME"]

        if environ["wsgi.url_scheme"] == "https":
            if environ["SERVER_PORT"] != "443":
                url += ":" + environ["SERVER_PORT"]
        else:
            if environ["SERVER_PORT"] != "80":
                url += ":" + environ["SERVER_PORT"]

    url += compat.quote(environ.get("SCRIPT_NAME", ""))

    if localUri is None:
        url += compat.quote(environ.get("PATH_INFO", ""))
        if environ.get("QUERY_STRING"):
            url += "?" + environ["QUERY_STRING"]
    else:
        url += localUri  # TODO: quote?
    return url


# ========================================================================
# XML
# ========================================================================


def parse_xml_body(environ, allow_empty=False):
    """Read request body XML into an etree.Element.

    Return None, if no request body was sent.
    Raise HTTP_BAD_REQUEST, if something else went wrong.

    TODO: this is a very relaxed interpretation: should we raise HTTP_BAD_REQUEST
    instead, if CONTENT_LENGTH is missing, invalid, or 0?

    RFC: For compatibility with HTTP/1.0 applications, HTTP/1.1 requests containing
    a message-body MUST include a valid Content-Length header field unless the
    server is known to be HTTP/1.1 compliant.
    If a request contains a message-body and a Content-Length is not given, the
    server SHOULD respond with 400 (bad request) if it cannot determine the
    length of the message, or with 411 (length required) if it wishes to insist
    on receiving a valid Content-Length."

    So I'd say, we should accept a missing CONTENT_LENGTH, and try to read the
    content anyway.
    But WSGI doesn't guarantee to support input.read() without length(?).
    At least it locked, when I tried it with a request that had a missing
    content-type and no body.

    Current approach: if CONTENT_LENGTH is

    - valid and >0:
      read body (exactly <CONTENT_LENGTH> bytes) and parse the result.
    - 0:
      Assume empty body and return None or raise exception.
    - invalid (negative or not a number:
      raise HTTP_BAD_REQUEST
    - missing:
      NOT: Try to read body until end and parse the result.
      BUT: assume '0'
    - empty string:
      WSGI allows it to be empty or absent: treated like 'missing'.
    """
    #
    clHeader = environ.get("CONTENT_LENGTH", "").strip()
    #    content_length = -1 # read all of stream
    if clHeader == "":
        # No Content-Length given: read to end of stream
        # TODO: etree.parse() locks, if input is invalid?
        #        pfroot = etree.parse(environ["wsgi.input"]).getroot()
        # requestbody = environ["wsgi.input"].read()  # TODO: read() should be
        # called in a loop?
        requestbody = ""
    else:
        try:
            content_length = int(clHeader)
            if content_length < 0:
                raise DAVError(HTTP_BAD_REQUEST, "Negative content-length.")
        except ValueError:
            raise DAVError(HTTP_BAD_REQUEST, "content-length is not numeric.")

        if content_length == 0:
            requestbody = ""
        else:
            requestbody = environ["wsgi.input"].read(content_length)
            environ["wsgidav.all_input_read"] = 1

    if requestbody == "":
        if allow_empty:
            return None
        else:
            raise DAVError(HTTP_BAD_REQUEST, "Body must not be empty.")

    try:
        rootEL = etree.fromstring(requestbody)
    except Exception as e:
        raise DAVError(HTTP_BAD_REQUEST, "Invalid XML format.", src_exception=e)

    # If dumps of the body are desired, then this is the place to do it pretty:
    if environ.get("wsgidav.dump_request_body"):
        _logger.info(
            "{} XML request body:\n{}".format(
                environ["REQUEST_METHOD"],
                compat.to_native(xml_to_bytes(rootEL, pretty_print=True)),
            )
        )
        environ["wsgidav.dump_request_body"] = False

    return rootEL


# def sendResponse(environ, start_response, body, content_type):
#    """Send a WSGI response for a HTML or XML string."""
#    assert content_type in ("application/xml", "text/html")
#
#    start_response(status, [("Content-Type", content_type),
#                            ("Date", get_rfc1123_time()),
#                            ("Content-Length", str(len(body))),
#                            ])
#    return [ body ]


def send_status_response(environ, start_response, e, add_headers=None, is_head=False):
    """Start a WSGI response for a DAVError or status code."""
    status = get_http_status_string(e)
    headers = []
    if add_headers:
        headers.extend(add_headers)
    #    if 'keep-alive' in environ.get('HTTP_CONNECTION', '').lower():
    #        headers += [
    #            ('Connection', 'keep-alive'),
    #        ]

    if e in (HTTP_NOT_MODIFIED, HTTP_NO_CONTENT):
        # See paste.lint: these code don't have content
        start_response(
            status, [("Content-Length", "0"), ("Date", get_rfc1123_time())] + headers
        )
        return [b""]

    if e in (HTTP_OK, HTTP_CREATED):
        e = DAVError(e)
    assert isinstance(e, DAVError)

    content_type, body = e.get_response_page()
    if is_head:
        body = compat.b_empty

    assert compat.is_bytes(body), body  # If not, Content-Length is wrong!
    start_response(
        status,
        [
            ("Content-Type", content_type),
            ("Date", get_rfc1123_time()),
            ("Content-Length", str(len(body))),
        ]
        + headers,
    )
    return [body]


def send_multi_status_response(environ, start_response, multistatusEL):
    # If logging of the body is desired, then this is the place to do it
    # pretty:
    if environ.get("wsgidav.dump_response_body"):
        xml = "{} XML response body:\n{}".format(
            environ["REQUEST_METHOD"],
            compat.to_native(xml_to_bytes(multistatusEL, pretty_print=True)),
        )
        environ["wsgidav.dump_response_body"] = xml

    # Hotfix for Windows XP
    # PROPFIND XML response is not recognized, when pretty_print = True!
    # (Vista and others would accept this).
    xml_data = xml_to_bytes(multistatusEL, pretty_print=False)
    # If not, Content-Length is wrong!
    assert compat.is_bytes(xml_data), xml_data

    headers = [
        ("Content-Type", "application/xml"),
        ("Date", get_rfc1123_time()),
        ("Content-Length", str(len(xml_data))),
    ]

    #    if 'keep-alive' in environ.get('HTTP_CONNECTION', '').lower():
    #        headers += [
    #            ('Connection', 'keep-alive'),
    #        ]

    start_response("207 Multi-Status", headers)
    return [xml_data]


def add_property_response(multistatusEL, href, propList):
    """Append <response> element to <multistatus> element.

    <prop> node depends on the value type:
      - str or unicode: add element with this content
      - None: add an empty element
      - etree.Element: add XML element as child
      - DAVError: add an empty element to an own <propstatus> for this status code

    @param multistatusEL: etree.Element
    @param href: global URL of the resource, e.g. 'http://server:port/path'.
    @param propList: list of 2-tuples (name, value)
    """
    # Split propList by status code and build a unique list of namespaces
    nsCount = 1
    nsDict = {}
    nsMap = {}
    propDict = {}

    for name, value in propList:
        status = "200 OK"
        if isinstance(value, DAVError):
            status = get_http_status_string(value)
            # Always generate *empty* elements for props with error status
            value = None

        # Collect namespaces, so we can declare them in the <response> for
        # compacter output
        ns, _ = split_namespace(name)
        if ns != "DAV:" and ns not in nsDict and ns != "":
            nsDict[ns] = True
            nsMap["NS{}".format(nsCount)] = ns
            nsCount += 1

        propDict.setdefault(status, []).append((name, value))

    # <response>
    responseEL = make_sub_element(multistatusEL, "{DAV:}response", nsmap=nsMap)

    #    log("href value:{}".format(string_repr(href)))
    #    etree.SubElement(responseEL, "{DAV:}href").text = toUnicode(href)
    etree.SubElement(responseEL, "{DAV:}href").text = href
    #    etree.SubElement(responseEL, "{DAV:}href").text = compat.quote(href, safe="/" + "!*'(),"
    #       + "$-_|.")

    # One <propstat> per status code
    for status in propDict:
        propstatEL = etree.SubElement(responseEL, "{DAV:}propstat")
        # List of <prop>
        propEL = etree.SubElement(propstatEL, "{DAV:}prop")
        for name, value in propDict[status]:
            if value is None:
                etree.SubElement(propEL, name)
            elif is_etree_element(value):
                propEL.append(value)
            else:
                # value must be string or unicode
                #                log("{} value:{}".format(name, string_repr(value)))
                #                etree.SubElement(propEL, name).text = value
                etree.SubElement(propEL, name).text = to_unicode_safe(value)
        # <status>
        etree.SubElement(propstatEL, "{DAV:}status").text = "HTTP/1.1 {}".format(status)


# ========================================================================
# ETags
# ========================================================================


def calc_hexdigest(s):
    """Return md5 digest for a string."""
    s = compat.to_bytes(s)
    return md5(s).hexdigest()  # return native string


def calc_base64(s):
    """Return base64 encoded binarystring."""
    s = compat.to_bytes(s)
    s = compat.base64_encodebytes(s).strip()  # return bytestring
    return compat.to_native(s)


def get_etag(file_path):
    """Return a strong Entity Tag for a (file)path.

    http://www.webdav.org/specs/rfc4918.html#etag

    Returns the following as entity tags::

        Non-file - md5(pathname)
        Win32 - md5(pathname)-lastmodifiedtime-filesize
        Others - inode-lastmodifiedtime-filesize
    """
    # (At least on Vista) os.path.exists returns False, if a file name contains
    # special characters, even if it is correctly UTF-8 encoded.
    # So we convert to unicode. On the other hand, md5() needs a byte string.
    if compat.is_bytes(file_path):
        unicodeFilePath = to_unicode_safe(file_path)
    else:
        unicodeFilePath = file_path
        file_path = file_path.encode("utf8")

    if not os.path.isfile(unicodeFilePath):
        return md5(file_path).hexdigest()

    if sys.platform == "win32":
        statresults = os.stat(unicodeFilePath)
        return (
            md5(file_path).hexdigest()
            + "-"
            + str(statresults[stat.ST_MTIME])
            + "-"
            + str(statresults[stat.ST_SIZE])
        )
    else:
        statresults = os.stat(unicodeFilePath)
        return (
            str(statresults[stat.ST_INO])
            + "-"
            + str(statresults[stat.ST_MTIME])
            + "-"
            + str(statresults[stat.ST_SIZE])
        )


# ========================================================================
# Ranges
# ========================================================================

# Range Specifiers
reByteRangeSpecifier = re.compile("(([0-9]+)-([0-9]*))")
reSuffixByteRangeSpecifier = re.compile("(-([0-9]+))")
# reByteRangeSpecifier = re.compile("(([0-9]+)\-([0-9]*))")
# reSuffixByteRangeSpecifier = re.compile("(\-([0-9]+))")


def obtain_content_ranges(rangetext, filesize):
    """
   returns tuple (list, value)

   list
       content ranges as values to their parsed components in the tuple
       (seek_position/abs position of first byte, abs position of last byte, num_of_bytes_to_read)
   value
       total length for Content-Length
   """
    listReturn = []
    seqRanges = rangetext.split(",")
    for subrange in seqRanges:
        matched = False
        if not matched:
            mObj = reByteRangeSpecifier.search(subrange)
            if mObj:
                firstpos = int(mObj.group(2))
                if mObj.group(3) == "":
                    lastpos = filesize - 1
                else:
                    lastpos = int(mObj.group(3))
                if firstpos <= lastpos and firstpos < filesize:
                    if lastpos >= filesize:
                        lastpos = filesize - 1
                    listReturn.append((firstpos, lastpos))
                    matched = True
        if not matched:
            mObj = reSuffixByteRangeSpecifier.search(subrange)
            if mObj:
                firstpos = filesize - int(mObj.group(2))
                if firstpos < 0:
                    firstpos = 0
                lastpos = filesize - 1
                listReturn.append((firstpos, lastpos))

                matched = True

    # consolidate ranges
    listReturn.sort()
    listReturn2 = []
    totallength = 0
    while len(listReturn) > 0:
        (rfirstpos, rlastpos) = listReturn.pop()
        counter = len(listReturn)
        while counter > 0:
            (nfirstpos, nlastpos) = listReturn[counter - 1]
            if nlastpos < rfirstpos - 1 or nfirstpos > nlastpos + 1:
                pass
            else:
                rfirstpos = min(rfirstpos, nfirstpos)
                rlastpos = max(rlastpos, nlastpos)
                del listReturn[counter - 1]
            counter = counter - 1
        listReturn2.append((rfirstpos, rlastpos, rlastpos - rfirstpos + 1))
        totallength = totallength + rlastpos - rfirstpos + 1

    return (listReturn2, totallength)


# ========================================================================
#
# ========================================================================

#: any numofsecs above the following limit is regarded as infinite
MAX_FINITE_TIMEOUT_LIMIT = 10 * 365 * 24 * 60 * 60  # approx 10 years
reSecondsReader = re.compile(r"second\-([0-9]+)", re.I)


def read_timeout_value_header(timeoutvalue):
    """Return -1 if infinite, else return numofsecs."""
    timeoutsecs = 0
    timeoutvaluelist = timeoutvalue.split(",")
    for timeoutspec in timeoutvaluelist:
        timeoutspec = timeoutspec.strip()
        if timeoutspec.lower() == "infinite":
            return -1
        else:
            listSR = reSecondsReader.findall(timeoutspec)
            for secs in listSR:
                timeoutsecs = int(secs)
                if timeoutsecs > MAX_FINITE_TIMEOUT_LIMIT:
                    return -1
                if timeoutsecs != 0:
                    return timeoutsecs
    return None


# ========================================================================
# If Headers
# ========================================================================


def evaluate_http_conditionals(dav_res, last_modified, entitytag, environ):
    """Handle 'If-...:' headers (but not 'If:' header).

    If-Match
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.24
        Only perform the action if the client supplied entity matches the
        same entity on the server. This is mainly for methods like
        PUT to only update a resource if it has not been modified since the
        user last updated it.
        If-Match: "737060cd8c284d8af7ad3082f209582d"
    If-Modified-Since
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.25
        Allows a 304 Not Modified to be returned if content is unchanged
        If-Modified-Since: Sat, 29 Oct 1994 19:43:31 GMT
    If-None-Match
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.26
        Allows a 304 Not Modified to be returned if content is unchanged,
        see HTTP ETag
        If-None-Match: "737060cd8c284d8af7ad3082f209582d"
    If-Unmodified-Since
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.28
        Only send the response if the entity has not been modified since a
        specific time.
    """
    if not dav_res:
        return
    # Conditions

    # An HTTP/1.1 origin server, upon receiving a conditional request that includes both a
    # Last-Modified date (e.g., in an If-Modified-Since or If-Unmodified-Since header field) and
    # one or more entity tags (e.g., in an If-Match, If-None-Match, or If-Range header field) as
    # cache validators, MUST NOT return a response status of 304 (Not Modified) unless doing so
    # is consistent with all of the conditional header fields in the request.

    if "HTTP_IF_MATCH" in environ and dav_res.support_etag():
        ifmatchlist = environ["HTTP_IF_MATCH"].split(",")
        for ifmatchtag in ifmatchlist:
            ifmatchtag = ifmatchtag.strip(' "\t')
            if ifmatchtag == entitytag or ifmatchtag == "*":
                break
            raise DAVError(HTTP_PRECONDITION_FAILED, "If-Match header condition failed")

    # TODO: after the refactoring
    ifModifiedSinceFailed = False
    if "HTTP_IF_MODIFIED_SINCE" in environ and dav_res.support_modified():
        ifmodtime = parse_time_string(environ["HTTP_IF_MODIFIED_SINCE"])
        if ifmodtime and ifmodtime > last_modified:
            ifModifiedSinceFailed = True

    # If-None-Match
    # If none of the entity tags match, then the server MAY perform the requested method as if the
    # If-None-Match header field did not exist, but MUST also ignore any If-Modified-Since header
    # field (s) in the request. That is, if no entity tags match, then the server MUST NOT return
    # a 304 (Not Modified) response.
    ignoreIfModifiedSince = False
    if "HTTP_IF_NONE_MATCH" in environ and dav_res.support_etag():
        ifmatchlist = environ["HTTP_IF_NONE_MATCH"].split(",")
        for ifmatchtag in ifmatchlist:
            ifmatchtag = ifmatchtag.strip(' "\t')
            if ifmatchtag == entitytag or ifmatchtag == "*":
                # ETag matched. If it's a GET request and we don't have an
                # conflicting If-Modified header, we return NOT_MODIFIED
                if (
                    environ["REQUEST_METHOD"] in ("GET", "HEAD")
                    and not ifModifiedSinceFailed
                ):
                    raise DAVError(HTTP_NOT_MODIFIED, "If-None-Match header failed")
                raise DAVError(
                    HTTP_PRECONDITION_FAILED, "If-None-Match header condition failed"
                )
        ignoreIfModifiedSince = True

    if "HTTP_IF_UNMODIFIED_SINCE" in environ and dav_res.support_modified():
        ifunmodtime = parse_time_string(environ["HTTP_IF_UNMODIFIED_SINCE"])
        if ifunmodtime and ifunmodtime < last_modified:
            raise DAVError(
                HTTP_PRECONDITION_FAILED, "If-Unmodified-Since header condition failed"
            )

    if ifModifiedSinceFailed and not ignoreIfModifiedSince:
        raise DAVError(HTTP_NOT_MODIFIED, "If-Modified-Since header condition failed")

    return


reIfSeparator = re.compile(r"(\<([^>]+)\>)|(\(([^\)]+)\))")
reIfHeader = re.compile(r"\<([^>]+)\>([^<]+)")
reIfTagList = re.compile(r"\(([^)]+)\)")
reIfTagListContents = re.compile(r"(\S+)")


def parse_if_header_dict(environ):
    """Parse HTTP_IF header into a dictionary and lists, and cache the result.

    @see http://www.webdav.org/specs/rfc4918.html#HEADER_If
    """
    if "wsgidav.conditions.if" in environ:
        return

    if "HTTP_IF" not in environ:
        environ["wsgidav.conditions.if"] = None
        environ["wsgidav.ifLockTokenList"] = []
        return

    iftext = environ["HTTP_IF"].strip()
    if not iftext.startswith("<"):
        iftext = "<*>" + iftext

    ifDict = dict([])
    ifLockList = []

    resource1 = "*"
    for (tmpURLVar, URLVar, _tmpContentVar, contentVar) in reIfSeparator.findall(
        iftext
    ):
        if tmpURLVar != "":
            resource1 = URLVar
        else:
            listTagContents = []
            testflag = True
            for listitem in reIfTagListContents.findall(contentVar):
                if listitem.upper() != "NOT":
                    if listitem.startswith("["):
                        listTagContents.append(
                            (testflag, "entity", listitem.strip('"[]'))
                        )
                    else:
                        listTagContents.append(
                            (testflag, "locktoken", listitem.strip("<>"))
                        )
                        ifLockList.append(listitem.strip("<>"))
                testflag = listitem.upper() != "NOT"

            if resource1 in ifDict:
                listTag = ifDict[resource1]
            else:
                listTag = []
                ifDict[resource1] = listTag
            listTag.append(listTagContents)

    environ["wsgidav.conditions.if"] = ifDict
    environ["wsgidav.ifLockTokenList"] = ifLockList
    _logger.debug("parse_if_header_dict\n{}".format(pformat(ifDict)))
    return


def test_if_header_dict(dav_res, dictIf, fullurl, locktokenlist, entitytag):
    _logger.debug(
        "test_if_header_dict({}, {}, {})".format(fullurl, locktokenlist, entitytag)
    )

    if fullurl in dictIf:
        listTest = dictIf[fullurl]
    elif "*" in dictIf:
        listTest = dictIf["*"]
    else:
        return True

    #    supportEntityTag = dav.isInfoTypeSupported(path, "etag")
    supportEntityTag = dav_res.support_etag()
    for listTestConds in listTest:
        matchfailed = False

        for (testflag, checkstyle, checkvalue) in listTestConds:
            if checkstyle == "entity" and supportEntityTag:
                testresult = entitytag == checkvalue
            elif checkstyle == "entity":
                testresult = testflag
            elif checkstyle == "locktoken":
                testresult = checkvalue in locktokenlist
            else:  # unknown
                testresult = True
            checkresult = testresult == testflag
            if not checkresult:
                matchfailed = True
                break
        if not matchfailed:
            return True
    _logger.debug("  -> FAILED")
    return False


test_if_header_dict.__test__ = False  # Tell nose to ignore this function


# ========================================================================
# guess_mime_type
# ========================================================================
_MIME_TYPES = {
    ".oga": "audio/ogg",
    ".ogg": "audio/ogg",
    ".ogv": "video/ogg",
    ".webm": "video/webm",
}


def guess_mime_type(url):
    """Use the mimetypes module to lookup the type for an extension.

    This function also adds some extensions required for HTML5
    """
    (mimetype, _mimeencoding) = mimetypes.guess_type(url)
    if not mimetype:
        ext = os.path.splitext(url)[1]
        mimetype = _MIME_TYPES.get(ext)
        _logger.debug("mimetype({}): {}".format(url, mimetype))
    if not mimetype:
        mimetype = "application/octet-stream"
    return mimetype
