# -*- coding: iso-8859-1 -*-

"""
util
====

:Author: Ho Chun Wei, fuzzybr80(at)gmail.com (author of original PyFileServer)
:Author: Martin Wendt, moogle(at)wwwendt.de 
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

Miscellaneous support functions for WsgiDAV.

See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
"""
from urllib import quote
from lxml import etree
from lxml.etree import SubElement
from dav_error import DAVError, getHttpStatusString, HTTP_BAD_REQUEST
from pprint import pprint
from wsgidav.dav_error import HTTP_PRECONDITION_FAILED, HTTP_NOT_MODIFIED
import re
import md5
import os
import calendar
import threading
import sys
import time
import stat

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

__docformat__ = 'reStructuredText'

#===============================================================================
# Debugging
#===============================================================================
def traceCall(msg=None):
    """Return name of calling function."""
    if __debug__:
        f_code = sys._getframe(2).f_code
        if msg is None:
            msg = ": %s"
        else: msg = ""
        print "%s.%s #%s%s" % (f_code.co_filename, f_code.co_name, f_code.co_lineno, msg)


def isVerboseMode(environ):
    if environ['wsgidav.verbose'] >= 1 and environ["REQUEST_METHOD"] in environ.get('wsgidav.debug_methods', []):
        return True
    return False


def getRfc1123Time(secs=None):   
    """Return <secs> in rfc 1123 date/time format (pass secs=None for current date)."""
    return time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(secs))


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
    else:
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

    return None


def log(msg, var=None):
    out = sys.stderr
    tid = threading._get_ident() #threading.currentThread()
    print >>out, "<%s> %s" % (tid, msg)
    if var:
        pprint(var, out, indent=4)
    
    
def debug(cat, msg):
    """Print debug msessage to console (type filtered).
    
    This is only a hack during early develpment: we can spread log calls and
    use temporarily disable it by hard coding the filter condition here. 
    cat: 'pp' Paste Prune
         'sc' "Socket closed" exception
    """
    assert cat in ("pp", "sc")
    tid = threading._get_ident() #threading.currentThread()
    if cat in ("pp", "NOTsc"):
        print >>sys.stderr, "<%s>[%s] %s" % (tid, cat, msg)

        
#===============================================================================
# WSGI, strings and URLs
#===============================================================================
def saveSplit(s, sep, maxsplit):
    """Split string, always returning n-tuple (filled with None if necessary)."""
    tok = s.split(sep, maxsplit)
    while len(tok) <= maxsplit:
        tok.append(None)
    return tok


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


def getContentLength(environ):
    """Return CONTENT_LENGTH in a safe way (defaults to 0)."""
    try:
        return max(0, long(environ.get('CONTENT_LENGTH', 0)))
    except ValueError:
        return 0


def getRealm(environ):
    return getUriRealm(environ["SCRIPT_NAME"] + environ["PATH_INFO"])


def getUri(environ):
    return environ["PATH_INFO"]


def getUriRealm(uri):
    """Return realm, i.e. first part of URI with a leading '/'."""
    if uri.strip() in ("", "/"):
        return "/"
    return uri.strip("/").split("/")[0]


def getUriName(uri):
    """Return local name, i.e. last part of URI."""
    return uri.strip("/").split("/")[-1]
    

def getUriParent(uri):
    """Return URI of parent collection."""
    if not uri or uri.strip() == "/":
        return None
    return uri.rstrip("/").rsplit("/", 1)[0] + "/"


def makeCompleteUrl(environ, localUri=None):
    """URL reconstruction according to PEP 333.
    @see http://www.python.org/dev/peps/pep-0333/#id33
    """
    url = environ['wsgi.url_scheme']+'://'
    
    if environ.get('HTTP_HOST'):
        url += environ['HTTP_HOST']
    else:
        url += environ['SERVER_NAME']
    
        if environ['wsgi.url_scheme'] == 'https':
            if environ['SERVER_PORT'] != '443':
                url += ':' + environ['SERVER_PORT']
        else:
            if environ['SERVER_PORT'] != '80':
                url += ':' + environ['SERVER_PORT']
    
    url += quote(environ.get('SCRIPT_NAME',''))

    if localUri is None:
        url += quote(environ.get('PATH_INFO',''))
        if environ.get('QUERY_STRING'):
            url += '?' + environ['QUERY_STRING']
    else:
        url += localUri # TODO: quote?
    return url


#===============================================================================
# XML
#===============================================================================

def parseXmlBody(environ, allowEmpty=False):
    """Read request body XML into an lxml.etree.Element.
    
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

    if requestbody == "":
        if allowEmpty:
            return None
        else:
            raise DAVError(HTTP_BAD_REQUEST, "Body must not be empty.")
    
    try:
        rootEL = etree.fromstring(requestbody)
    except Exception, e:
        raise DAVError(HTTP_BAD_REQUEST, "Invalid XML format.", srcexception=e)   
    
    if environ['wsgidav.verbose'] >= 1 and environ["REQUEST_METHOD"] in environ.get('wsgidav.debug_methods', []):
        print "XML request for %s:\n%s" % (environ["REQUEST_METHOD"], etree.tostring(rootEL, pretty_print=True))
    return rootEL
    

def elementContentAsString(element):
    """Serialize etree.Element.
    
    Note: element may contain more than one child or only text (i.e. no child 
          at all). Therefore the resulting string may raise an exception, when
          passed back to etree.XML(). 
    """
    if len(element) == 0:
        return element.text or ""  # Make sure, None is returned as '' 
    stream = StringIO()
    for childnode in element:
        print >>stream, etree.tostring(childnode, pretty_print=False)
    s = stream.getvalue()
    stream.close()
    return s


def sendMultiStatusResponse(environ, start_response, multistatusEL):
    # Send response
    start_response('207 Multistatus', [("Content-Type", "application/xml"), 
                                       ("Date", getRfc1123Time()),
                                       ])
    # Hotfix for Windows XP: PPROPFIND XML response is not recognized, when 
    # pretty_print = True!
#    pretty_print = True
    pretty_print = False
    return ["<?xml version='1.0' ?>",
            etree.tostring(multistatusEL, pretty_print=pretty_print) ]
        
            
def sendSimpleResponse(environ, start_response, status):
    s = getHttpStatusString(status)
    start_response(s, [("Content-Length", "0"),
                       ("Date", getRfc1123Time()),
                       ])
    return [ "" ]      
    
    
def addPropertyResponse(multistatusEL, href, propList):
    """Append <response> element to <multistatus> element.

    <prop> node depends on the value type: 
      - str or unicode: add element with this content
      - None: add an empty element
      - lxml.etree.Element: add XML element as child 
      - DAVError: add an empty element to an own <propstatus> for this status code
    
    @param multistatusEL: lxml.etree.Element
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
    responseEL = SubElement(multistatusEL, "{DAV:}response", 
                            nsmap=nsMap) 
    SubElement(responseEL, "{DAV:}href").text = href
    
    # One <propstat> per status code
    for status in propDict:
        propstatEL = SubElement(responseEL, "{DAV:}propstat")
        # List of <prop>
        propEL = SubElement(propstatEL, "{DAV:}prop")
        for name, value in propDict[status]:
            if value is None:
                SubElement(propEL, name)
            elif isinstance(value, etree._Element):
                propEL.append(value)
            else:
                # value must be string or unicode
#                log("%s value:%s" % (name, value))
                SubElement(propEL, name).text = value
        # <status>
        SubElement(propstatEL, "{DAV:}status").text = "HTTP/1.1 %s" % status
    
    
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
    if not os.path.isfile(filePath):
        return md5.new(filePath).hexdigest()   
    if sys.platform == 'win32':
        statresults = os.stat(filePath)
        return md5.new(filePath).hexdigest() + '-' + str(statresults[stat.ST_MTIME]) + '-' + str(statresults[stat.ST_SIZE])
    else:
        statresults = os.stat(filePath)
        return str(statresults[stat.ST_INO]) + '-' + str(statresults[stat.ST_MTIME]) + '-' + str(statresults[stat.ST_SIZE])


#===============================================================================
# Ranges     
#===============================================================================

# Range Specifiers
reByteRangeSpecifier = re.compile("(([0-9]+)\-([0-9]*))")
reSuffixByteRangeSpecifier = re.compile("(\-([0-9]+))")

def obtainContentRanges(rangetext, filesize):
    """
   returns tuple
   list: content ranges as values to their parsed components in the tuple 
   (seek_position/abs position of first byte, 
    abs position of last byte, 
    num_of_bytes_to_read)
   value: total length for Content-Length
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
                if mObj.group(3) == '':
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
# If Headers
#===============================================================================

def evaluateHTTPConditionals(dav, path, lastmodified, entitytag, environ, isnewfile=False):
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
    ## Conditions

    # An HTTP/1.1 origin server, upon receiving a conditional request that includes both a Last-Modified date
    # (e.g., in an If-Modified-Since or If-Unmodified-Since header field) and one or more entity tags (e.g., 
    # in an If-Match, If-None-Match, or If-Range header field) as cache validators, MUST NOT return a response 
    # status of 304 (Not Modified) unless doing so is consistent with all of the conditional header fields in 
    # the request.

    if 'HTTP_IF_MATCH' in environ and dav.isInfoTypeSupported(path, "etag"):
        if isnewfile:
            raise DAVError(HTTP_PRECONDITION_FAILED)
        else:
            ifmatchlist = environ['HTTP_IF_MATCH'].split(",")
            for ifmatchtag in ifmatchlist:
                ifmatchtag = ifmatchtag.strip(" \"\t")
                if ifmatchtag == entitytag or ifmatchtag == '*':
                    break   
                raise DAVError(HTTP_PRECONDITION_FAILED,
                               "If-Match header condition failed")

    # If-None-Match 
    # If none of the entity tags match, then the server MAY perform the requested method as if the 
    # If-None-Match header field did not exist, but MUST also ignore any If-Modified-Since header field
    # (s) in the request. That is, if no entity tags match, then the server MUST NOT return a 304 (Not Modified) 
    # response.
    ignoreifmodifiedsince = False         
    if 'HTTP_IF_NONE_MATCH' in environ and dav.isInfoTypeSupported(path, "etag"):         
        if isnewfile:
            ignoreifmodifiedsince = True
        else:
            ifmatchlist = environ['HTTP_IF_NONE_MATCH'].split(",")
            for ifmatchtag in ifmatchlist:
                ifmatchtag = ifmatchtag.strip(" \"\t")
                if ifmatchtag == entitytag or ifmatchtag == '*':
                    raise DAVError(HTTP_PRECONDITION_FAILED,
                                   "If-None-Match header condition failed")
            ignoreifmodifiedsince = True

    if not isnewfile and 'HTTP_IF_UNMODIFIED_SINCE' in environ and dav.isInfoTypeSupported(path, "modified"):
        ifunmodtime = parseTimeString(environ['HTTP_IF_UNMODIFIED_SINCE'])
        if ifunmodtime and ifunmodtime <= lastmodified:
            raise DAVError(HTTP_PRECONDITION_FAILED,
                           "If-Unmodified-Since header condition failed")

    if not isnewfile and 'HTTP_IF_MODIFIED_SINCE' in environ and not ignoreifmodifiedsince and dav.isInfoTypeSupported(path, "modified"):
        ifmodtime = parseTimeString(environ['HTTP_IF_MODIFIED_SINCE'])
        if ifmodtime and ifmodtime > lastmodified:
            raise DAVError(HTTP_NOT_MODIFIED,
                           "If-Modified-Since header condition failed")




reIfSeparator = re.compile(r'(\<([^>]+)\>)|(\(([^\)]+)\))')
reIfHeader = re.compile(r'\<([^>]+)\>([^<]+)')
reIfTagList = re.compile(r'\(([^)]+)\)')
reIfTagListContents = re.compile(r'(\S+)')


def parseIfHeaderDict(environ):
    """Parse HTTP_IF header into a dictionary and lists, and cache result.
    
    @see http://www.webdav.org/specs/rfc2518.html#HEADER_If
    """
    if "wsgidav.conditions.if" in environ:
        return

    if not "HTTP_IF" in environ:
        environ['wsgidav.conditions.if'] = None
        environ['wsgidav.ifLockTokenList'] = []
        return
    
    iftext = environ["HTTP_IF"].strip()
    if not iftext.startswith('<'):
        iftext = '<*>' + iftext   

    ifDict = dict([])
    ifLockList = []
    
    resource1 = '*'
    for (tmpURLVar, URLVar, _tmpContentVar, contentVar) in reIfSeparator.findall(iftext):
        if tmpURLVar != '':
            resource1 = URLVar         
        else:
            listTagContents = []
            testflag = True
            for listitem in reIfTagListContents.findall(contentVar):            
                if listitem.upper() != 'NOT':
                    if listitem.startswith('['):
                        listTagContents.append((testflag,'entity',listitem.strip('\"[]')))   
                    else:
                        listTagContents.append((testflag,'locktoken',listitem.strip('<>')))            
                        ifLockList.append(listitem.strip("<>"))
                testflag = listitem.upper() != 'NOT'

            if resource1 in ifDict:
                listTag = ifDict[resource1]
            else:
                listTag = []
                ifDict[resource1] = listTag
            listTag.append(listTagContents)

    environ['wsgidav.conditions.if'] = ifDict
    environ['wsgidav.ifLockTokenList'] = ifLockList
    return


#def _lookForLockTokenInSubDict(locktoken, listTest):
#    for listTestConds in listTest:
#        for (testflag, checkstyle, checkvalue) in listTestConds:
#            if checkstyle == 'locktoken' and testflag:
#                if locktoken == checkvalue:  
#                    return True
#    return False   




#def testForLockTokenInIfHeaderDict(dictIf, locktoken, fullurl, headurl):
#    if '*' in dictIf:
#        if _lookForLockTokenInSubDict(locktoken, dictIf['*']):
#            return True
#
#    if fullurl in dictIf:
#        if _lookForLockTokenInSubDict(locktoken, dictIf[fullurl]):
#            return True
#
#    if headurl in dictIf:
#        if _lookForLockTokenInSubDict(locktoken, dictIf[headurl]):
#            return True




def testIfHeaderDict(dav, path, dictIf, fullurl, locktokenlist, entitytag):
    
    log("testIfHeaderDict(%s, %s, %s, %s)" % (path, fullurl, locktokenlist, entitytag),
        dictIf)

    if fullurl in dictIf:
        listTest = dictIf[fullurl]
    elif '*' in dictIf:
        listTest = dictIf['*']
    else:
        return True   

    supportEntityTag = dav.isInfoTypeSupported(path, "etag")
    for listTestConds in listTest:
        matchfailed = False

        for (testflag, checkstyle, checkvalue) in listTestConds:
            if checkstyle == 'entity' and supportEntityTag:
                testresult = entitytag == checkvalue  
            elif checkstyle == 'entity':
                testresult = testflag
            elif checkstyle == 'locktoken':
                testresult = checkvalue in locktokenlist
            else: # unknown
                testresult = True
            checkresult = testresult == testflag
            if not checkresult:
                matchfailed = True         
                break
        if not matchfailed:
            return True
    return False

#===============================================================================
# TEST
#===============================================================================
if __name__ == "__main__":
    #n = etree.XML("<a><b/></a><c/>")
    n = etree.XML("abc")
    print etree.tostring(n)
    
    pass