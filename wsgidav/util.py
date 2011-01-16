# (c) 2009-2011 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Miscellaneous support functions for WsgiDAV.

See `Developers info`_ for more information about the WsgiDAV architecture.

.. _`Developers info`: http://docs.wsgidav.googlecode.com/hg/html/develop.html  
"""
from pprint import pformat
from wsgidav.dav_error import DAVError, HTTP_PRECONDITION_FAILED, HTTP_NOT_MODIFIED,\
    HTTP_NO_CONTENT, HTTP_CREATED, getHttpStatusString, HTTP_BAD_REQUEST,\
    HTTP_OK
from wsgidav.xml_tools import xmlToString, makeSubElement
import urllib
import socket


import locale
import logging
import re
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import os
import calendar
import sys
import time
import stat

try:
    from email.utils import formatdate, parsedate
except ImportError, e:
    # Python < 2.5
    from email.Utils import formatdate, parsedate

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO #@UnusedImport

#import xml_tools
## Trick PyDev to do intellisense and don't produce warnings:
from xml_tools import etree #@UnusedImport
if False: from xml.etree import ElementTree as etree     #@Reimport @UnresolvedImport

__docformat__ = "reStructuredText"

BASE_LOGGER_NAME = "wsgidav"
_logger = logging.getLogger(BASE_LOGGER_NAME)
# Pre-initialize, so we get some output before initLogging() was called
# (for example during parsing of wsgidav.conf)
logging.basicConfig(level=logging.INFO)


#===============================================================================
# String handling
#===============================================================================

def getRfc1123Time(secs=None):   
    """Return <secs> in rfc 1123 date/time format (pass secs=None for current date)."""
    # issue #20: time string must be locale independent
#    return time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(secs))
    return formatdate(timeval=secs, localtime=False, usegmt=True)


def getRfc3339Time(secs=None):   
    """Return <secs> in RFC 3339 date/time format (pass secs=None for current date).
    
    RFC 3339 is a subset of ISO 8601, used for '{DAV:}creationdate'. 
    See http://tools.ietf.org/html/rfc3339
    """
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(secs))


def getLogTime(secs=None):   
    """Return <secs> in log time format (pass secs=None for current date)."""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(secs))


def parseTimeString(timestring):
    """Return the number of seconds since the epoch, for a date/time string.
  
    Returns None for invalid input

    The following time type strings are supported:

    Sun, 06 Nov 1994 08:49:37 GMT  ; RFC 822, updated by RFC 1123
    Sunday, 06-Nov-94 08:49:37 GMT ; RFC 850, obsoleted by RFC 1036
    Sun Nov  6 08:49:37 1994       ; ANSI C's asctime() format  
    """
    result = _parsegmtime(timestring)
    if result:
        return calendar.timegm(result)
    return None


def _parsegmtime(timestring):
    """Return a standard time tuple (see time and calendar), for a date/time string."""
    # Sun, 06 Nov 1994 08:49:37 GMT  ; RFC 822, updated by RFC 1123
    try:
        return time.strptime(timestring, "%a, %d %b %Y %H:%M:%S GMT")   
    except:
        pass

    # Sunday, 06-Nov-94 08:49:37 GMT ; RFC 850, obsoleted by RFC 1036
    try:
        return time.strptime(timestring, "%A %d-%b-%y %H:%M:%S GMT")
    except:
        pass   

    # Sun Nov  6 08:49:37 1994       ; ANSI C's asctime() format  
    try:
        return time.strptime(timestring, "%a %b %d %H:%M:%S %Y")
    except:
        pass

    # Sun Nov  6 08:49:37 1994 +0100      ; ANSI C's asctime() format with timezon  
    try:
        return parsedate(timestring)
    except:
        pass

    return None


#===============================================================================
# Logging
#===============================================================================

def initLogging(verbose=2, enable_loggers=[]):
    """Initialize base logger named 'wsgidav'.

    The base logger is filtered by the `verbose` configuration option.
    Log entries will have a time stamp and thread id.
    
    :Parameters:
        verbose : int
            Verbosity configuration (0..3) 
        enable_loggers : string list
            List of module logger names, that will be switched to DEBUG level.
         
    Module loggers
    ~~~~~~~~~~~~~~
    Module loggers (e.g 'wsgidav.lock_manager') are named loggers, that can be
    independently switched to DEBUG mode.
    
    Except for verbosity, they will inherit settings from the base logger.

    They will suppress DEBUG level messages, unless they are enabled by passing 
    their name to util.initLogging().

    If enabled, module loggers will print DEBUG messages, even if verbose == 2.   
    
    Example initialize and use a module logger, that will generate output, 
    if enabled (and verbose >= 2):
        
    .. python::
        _logger = util.getModuleLogger(__name__)
        [..]
        _logger.debug("foo: '%s'" % s)

    This logger would be enabled by passing its name to initLoggiong():
    
    .. python::
        enable_loggers = ["lock_manager",
                          "property_manager",
                         ]
        util.initLogging(2, enable_loggers)

    
    Log level matrix
    ~~~~~~~~~~~~~~~~
    =======  ======  ===========  ======================  =======================
    verbose  util                        Log level 
    -------  ------  ------------------------------------------------------------
      n      ()      base logger  module logger(enabled)  module logger(disabled)
    =======  ======  ===========  ======================  =======================
      0      write   ERROR        ERROR                   ERROR
      1      status  WARN         WARN                    WARN
      2      note    INFO         DEBUG                   INFO
      3      debug   DEBUG        DEBUG                   INFO
    =======  ======  ===========  ======================  =======================
    """

    formatter = logging.Formatter("<%(thread)d> [%(asctime)s.%(msecs)d] %(name)s:  %(message)s",
                                  "%H:%M:%S")
    
    # Define handlers
    consoleHandler = logging.StreamHandler(sys.stdout)
#    consoleHandler = logging.StreamHandler(sys.stderr)
    consoleHandler.setFormatter(formatter)
    consoleHandler.setLevel(logging.DEBUG)

    # Add the handlers to the base logger
    logger = logging.getLogger(BASE_LOGGER_NAME)

    if verbose >= 3: # --debug
        logger.setLevel(logging.DEBUG)
    elif verbose >= 2: # --verbose
        logger.setLevel(logging.INFO)
    elif verbose >= 1: # standard 
        logger.setLevel(logging.WARN)
        consoleHandler.setLevel(logging.WARN)
    else: # --quiet
        logger.setLevel(logging.ERROR)
        consoleHandler.setLevel(logging.ERROR)

    # Don't call the root's handlers after our custom handlers
    logger.propagate = False
    
    # Remove previous handlers
    for hdlr in logger.handlers[:]:  # Must iterate an array copy
        try:
            hdlr.flush()
            hdlr.close()
        except:
            pass
        logger.removeHandler(hdlr)

    logger.addHandler(consoleHandler)

    if verbose >= 2:
        for e in enable_loggers:
            if not e.startswith(BASE_LOGGER_NAME + "."):
                e = BASE_LOGGER_NAME + "." + e
            l = logging.getLogger(e.strip())
#            if verbose >= 2:
#                log("Logger(%s).setLevel(DEBUG)" % e.strip())
            l.setLevel(logging.DEBUG)        


  
def getModuleLogger(moduleName, defaultToVerbose=False):
    """Create a module logger, that can be en/disabled by configuration.
    
    @see: unit.initLogging
    """
#    _logger.debug("getModuleLogger(%s)" % moduleName)
    if not moduleName.startswith(BASE_LOGGER_NAME + "."):
        moduleName = BASE_LOGGER_NAME + "." + moduleName
#    assert not "." in moduleName, "Only pass the module name, without leading '%s.'." % BASE_LOGGER_NAME
#    logger = logging.getLogger("%s.%s" % (BASE_LOGGER_NAME, moduleName))
    logger = logging.getLogger(moduleName)
    if logger.level == logging.NOTSET and not defaultToVerbose:
        logger.setLevel(logging.INFO)  # Disable debug messages by default
    return logger


def log(msg, var=None):
    """Shortcut for logging.getLogger('wsgidav').info(msg)

    This message will only display, if verbose >= 2. 
    """
#    _logger.info(msg)
#    if var and logging.INFO >= _logger.getEffectiveLevel():
#        pprint(var, sys.stderr, indent=4)
    note(msg, var=var)
    

def _write(msg, var, module, level, flush):  
    if module:
        logger = logging.getLogger(BASE_LOGGER_NAME+"."+module)
        # Disable debug messages for module loggers by default
        if logger.level == logging.NOTSET:
            logger.setLevel(logging.INFO)
    else:
        logger = _logger
    logger.log(level, msg)
#    if level >= logger.getEffectiveLevel():
    if var is not None and level >= logger.getEffectiveLevel():
        logger.log(level, pformat(var, indent=4))
    if flush:
        for hdlr in logger.handlers:
            hdlr.flush()

def write(msg, var=None, module=None, flush=True):  
    """Log always."""
    _write(msg, var, module, logging.CRITICAL, flush)
def warn(msg, var=None, module=None, flush=True):
    """Log to stderr."""
    _write(msg, var, module, logging.ERROR, flush)
def status(msg, var=None, module=None, flush=True):
    """Log if not --quiet."""
    _write(msg, var, module, logging.WARNING, flush)
def note(msg, var=None, module=None, flush=True):
    """Log if --verbose."""
    _write(msg, var, module, logging.INFO, flush)
def debug(msg, var=None, module=None, flush=True):
    """Log if --debug."""
    _write(msg, var, module, logging.DEBUG, flush)


def traceCall(msg=None):
    """Return name of calling function."""
    if __debug__:
        f_code = sys._getframe(2).f_code
        if msg is None:
            msg = ": %s"
        else: msg = ""
        print "%s.%s #%s%s" % (f_code.co_filename, f_code.co_name, f_code.co_lineno, msg)


#===============================================================================
# Strings
#===============================================================================

def lstripstr(s, prefix, ignoreCase=False):
    if ignoreCase:
        if not s.lower().startswith(prefix.lower()):
            return s
    else:
        if not s.startswith(prefix):
            return s
    return s[len(prefix):]

     
def saveSplit(s, sep, maxsplit):
    """Split string, always returning n-tuple (filled with None if necessary)."""
    tok = s.split(sep, maxsplit)
    while len(tok) <= maxsplit:
        tok.append(None)
    return tok


def popPath(path):
    """Return '/a/b/c' -> ('a', '/b/c')."""
    if path in ("", "/"):
        return ("", "")
    assert path.startswith("/")
    first, _sep, rest = path.lstrip("/").partition("/")
    return (first, "/"+rest)


def popPath2(path):
    """Return '/a/b/c' -> ('a', 'b', '/c')."""
    if path in ("", "/"):
        return ("", "", "")
    first, rest = popPath(path)
    second, rest = popPath(rest)
    return (first, second, "/"+rest)


def shiftPath(scriptName, pathInfo):
    """Return ('/a', '/b/c') -> ('b', '/a/b', 'c')."""
    segment, rest = popPath(pathInfo)
    return (segment, joinUri(scriptName.rstrip("/"), segment), rest.rstrip("/"))


def splitNamespace(clarkName):
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


def toUnicode(s):
    """Convert a binary string to Unicode using UTF-8 (fallback to latin-1)."""
    if not isinstance(s, str):
        return s
    try:
        u = s.decode("utf8")
#        log("toUnicode(%r) = '%r'" % (s, u))
    except:
        log("toUnicode(%r) *** UTF-8 failed. Trying latin-1 " % s)
        u = s.decode("latin-1")
    return u


def stringRepr(s):
    """Return a string as hex dump."""
    if isinstance(s, str):
        res = "'%s': " % s
        for b in s:
            res += "%02x " % ord(b)
        return res
    return "%s" % s



def byteNumberString(number, thousandsSep=True, partition=False, base1024=True, appendBytes=True):
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
        locale.setlocale(locale.LC_ALL, "")
        # TODO: make precision configurable
        snum = locale.format("%d", number, thousandsSep)
    else:
        snum = str(number)

    return "%s%s%s" % (snum, magsuffix, bytesuffix)
    
    

#===============================================================================
# WSGI
#===============================================================================
def getContentLength(environ):
    """Return a positive CONTENT_LENGTH in a safe way (return 0 otherwise)."""
    # TODO: http://www.wsgi.org/wsgi/WSGI_2.0
    try:
        return max(0, long(environ.get("CONTENT_LENGTH", 0)))
    except ValueError:
        return 0


#def readAllInput(environ):
#    """Read and discard all from from wsgi.input, if this has not been done yet."""
#    cl = getContentLength(environ)
#    if environ.get("wsgidav.all_input_read") or cl == 0:
#        return
#    assert not environ.get("wsgidav.some_input_read")
#    write("Reading and discarding %s bytes input." % cl)
#    environ["wsgi.input"].read(cl)
#    environ["wsgidav.all_input_read"] = 1


def readAndDiscardInput(environ):
    """Read 1 byte from wsgi.input, if this has not been done yet.
    
    Returning a response without reading from a request body might confuse the 
    WebDAV client.  
    This may happen, if an exception like '401 Not authorized', or 
    '500 Internal error' was raised BEFORE anything was read from the request 
    stream.

    See issue 13, issue 23
    See http://groups.google.com/group/paste-users/browse_frm/thread/fc0c9476047e9a47?hl=en
    
    Note that with persistent sessions (HTTP/1.1) we must make sure, that the
    'Connection: closed' header is set with the response, to prevent reusing
    the current stream.
    """
    if environ.get("wsgidav.some_input_read") or environ.get("wsgidav.all_input_read"):
        return
    cl = getContentLength(environ)
    assert cl >= 0
    if cl == 0:
        return 

    READ_ALL = True
    
    environ["wsgidav.some_input_read"] = 1
    if READ_ALL:
        environ["wsgidav.all_input_read"] = 1
        
    
    wsgi_input = environ["wsgi.input"]

    # TODO: check if still required after issue 24 is fixed 
    if hasattr(wsgi_input, "_consumed") and hasattr(wsgi_input, "length"): 
        # Seems to be Paste's httpserver.LimitedLengthFile
        # see http://groups.google.com/group/paste-users/browse_thread/thread/fc0c9476047e9a47/aa4a3aa416016729?hl=en&lnk=gst&q=.input#aa4a3aa416016729
        # Consume something if nothing was consumed *and* work
        # around a bug where paste.httpserver allows negative lengths
        if wsgi_input._consumed == 0 and wsgi_input.length > 0:
            # This seems to work even if there's 10K of input.
            if READ_ALL:
                n = wsgi_input.length
            else:
                n = 1
            body = wsgi_input.read(n) 
            debug("Reading %s bytes from potentially unread httpserver.LimitedLengthFile: '%s'..." % (n, body[:50]))

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
                debug("Reading %s bytes from potentially unread POST body: '%s'..." % (n, body[:50]))
            except socket.error, se:
                # se(10035, 'The socket operation could not complete without blocking')
                warn("-> read %s bytes failed: %s" % (n, se))
            # Restore socket settings
            sock.settimeout(timeout)
        except:
            warn("--> wsgi_input.read(): %s" % sys.exc_info())



#===============================================================================
# URLs
#===============================================================================

def joinUri(uri, *segments):
    """Append segments to URI.
    
    Example: joinUri("/a/b", "c", "d")
    """
    sub = "/".join(segments)
    if not sub:
        return uri
    return uri.rstrip("/") + "/" + sub


def getUriName(uri):
    """Return local name, i.e. last segment of URI."""
    return uri.strip("/").split("/")[-1]
    

def getUriParent(uri):
    """Return URI of parent collection with trailing '/', or None, if URI is top-level.
    
    This function simply strips the last segment. It does not test, if the
    target is a 'collection', or even exists.
    """
    if not uri or uri.strip() == "/":
        return None
    return uri.rstrip("/").rsplit("/", 1)[0] + "/"


def isChildUri(parentUri, childUri):
    """Return True, if childUri is a child of parentUri.
    
    This function accounts for the fact that '/a/b/c' and 'a/b/c/' are
    children of '/a/b' (and also of '/a/b/').
    Note that '/a/b/cd' is NOT a child of 'a/b/c'. 
    """
    return parentUri and childUri and childUri.rstrip("/").startswith(parentUri.rstrip("/")+"/")


def isEqualOrChildUri(parentUri, childUri):
    """Return True, if childUri is a child of parentUri or maps to the same resource.
    
    Similar to <util.isChildUri>_ ,  but this method also returns True, if parent
    equals child. ('/a/b' is considered identical with '/a/b/').
    """
    return parentUri and childUri and (childUri.rstrip("/")+"/").startswith(parentUri.rstrip("/")+"/")


def makeCompleteUrl(environ, localUri=None):
    """URL reconstruction according to PEP 333.
    @see http://www.python.org/dev/peps/pep-0333/#id33
    """
    url = environ["wsgi.url_scheme"]+"://"
    
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
    
    url += urllib.quote(environ.get("SCRIPT_NAME",""))

    if localUri is None:
        url += urllib.quote(environ.get("PATH_INFO",""))
        if environ.get("QUERY_STRING"):
            url += "?" + environ["QUERY_STRING"]
    else:
        url += localUri # TODO: quote?
    return url


#===============================================================================
# XML
#===============================================================================

def parseXmlBody(environ, allowEmpty=False):
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
#    contentLength = -1 # read all of stream
    if clHeader == "":
        # No Content-Length given: read to end of stream 
        # TODO: etree.parse() locks, if input is invalid?
#        pfroot = etree.parse(environ["wsgi.input"]).getroot()
#        requestbody = environ["wsgi.input"].read()  # TODO: read() should be called in a loop?
        requestbody = ""
    else:
        try:
            contentLength = long(clHeader)
            if contentLength < 0:   
                raise DAVError(HTTP_BAD_REQUEST, "Negative content-length.")
        except ValueError:
            raise DAVError(HTTP_BAD_REQUEST, "content-length is not numeric.")
        
        if contentLength == 0:
            requestbody = ""
        else:
            requestbody = environ["wsgi.input"].read(contentLength)
            environ["wsgidav.all_input_read"] = 1

    if requestbody == "":
        if allowEmpty:
            return None
        else:
            raise DAVError(HTTP_BAD_REQUEST, "Body must not be empty.")
    
    try:
        rootEL = etree.fromstring(requestbody)
    except Exception, e:
        raise DAVError(HTTP_BAD_REQUEST, "Invalid XML format.", srcexception=e)   
    
    # If dumps of the body are desired, then this is the place to do it pretty:
    if environ.get("wsgidav.dump_request_body"):
        write("%s XML request body:\n%s" % (environ["REQUEST_METHOD"], 
                                            xmlToString(rootEL, pretty_print=True)))
        environ["wsgidav.dump_request_body"] = False

    return rootEL
    

#def sendResponse(environ, start_response, body, content_type):
#    """Send a WSGI response for a HTML or XML string.""" 
#    assert content_type in ("application/xml", "text/html")
#
#    start_response(status, [("Content-Type", content_type), 
#                            ("Date", getRfc1123Time()),
#                            ("Content-Length", str(len(body))),
#                            ]) 
#    return [ body ]
    
    
def sendStatusResponse(environ, start_response, e):
    """Start a WSGI response for a DAVError or status code.""" 
    status = getHttpStatusString(e)
    headers = [] 
#    if 'keep-alive' in environ.get('HTTP_CONNECTION', '').lower():
#        headers += [
#            ('Connection', 'keep-alive'),
#        ]

    if e in (HTTP_NOT_MODIFIED, HTTP_NO_CONTENT):
        # See paste.lint: these code don't have content
        start_response(status, [("Content-Length", "0"),
                                ("Date", getRfc1123Time()),
                                ] + headers)
        return [ "" ]
    
    if e in (HTTP_OK, HTTP_CREATED):
        e = DAVError(e)
    assert isinstance(e, DAVError)
    
    content_type, body = e.getResponsePage()            

    start_response(status, [("Content-Type", content_type), 
                            ("Date", getRfc1123Time()),
                            ("Content-Length", str(len(body))),
                            ] + headers) 
    assert type(body) is str # If not, Content-Length is wrong!
    return [ body ]
    
    
def sendMultiStatusResponse(environ, start_response, multistatusEL):
    # If logging of the body is desired, then this is the place to do it pretty:
    if environ.get("wsgidav.dump_response_body"):
        xml = "%s XML response body:\n%s" % (environ["REQUEST_METHOD"],
                                             xmlToString(multistatusEL, pretty_print=True)) 
        environ["wsgidav.dump_response_body"] = xml 
        
    # Hotfix for Windows XP 
    # PROPFIND XML response is not recognized, when pretty_print = True!
    # (Vista and others would accept this).
    xml_data = xmlToString(multistatusEL, pretty_print=False)
    
    headers = [
        ("Content-Type", "application/xml"),
        ("Date", getRfc1123Time()),
        ('Content-Length', str(len(xml_data))),
    ]

#    if 'keep-alive' in environ.get('HTTP_CONNECTION', '').lower():
#        headers += [
#            ('Connection', 'keep-alive'),
#        ]

    start_response("207 Multistatus", headers)
    assert type(xml_data) is str # If not, Content-Length is wrong!
    return [ xml_data ]
        
            
def addPropertyResponse(multistatusEL, href, propList):
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
            status = getHttpStatusString(value)
            # Always generate *empty* elements for props with error status
            value = None

        # Collect namespaces, so we can declare them in the <response> for 
        # compacter output
        ns, _ = splitNamespace(name)
        if ns!="DAV:" and not ns in nsDict and ns != "":
            nsDict[ns] = True
            nsMap["NS%s" % nsCount] = ns
            nsCount += 1

        propDict.setdefault(status, []).append( (name, value) )

    # <response>
    responseEL = makeSubElement(multistatusEL, "{DAV:}response", nsmap=nsMap) 
    
#    log("href value:%s" % (stringRepr(href)))
#    etree.SubElement(responseEL, "{DAV:}href").text = toUnicode(href)
    etree.SubElement(responseEL, "{DAV:}href").text = href
#    etree.SubElement(responseEL, "{DAV:}href").text = urllib.quote(href, safe="/" + "!*'()," + "$-_|.")
    
    
    # One <propstat> per status code
    for status in propDict:
        propstatEL = etree.SubElement(responseEL, "{DAV:}propstat")
        # List of <prop>
        propEL = etree.SubElement(propstatEL, "{DAV:}prop")
        for name, value in propDict[status]:
            if value is None:
                etree.SubElement(propEL, name)
            elif isinstance(value, etree._Element):
                propEL.append(value)
            else:
                # value must be string or unicode
#                log("%s value:%s" % (name, stringRepr(value)))
#                etree.SubElement(propEL, name).text = value
                etree.SubElement(propEL, name).text = toUnicode(value)
        # <status>
        etree.SubElement(propstatEL, "{DAV:}status").text = "HTTP/1.1 %s" % status
    

#===============================================================================
# ETags
#===============================================================================
def getETag(filePath):
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
    if isinstance(filePath, unicode):
        unicodeFilePath = filePath
        filePath = filePath.encode("utf8")
    else:
        unicodeFilePath = toUnicode(filePath)
        
    if not os.path.isfile(unicodeFilePath):
        return md5(filePath).hexdigest()   
    if sys.platform == "win32":
        statresults = os.stat(unicodeFilePath)
        return md5(filePath).hexdigest() + "-" + str(statresults[stat.ST_MTIME]) + "-" + str(statresults[stat.ST_SIZE])
    else:
        statresults = os.stat(unicodeFilePath)
        return str(statresults[stat.ST_INO]) + "-" + str(statresults[stat.ST_MTIME]) + "-" + str(statresults[stat.ST_SIZE])


#===============================================================================
# Ranges     
#===============================================================================

# Range Specifiers
reByteRangeSpecifier = re.compile("(([0-9]+)\-([0-9]*))")
reSuffixByteRangeSpecifier = re.compile("(\-([0-9]+))")

def obtainContentRanges(rangetext, filesize):
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
#                print mObj.group(0), mObj.group(1), mObj.group(2), mObj.group(3)  
                firstpos = long(mObj.group(2))
                if mObj.group(3) == "":
                    lastpos = filesize - 1
                else:
                    lastpos = long(mObj.group(3))
                if firstpos <= lastpos and firstpos < filesize:
                    if lastpos >= filesize:
                        lastpos = filesize - 1
                    listReturn.append( (firstpos , lastpos) )
                    matched = True
        if not matched:      
            mObj = reSuffixByteRangeSpecifier.search(subrange)
            if mObj:
                firstpos = filesize - long(mObj.group(2))
                if firstpos < 0:
                    firstpos = 0
                lastpos = filesize - 1
                listReturn.append( (firstpos , lastpos) )

                matched = True

    # consolidate ranges
    listReturn.sort()
    listReturn2 = []
    totallength = 0
    while(len(listReturn) > 0):
        (rfirstpos, rlastpos) = listReturn.pop()
        counter = len(listReturn)
        while counter > 0:
            (nfirstpos, nlastpos) = listReturn[counter-1]
            if nlastpos < rfirstpos - 1 or nfirstpos > nlastpos + 1:
                pass
            else: 
                rfirstpos = min(rfirstpos, nfirstpos)
                rlastpos = max(rlastpos, nlastpos)
                del listReturn[counter-1]
            counter = counter - 1
        listReturn2.append((rfirstpos,rlastpos,rlastpos - rfirstpos + 1 ))            
        totallength = totallength + rlastpos - rfirstpos + 1

    return (listReturn2, totallength)

#===============================================================================
# 
#===============================================================================
# any numofsecs above the following limit is regarded as infinite
MAX_FINITE_TIMEOUT_LIMIT = 10*365*24*60*60  #approx 10 years
reSecondsReader = re.compile(r'second\-([0-9]+)', re.I)

def readTimeoutValueHeader(timeoutvalue):
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
                timeoutsecs = long(secs)
                if timeoutsecs > MAX_FINITE_TIMEOUT_LIMIT:
                    return -1          
                if timeoutsecs != 0:
                    return timeoutsecs
    return None


#===============================================================================
# If Headers
#===============================================================================

def evaluateHTTPConditionals(davres, lastmodified, entitytag, environ):
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
    if not davres:
        return
    ## Conditions

    # An HTTP/1.1 origin server, upon receiving a conditional request that includes both a Last-Modified date
    # (e.g., in an If-Modified-Since or If-Unmodified-Since header field) and one or more entity tags (e.g., 
    # in an If-Match, If-None-Match, or If-Range header field) as cache validators, MUST NOT return a response 
    # status of 304 (Not Modified) unless doing so is consistent with all of the conditional header fields in 
    # the request.
    
    if "HTTP_IF_MATCH" in environ and davres.supportEtag(): 
        ifmatchlist = environ["HTTP_IF_MATCH"].split(",")
        for ifmatchtag in ifmatchlist:
            ifmatchtag = ifmatchtag.strip(" \"\t")
            if ifmatchtag == entitytag or ifmatchtag == "*":
                break   
            raise DAVError(HTTP_PRECONDITION_FAILED,
                           "If-Match header condition failed")

    # TODO: after the refactoring
    ifModifiedSinceFailed = False
    if "HTTP_IF_MODIFIED_SINCE" in environ and davres.supportModified(): 
        ifmodtime = parseTimeString(environ["HTTP_IF_MODIFIED_SINCE"])
        if ifmodtime and ifmodtime > lastmodified:
            ifModifiedSinceFailed = True

    # If-None-Match 
    # If none of the entity tags match, then the server MAY perform the requested method as if the 
    # If-None-Match header field did not exist, but MUST also ignore any If-Modified-Since header field
    # (s) in the request. That is, if no entity tags match, then the server MUST NOT return a 304 (Not Modified) 
    # response.
    ignoreIfModifiedSince = False         
    if "HTTP_IF_NONE_MATCH" in environ and davres.supportEtag():          
        ifmatchlist = environ["HTTP_IF_NONE_MATCH"].split(",")
        for ifmatchtag in ifmatchlist:
            ifmatchtag = ifmatchtag.strip(" \"\t")
            if ifmatchtag == entitytag or ifmatchtag == "*":
                # ETag matched. If it's a GET request and we don't have an 
                # conflicting If-Modified header, we return NOT_MODIFIED
                if environ["REQUEST_METHOD"] in ("GET", "HEAD") and not ifModifiedSinceFailed:
                    raise DAVError(HTTP_NOT_MODIFIED,
                                   "If-None-Match header failed")
                raise DAVError(HTTP_PRECONDITION_FAILED,
                               "If-None-Match header condition failed")
        ignoreIfModifiedSince = True

    if "HTTP_IF_UNMODIFIED_SINCE" in environ and davres.supportModified(): 
        ifunmodtime = parseTimeString(environ["HTTP_IF_UNMODIFIED_SINCE"])
        if ifunmodtime and ifunmodtime <= lastmodified:
            raise DAVError(HTTP_PRECONDITION_FAILED,
                           "If-Unmodified-Since header condition failed")

    if ifModifiedSinceFailed and not ignoreIfModifiedSince:
        raise DAVError(HTTP_NOT_MODIFIED,
                       "If-Modified-Since header condition failed")

    return




reIfSeparator = re.compile(r'(\<([^>]+)\>)|(\(([^\)]+)\))')
reIfHeader = re.compile(r'\<([^>]+)\>([^<]+)')
reIfTagList = re.compile(r'\(([^)]+)\)')
reIfTagListContents = re.compile(r'(\S+)')


def parseIfHeaderDict(environ):
    """Parse HTTP_IF header into a dictionary and lists, and cache the result.
    
    @see http://www.webdav.org/specs/rfc4918.html#HEADER_If
    """
    if "wsgidav.conditions.if" in environ:
        return

    if not "HTTP_IF" in environ:
        environ["wsgidav.conditions.if"] = None
        environ["wsgidav.ifLockTokenList"] = []
        return
    
    iftext = environ["HTTP_IF"].strip()
    if not iftext.startswith("<"):
        iftext = "<*>" + iftext   

    ifDict = dict([])
    ifLockList = []
    
    resource1 = "*"
    for (tmpURLVar, URLVar, _tmpContentVar, contentVar) in reIfSeparator.findall(iftext):
        if tmpURLVar != "":
            resource1 = URLVar         
        else:
            listTagContents = []
            testflag = True
            for listitem in reIfTagListContents.findall(contentVar):            
                if listitem.upper() != "NOT":
                    if listitem.startswith("["):
                        listTagContents.append((testflag,"entity",listitem.strip('\"[]')))   
                    else:
                        listTagContents.append((testflag,"locktoken",listitem.strip("<>")))            
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
    debug("parseIfHeaderDict", var=ifDict, module="if")
    return


def testIfHeaderDict(davres, dictIf, fullurl, locktokenlist, entitytag):
    debug("testIfHeaderDict(%s, %s, %s)" % (fullurl, locktokenlist, entitytag),
          var=dictIf, module="if")

    if fullurl in dictIf:
        listTest = dictIf[fullurl]
    elif "*" in dictIf:
        listTest = dictIf["*"]
    else:
        return True   

#    supportEntityTag = dav.isInfoTypeSupported(path, "etag")
    supportEntityTag = davres.supportEtag()
    for listTestConds in listTest:
        matchfailed = False

        for (testflag, checkstyle, checkvalue) in listTestConds:
            if checkstyle == "entity" and supportEntityTag:
                testresult = entitytag == checkvalue  
            elif checkstyle == "entity":
                testresult = testflag
            elif checkstyle == "locktoken":
                testresult = checkvalue in locktokenlist
            else: # unknown
                testresult = True
            checkresult = testresult == testflag
            if not checkresult:
                matchfailed = True         
                break
        if not matchfailed:
            return True
    debug("  -> FAILED", module="if")
    return False

testIfHeaderDict.__test__ = False # Tell nose to ignore this function

#===============================================================================
# TEST
#===============================================================================
def testLogging():
    enable_loggers = ["test",
                      ]
    initLogging(3, enable_loggers)
    
    _baseLogger = logging.getLogger(BASE_LOGGER_NAME)
    _enabledLogger = getModuleLogger("test")  
    _disabledLogger = getModuleLogger("test2")
    
    _baseLogger.debug("_baseLogger.debug")  
    _baseLogger.info("_baseLogger.info")  
    _baseLogger.warning("_baseLogger.warning")  
    _baseLogger.error("_baseLogger.error")  
    print 

    _enabledLogger.debug("_enabledLogger.debug")  
    _enabledLogger.info("_enabledLogger.info")  
    _enabledLogger.warning("_enabledLogger.warning")  
    _enabledLogger.error("_enabledLogger.error")  
    print 
    
    _disabledLogger.debug("_disabledLogger.debug")  
    _disabledLogger.info("_disabledLogger.info")  
    _disabledLogger.warning("_disabledLogger.warning")  
    _disabledLogger.error("_disabledLogger.error")  
    print 

    write("util.write()")
    warn("util.warn()")
    status("util.status()")
    note("util.note()")
    debug("util.debug()")
    

if __name__ == "__main__":
    testLogging()
    pass
