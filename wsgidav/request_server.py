# (c) 2009-2011 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
WSGI application that handles one single WebDAV request.

See `Developers info`_ for more information about the WsgiDAV architecture.

.. _`Developers info`: http://docs.wsgidav.googlecode.com/hg/html/develop.html  
"""
from urlparse import urlparse
from wsgidav.dav_error import HTTP_OK, HTTP_LENGTH_REQUIRED
from wsgidav import xml_tools
import util
import urllib
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO #@UnusedImport

from dav_error import DAVError, asDAVError, \
    HTTP_BAD_REQUEST,\
    HTTP_NOT_IMPLEMENTED, HTTP_NOT_FOUND, HTTP_FORBIDDEN, HTTP_INTERNAL_ERROR,\
    HTTP_FAILED_DEPENDENCY, HTTP_METHOD_NOT_ALLOWED,\
    PRECONDITION_CODE_PropfindFiniteDepth, HTTP_MEDIATYPE_NOT_SUPPORTED,\
    HTTP_CONFLICT, \
    PRECONDITION_CODE_LockTokenMismatch, getHttpStatusString,\
    HTTP_PRECONDITION_FAILED, HTTP_BAD_GATEWAY, HTTP_NO_CONTENT, HTTP_CREATED,\
    HTTP_RANGE_NOT_SATISFIABLE

#import lock_manager

# Trick PyDev to do intellisense and don't produce warnings:
from util import etree #@UnusedImport
if False: from xml.etree import ElementTree as etree     #@Reimport
   
__docformat__ = "reStructuredText"

_logger = util.getModuleLogger(__name__)

BLOCK_SIZE = 8192



#===============================================================================
# RequestServer
#===============================================================================
class RequestServer(object):

    def __init__(self, davProvider):
        self._davProvider = davProvider
        self.allowPropfindInfinite = True
        self._verbose = 2
        util.debug("RequestServer: __init__", module="sc")

    def __del__(self):
        util.debug("RequestServer: __del__", module="sc")

    def __call__(self, environ, start_response):
        assert "wsgidav.verbose" in environ
        # TODO: allow anonymous somehow: this should run, even if http_authenticator middleware is not installed
#        assert "http_authenticator.username" in environ
        if not "http_authenticator.username" in environ:
            _logger.info("*** missing 'http_authenticator.username' in environ")

        environ["wsgidav.username"] = environ.get("http_authenticator.username", "anonymous") 
        requestmethod =  environ["REQUEST_METHOD"]

        # Convert 'infinity' and 'T'/'F' to a common case
        if environ.get("HTTP_DEPTH") is not None: 
            environ["HTTP_DEPTH"] = environ["HTTP_DEPTH"].lower() 
        if environ.get("HTTP_OVERWRITE") is not None: 
            environ["HTTP_OVERWRITE"] = environ["HTTP_OVERWRITE"].upper() 

        if "HTTP_EXPECT" in environ:
            pass
        
        # Dispatch HTTP request methods to 'doMETHOD()' handlers
        method = getattr(self, "do%s" % requestmethod, None)
        if not method:
            self._fail(HTTP_METHOD_NOT_ALLOWED)

        if environ.get("wsgidav.debug_break"):
            pass # Set a break point here
            
        if environ.get("wsgidav.debug_profile"):
            from cProfile import Profile
            profile = Profile()
            res = profile.runcall(method, environ, start_response)
            # sort: 0:"calls",1:"time", 2: "cumulative"
            profile.print_stats(sort=2)
            for v in res:
                yield v
            return
  
        for v in method(environ, start_response):
            yield v
        return
#        return method(environ, start_response)


    def _fail(self, value, contextinfo=None, srcexception=None, errcondition=None):
        """Wrapper to raise (and log) DAVError."""
        if isinstance(value, Exception):
            e = asDAVError(value)
        else:  
            e = DAVError(value, contextinfo, srcexception, errcondition)
        util.log("Raising DAVError %s" % e.getUserInfo())
        raise e


    def _sendResponse(self, environ, start_response, rootRes, successCode, errorList):
        """Send WSGI response (single or multistatus).
        
        - If errorList is None or [], then <successCode> is send as response.
        - If errorList contains a single error with a URL that matches rootRes,
          then this error is returned.
        - If errorList contains more than one error, then '207 Multistatus' is 
          returned.
        """
        assert successCode in (HTTP_CREATED, HTTP_NO_CONTENT, HTTP_OK)
        if not errorList:
            # Status OK
            return util.sendStatusResponse(environ, start_response, successCode)
        if len(errorList) == 1 and errorList[0][0] == rootRes.getHref():
            # Only one error that occurred on the root resource
            return util.sendStatusResponse(environ, start_response, errorList[0][1])
        
        # Multiple errors, or error on one single child
        multistatusEL = xml_tools.makeMultistatusEL()
        
        for refurl, e in errorList:
#            assert refurl.startswith("http:")
            assert refurl.startswith("/")
            assert isinstance(e, DAVError)
            responseEL = etree.SubElement(multistatusEL, "{DAV:}response") 
            etree.SubElement(responseEL, "{DAV:}href").text = refurl
            etree.SubElement(responseEL, "{DAV:}status").text = "HTTP/1.1 %s" % getHttpStatusString(e)

        return util.sendMultiStatusResponse(environ, start_response, multistatusEL)


    def _checkWritePermission(self, res, depth, environ):
        """Raise DAVError(HTTP_LOCKED), if res is locked.
        
        If depth=='infinity', we also raise when child resources are locked.
        """
        lockMan = self._davProvider.lockManager
        if lockMan is None or res is None:
            return True

        refUrl = res.getRefUrl()
        
        if "wsgidav.conditions.if" not in environ:
            util.parseIfHeaderDict(environ)

        # raise HTTP_LOCKED if conflict exists
        lockMan.checkWritePermission(refUrl, depth, 
                                     environ["wsgidav.ifLockTokenList"], 
                                     environ["wsgidav.username"])


    def _evaluateIfHeaders(self, res, environ):
        """Apply HTTP headers on <path>, raising DAVError if conditions fail.
         
        Add environ['wsgidav.conditions.if'] and environ['wsgidav.ifLockTokenList'].
        Handle these headers:
        
          - If-Match, If-Modified-Since, If-None-Match, If-Unmodified-Since:
            Raising HTTP_PRECONDITION_FAILED or HTTP_NOT_MODIFIED
          - If:
            Raising HTTP_PRECONDITION_FAILED

        @see http://www.webdav.org/specs/rfc4918.html#HEADER_If
        @see util.evaluateHTTPConditionals
        """
        # Add parsed If header to environ
        if "wsgidav.conditions.if" not in environ:
            util.parseIfHeaderDict(environ)

        # Bail out, if res does not exist
        if res is None:
            return

        ifDict = environ["wsgidav.conditions.if"]

        # Raise HTTP_PRECONDITION_FAILED or HTTP_NOT_MODIFIED, if standard 
        # HTTP condition fails
        lastmodified = -1 # nonvalid modified time
        entitytag = "[]" # Non-valid entity tag
        if res.getLastModified() is not None:
            lastmodified = res.getLastModified()            
        if res.getEtag() is not None:
            entitytag = res.getEtag()            

        if ("HTTP_IF_MODIFIED_SINCE" in environ 
            or "HTTP_IF_UNMODIFIED_SINCE" in environ 
            or "HTTP_IF_MATCH" in environ 
            or "HTTP_IF_NONE_MATCH" in environ):
            util.evaluateHTTPConditionals(res, lastmodified, entitytag, environ)

        if not "HTTP_IF" in environ:
            return

        # Raise HTTP_PRECONDITION_FAILED, if DAV 'If' condition fails  
        # TODO: handle empty locked resources
        # TODO: handle unmapped locked resources
#            isnewfile = not provider.exists(mappedpath)

        refUrl = res.getRefUrl()
        lockMan = self._davProvider.lockManager
        locktokenlist = []
        if lockMan:
            lockList = lockMan.getIndirectUrlLockList(refUrl, environ["wsgidav.username"])
            for lock in lockList:
                locktokenlist.append(lock["token"])

        if not util.testIfHeaderDict(res, ifDict, refUrl, locktokenlist, entitytag):
            self._fail(HTTP_PRECONDITION_FAILED, "'If' header condition failed.") 

        return
    
    
    
    
    def doPROPFIND(self, environ, start_response):
        """
        TODO: does not yet support If and If HTTP Conditions
        @see http://www.webdav.org/specs/rfc4918.html#METHOD_PROPFIND
        """
        path = environ["PATH_INFO"]
        res = self._davProvider.getResourceInst(path, environ)

        # RFC: By default, the PROPFIND method without a Depth header MUST act 
        # as if a "Depth: infinity" header was included.
        environ.setdefault("HTTP_DEPTH", "infinity")
        if not environ["HTTP_DEPTH"] in ("0", "1", "infinity"):            
            self._fail(HTTP_BAD_REQUEST, 
                       "Invalid Depth header: '%s'." % environ["HTTP_DEPTH"])

        if environ["HTTP_DEPTH"] == "infinity" and not self.allowPropfindInfinite:
            self._fail(HTTP_FORBIDDEN, 
                       "PROPFIND 'infinite' was disabled for security reasons.",
                       errcondition=PRECONDITION_CODE_PropfindFiniteDepth)    

        if res is None:
            self._fail(HTTP_NOT_FOUND)
        
        if environ.get("wsgidav.debug_break"):
            pass # break point

        self._evaluateIfHeaders(res, environ)

        # Parse PROPFIND request
        requestEL = util.parseXmlBody(environ, allowEmpty=True)
        if requestEL is None:   
            # An empty PROPFIND request body MUST be treated as a request for 
            # the names and values of all properties.
            requestEL = etree.XML("<D:propfind xmlns:D='DAV:'><D:allprop/></D:propfind>")

        if requestEL.tag != "{DAV:}propfind":
            self._fail(HTTP_BAD_REQUEST)   
        
        propNameList = []
        propFindMode = None
        for pfnode in requestEL:
            if pfnode.tag == "{DAV:}allprop":
                if propFindMode: 
                    # RFC: allprop and propname are mutually exclusive
                    self._fail(HTTP_BAD_REQUEST)
                propFindMode = "allprop"  
            # TODO: implement <include> option
#            elif pfnode.tag == "{DAV:}include":
#                if not propFindMode in (None, "allprop"):
#                    self._fail(HTTP_BAD_REQUEST, "<include> element is only valid with 'allprop'.")
#                for pfpnode in pfnode:
#                    propNameList.append(pfpnode.tag)       
            elif pfnode.tag == "{DAV:}propname":
                if propFindMode: # RFC: allprop and propname are mutually exclusive
                    self._fail(HTTP_BAD_REQUEST)
                propFindMode = "propname"       
            elif pfnode.tag == "{DAV:}prop":
                if propFindMode not in (None, "named"): # RFC: allprop and propname are mutually exclusive
                    self._fail(HTTP_BAD_REQUEST)
                propFindMode = "named"
                for pfpnode in pfnode:
                    propNameList.append(pfpnode.tag)       

        # --- Build list of resource URIs 
        
        reslist = res.getDescendants(depth=environ["HTTP_DEPTH"], addSelf=True)
#        if environ["wsgidav.verbose"] >= 3:
#            pprint(reslist, indent=4)
        
        multistatusEL = xml_tools.makeMultistatusEL()
        responsedescription = []
        
        for child in reslist:

            if propFindMode == "allprop": 
                propList = child.getProperties("allprop")
            elif propFindMode == "propname":
                propList = child.getProperties("propname")
            else:
                propList = child.getProperties("named", nameList=propNameList)

            href = child.getHref()
            util.addPropertyResponse(multistatusEL, href, propList)

        if responsedescription:
            etree.SubElement(multistatusEL, "{DAV:}responsedescription").text = "\n".join(responsedescription)
            
        return util.sendMultiStatusResponse(environ, start_response, multistatusEL)




    def doPROPPATCH(self, environ, start_response):
        """Handle PROPPATCH request to set or remove a property.
        
        @see http://www.webdav.org/specs/rfc4918.html#METHOD_PROPPATCH
        """
        path = environ["PATH_INFO"]
        res = self._davProvider.getResourceInst(path, environ)

        # Only accept Depth: 0 (but assume this, if omitted)
        environ.setdefault("HTTP_DEPTH", "0")
        if environ["HTTP_DEPTH"] != "0":
            self._fail(HTTP_BAD_REQUEST, "Depth must be '0'.")
        
        if res is None:
            self._fail(HTTP_NOT_FOUND)

        self._evaluateIfHeaders(res, environ)
        self._checkWritePermission(res, "0", environ)

        # Parse request
        requestEL = util.parseXmlBody(environ)

        if requestEL.tag != "{DAV:}propertyupdate":
            self._fail(HTTP_BAD_REQUEST)   

        # Create a list of update request tuples: (propname, value)
        propupdatelist = []

        for ppnode in requestEL:
            propupdatemethod = None
            if ppnode.tag == "{DAV:}remove":
                propupdatemethod = "remove"
            elif ppnode.tag == "{DAV:}set":
                propupdatemethod = "set"
            else:
                self._fail(HTTP_BAD_REQUEST, "Unknown tag (expected 'set' or 'remove').")   
            
            for propnode in ppnode:
                if propnode.tag != "{DAV:}prop":
                    self._fail(HTTP_BAD_REQUEST, "Unknown tag (expected 'prop').")   

                for propertynode in propnode: 
                    propvalue = None
                    if propupdatemethod == "remove":
                        propvalue = None # Mark as 'remove'
                        if len(propertynode) > 0:
                            # 14.23: All the XML elements in a 'prop' XML element inside of a 'remove' XML element MUST be empty
                            self._fail(HTTP_BAD_REQUEST, "prop element must be empty for 'remove'.")   
                    else:
                        propvalue = propertynode
                            
                    propupdatelist.append( (propertynode.tag, propvalue) )

        # Apply updates in SIMULATION MODE and create a result list (propname, result)
        successflag = True
        writeresultlist = []

        for (propname, propvalue) in propupdatelist:
            try:         
                res.setPropertyValue(propname, propvalue, dryRun=True)
            except Exception, e:
                writeresult = asDAVError(e)
            else:
                writeresult = "200 OK"
            writeresultlist.append( (propname, writeresult) )
            successflag = successflag and writeresult == "200 OK"
             
        # Generate response list of 2-tuples (name, value)
        # <value> is None on success, or an instance of DAVError
        propResponseList = []
        responsedescription = []
        
        if not successflag:
            # If dry run failed: convert all OK to FAILED_DEPENDENCY.
            for (propname, result) in writeresultlist:
                if result == "200 OK":
                    result = DAVError(HTTP_FAILED_DEPENDENCY)
                elif isinstance(result, DAVError):
                    responsedescription.append(result.getUserInfo())
                propResponseList.append( (propname, result) )
                
        else:
            # Dry-run succeeded: set properties again, this time in 'real' mode
            # In theory, there should be no exceptions thrown here, but this is real live... 
            for (propname, propvalue) in propupdatelist:
                try:
                    res.setPropertyValue(propname, propvalue, dryRun=False)
                    # Set value to None, so the response xml contains empty tags
                    propResponseList.append( (propname, None) )
                except Exception, e:
                    e = asDAVError(e)
                    propResponseList.append( (propname, e) )
                    responsedescription.append(e.getUserInfo())

        # Generate response XML
        multistatusEL = xml_tools.makeMultistatusEL()
#        href = util.makeCompleteUrl(environ, path) 
        href = res.getHref()
        util.addPropertyResponse(multistatusEL, href, propResponseList)
        if responsedescription:
            etree.SubElement(multistatusEL, "{DAV:}responsedescription").text = "\n".join(responsedescription)
        
        # Send response
        return util.sendMultiStatusResponse(environ, start_response, multistatusEL)




    def doMKCOL(self, environ, start_response):               
        """Handle MKCOL request to create a new collection.
        
        @see http://www.webdav.org/specs/rfc4918.html#METHOD_MKCOL
        """
        path = environ["PATH_INFO"]
        provider = self._davProvider
#        res = provider.getResourceInst(path, environ)

        # Do not understand ANY request body entities
        if util.getContentLength(environ) != 0:
            self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
                       "The server does not handle any body content.")

        # Only accept Depth: 0 (but assume this, if omitted)
        if environ.setdefault("HTTP_DEPTH", "0") != "0":
            self._fail(HTTP_BAD_REQUEST, "Depth must be '0'.")
        
        if provider.exists(path, environ):
            self._fail(HTTP_METHOD_NOT_ALLOWED,
                       "MKCOL can only be executed on an unmapped URL.")         

        parentRes = provider.getResourceInst(util.getUriParent(path), environ)
        if not parentRes or not parentRes.isCollection:
            self._fail(HTTP_CONFLICT, "Parent must be an existing collection.")          

        # TODO: should we check If headers here?
#        self._evaluateIfHeaders(res, environ)
        # Check for write permissions on the PARENT
        self._checkWritePermission(parentRes, "0", environ)

        parentRes.createCollection(util.getUriName(path))

        return util.sendStatusResponse(environ, start_response, HTTP_CREATED)



    
    def doPOST(self, environ, start_response):
        """
        @see http://www.webdav.org/specs/rfc4918.html#METHOD_POST
        """
        self._fail(HTTP_METHOD_NOT_ALLOWED)         



    
    def doDELETE(self, environ, start_response):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_DELETE
        """
        path = environ["PATH_INFO"]
        provider = self._davProvider
        res = provider.getResourceInst(path, environ)

        # --- Check request preconditions --------------------------------------
        
        if util.getContentLength(environ) != 0:
            self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
                       "The server does not handle any body content.")
        if res is None:
            self._fail(HTTP_NOT_FOUND)         

        if res.isCollection: 
            # Delete over collection
            # "The DELETE method on a collection MUST act as if a 
            # 'Depth: infinity' header was used on it. A client MUST NOT submit 
            # a Depth header with a DELETE on a collection with any value but 
            # infinity."
            if environ.setdefault("HTTP_DEPTH", "infinity") != "infinity":
                self._fail(HTTP_BAD_REQUEST,
                           "Only Depth: infinity is supported for collections.")         
        else:
            if not environ.setdefault("HTTP_DEPTH", "0") in ("0", "infinity"):
                self._fail(HTTP_BAD_REQUEST,
                           "Only Depth: 0 or infinity are supported for non-collections.")         

        self._evaluateIfHeaders(res, environ)
        # We need write access on the parent collection. Also we check for 
        # locked children
        parentRes = provider.getResourceInst(util.getUriParent(path), environ)
        if parentRes:
#            self._checkWritePermission(parentRes, environ["HTTP_DEPTH"], environ)
            self._checkWritePermission(parentRes, "0", environ)
        else:
#            self._checkWritePermission(res, environ["HTTP_DEPTH"], environ)
            self._checkWritePermission(res, "0", environ)

        # --- Let provider handle the request natively -------------------------
        
        # Errors in deletion; [ (<ref-url>, <DAVError>), ... ]
        errorList = []  

        try:
            handled = res.handleDelete()
            assert handled in (True, False) or type(handled) is list
            if type(handled) is list:
                errorList = handled
                handled = True
        except Exception, e:
            errorList = [ (res.getHref(), asDAVError(e)) ]
            handled = True
        if handled:
            return self._sendResponse(environ, start_response, 
                                      res, HTTP_NO_CONTENT, errorList)
            
        
        # --- Let provider implement own recursion -----------------------------
        
        # Get a list of all resources (parents after children, so we can remove 
        # them in that order)
        reverseChildList = res.getDescendants(depthFirst=True, 
                                              depth=environ["HTTP_DEPTH"], 
                                              addSelf=True)

        if res.isCollection and res.supportRecursiveDelete():
            hasConflicts = False
            for childRes in reverseChildList:
                try:
                    self._evaluateIfHeaders(childRes, environ)
                    self._checkWritePermission(childRes, "0", environ)
                except:
                    hasConflicts = True
                    break
            
            if not hasConflicts:
                try:
                    errorList = res.delete()
                except Exception, e:
                    errorList = [ (res.getHref(), asDAVError(e)) ]
                return self._sendResponse(environ, start_response, 
                                          res, HTTP_NO_CONTENT, errorList)

        # --- Implement file-by-file processing --------------------------------
        
        # Hidden paths (ancestors of failed deletes) {<path>: True, ...}
        ignoreDict = {}  
        for childRes in reverseChildList:
            if childRes.path in ignoreDict:
                _logger.debug("Skipping %s (contains error child)" % childRes.path)
                ignoreDict[util.getUriParent(childRes.path)] = ""
                continue            

            try:
                # 9.6.1.: Any headers included with delete must be applied in 
                #         processing every resource to be deleted
                self._evaluateIfHeaders(childRes, environ)
                self._checkWritePermission(childRes, "0", environ)
                childRes.delete()
                # Double-check, if deletion succeeded
                if provider.exists(childRes.path, environ):
                    raise DAVError(HTTP_INTERNAL_ERROR, 
                                   "Resource could not be deleted.")
            except Exception, e:
                errorList.append( (childRes.getHref(), asDAVError(e)) )
                ignoreDict[util.getUriParent(childRes.path)] = True

        # --- Send response ----------------------------------------------------

        return self._sendResponse(environ, start_response, 
                                  res, HTTP_NO_CONTENT, errorList)




    def doPUT(self, environ, start_response):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_PUT
        """
        path = environ["PATH_INFO"]
        provider = self._davProvider
        res = provider.getResourceInst(path, environ)
        parentRes = provider.getResourceInst(util.getUriParent(path), environ)
        
        isnewfile = res is None

        ## Test for unsupported stuff
        if "HTTP_CONTENT_ENCODING" in environ:
            self._fail(HTTP_NOT_IMPLEMENTED,
                       "Content-encoding header is not supported.")
        if "HTTP_CONTENT_RANGE" in environ:
            self._fail(HTTP_NOT_IMPLEMENTED,
                       "Content-range header is not supported.")

        if res and res.isCollection:
            self._fail(HTTP_METHOD_NOT_ALLOWED, "Cannot PUT to a collection")
        elif not parentRes.isCollection: # TODO: allow parentRes==None?
            self._fail(HTTP_CONFLICT, "PUT parent must be a collection")

        self._evaluateIfHeaders(res, environ)

        if isnewfile:
            self._checkWritePermission(parentRes, "0", environ)
            res = parentRes.createEmptyResource(util.getUriName(path))
        else:
            self._checkWritePermission(res, "0", environ)

        ## Start Content Processing
        # Content-Length may be 0 or greater. (Set to -1 if missing or invalid.) 
#        WORKAROUND_BAD_LENGTH = True
        try:
            contentlength = max(-1, long(environ.get("CONTENT_LENGTH", -1)))
        except ValueError: 
            contentlength = -1
        
#        if contentlength < 0 and not WORKAROUND_BAD_LENGTH:
        if (
            (contentlength < 0) and
            (environ.get("HTTP_TRANSFER_ENCODING", "").lower() != "chunked")
        ):
            # HOTFIX: not fully understood, but MS sends PUT without content-length,
            # when creating new files 
            if "Microsoft-WebDAV-MiniRedir" in environ.get("HTTP_USER_AGENT", ""):
                _logger.warning("Setting misssing Content-Length to 0 for MS client")
                contentlength = 0
            else:
                self._fail(HTTP_LENGTH_REQUIRED, 
                           "PUT request with invalid Content-Length: (%s)" % environ.get("CONTENT_LENGTH"))
        
        hasErrors = False
        try:      
            fileobj = res.beginWrite(contentType=environ.get("CONTENT_TYPE"))

            if environ.get("HTTP_TRANSFER_ENCODING", "").lower() == "chunked":
                buf = environ["wsgi.input"].readline()
                if buf == '':
                    l = 0
                else:
                    l = int(buf, 16)

                environ["wsgidav.some_input_read"] = 1
                while l > 0:
                    buf = environ["wsgi.input"].read(l)
                    fileobj.write(buf)
                    environ["wsgi.input"].readline()
                    buf = environ["wsgi.input"].readline()
                    if buf == '':
                        l = 0
                    else:
                        l = int(buf, 16)
                environ["wsgidav.all_input_read"] = 1
                    
            elif contentlength == 0:
                # TODO: review this
                # XP and Vista MiniRedir submit PUT with Content-Length 0, 
                # before LOCK and the real PUT. So we have to accept this. 
                _logger.info("PUT: Content-Length == 0. Creating empty file...")
                
#            elif contentlength < 0:
#                # TODO: review this
#                # If CONTENT_LENGTH is invalid, we may try to workaround this
#                # by reading until the end of the stream. This may block however!
#                # The iterator produced small chunks of varying size, but not
#                # sure, if we always get everything before it times out.
#                _logger.warning("PUT with invalid Content-Length (%s). Trying to read all (this may timeout)..." % environ.get("CONTENT_LENGTH"))
#                nb = 0
#                try:
#                    for s in environ["wsgi.input"]:
#                        environ["wsgidav.some_input_read"] = 1
#                        _logger.debug("PUT: read from wsgi.input.__iter__, len=%s" % len(s))
#                        fileobj.write(s)
#                        nb += len (s)
#                except socket.timeout:
#                    _logger.warning("PUT: input timed out after writing %s bytes" % nb)
#                    hasErrors = True                    
            else:
                assert contentlength > 0
                contentremain = contentlength
                while contentremain > 0:
                    n = min(contentremain, BLOCK_SIZE)
                    readbuffer = environ["wsgi.input"].read(n)
                    # This happens with litmus expect-100 test:
#                    assert len(readbuffer) > 0, "input.read(%s) returned %s bytes" % (n, len(readbuffer))
                    if not len(readbuffer) > 0:
                        util.warn("input.read(%s) returned 0 bytes" % n)
                        break
                    environ["wsgidav.some_input_read"] = 1
                    fileobj.write(readbuffer)
                    contentremain -= len(readbuffer)
                
                if contentremain == 0:
                    environ["wsgidav.all_input_read"] = 1
                     
            fileobj.close()

        except Exception, e:
            res.endWrite(withErrors=True)
            _logger.exception("PUT: byte copy failed")
            self._fail(e)

        res.endWrite(hasErrors)

        if isnewfile:
            return util.sendStatusResponse(environ, start_response, HTTP_CREATED)
        return util.sendStatusResponse(environ, start_response, HTTP_NO_CONTENT)




    def doCOPY(self, environ, start_response):
        return self._copyOrMove(environ, start_response, False)




    def doMOVE(self, environ, start_response):
        return self._copyOrMove(environ, start_response, True)




    def _copyOrMove(self, environ, start_response, isMove):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_COPY
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_MOVE
        """
        srcPath = environ["PATH_INFO"]
        provider = self._davProvider
        srcRes = provider.getResourceInst(srcPath, environ)
        srcParentRes = provider.getResourceInst(util.getUriParent(srcPath), environ)

        # --- Check source -----------------------------------------------------
        
        if srcRes is None:
            self._fail(HTTP_NOT_FOUND)         
        if "HTTP_DESTINATION" not in environ:
            self._fail(HTTP_BAD_REQUEST, "Missing required Destination header.")
        if not environ.setdefault("HTTP_OVERWRITE", "T") in ("T", "F"):
            # Overwrite defaults to 'T'
            self._fail(HTTP_BAD_REQUEST, "Invalid Overwrite header.")
        if util.getContentLength(environ) != 0:
            # RFC 2518 defined support for <propertybehavior>.
            # This was dropped with RFC 4918. 
            # Still clients may send it (e.g. DAVExplorer 0.9.1 File-Copy) sends 
            # <A:propertybehavior xmlns:A="DAV:"> <A:keepalive>*</A:keepalive>
            body = environ["wsgi.input"].read(util.getContentLength(environ))
            environ["wsgidav.all_input_read"] = 1
            _logger.info("Ignored copy/move  body: '%s'..." % body[:50])
        
        if srcRes.isCollection:
            # The COPY method on a collection without a Depth header MUST act as 
            # if a Depth header with value "infinity" was included. 
            # A client may submit a Depth header on a COPY on a collection with 
            # a value of "0" or "infinity". 
            environ.setdefault("HTTP_DEPTH", "infinity")
            if not environ["HTTP_DEPTH"] in ("0", "infinity"):
                self._fail(HTTP_BAD_REQUEST, "Invalid Depth header.")
            if isMove and environ["HTTP_DEPTH"] != "infinity":
                self._fail(HTTP_BAD_REQUEST, "Depth header for MOVE collection must be 'infinity'.")
        else:
            # It's an existing non-collection: assume Depth 0
            # Note: litmus 'copymove: 3 (copy_simple)' sends 'infinity' for a 
            # non-collection resource, so we accept that too
            environ.setdefault("HTTP_DEPTH", "0")
            if not environ["HTTP_DEPTH"] in ("0", "infinity"):
                self._fail(HTTP_BAD_REQUEST, "Invalid Depth header.")
            environ["HTTP_DEPTH"] = "0"

        # --- Get destination path and check for cross-realm access ------------
        
        # Destination header may be quoted (e.g. DAV Explorer sends unquoted, 
        # Windows quoted)
        destinationHeader = urllib.unquote(environ["HTTP_DESTINATION"])
        
        # Return fragments as part of <path>
        # Fixes litmus -> running `basic': 9. delete_fragment....... WARNING: DELETE removed collection resource withRequest-URI including fragment; unsafe
        destScheme, destNetloc, destPath, \
        _destParams, _destQuery, _destFrag = urlparse(destinationHeader, 
                                                      allow_fragments=False) 

        if srcRes.isCollection:
            destPath = destPath.rstrip("/") + "/"
        
        if destScheme and destScheme.lower() != environ["wsgi.url_scheme"].lower():
            self._fail(HTTP_BAD_GATEWAY,
                       "Source and destination must have the same scheme.")
        elif destNetloc and destNetloc.lower() != environ["HTTP_HOST"].lower():
            # TODO: this should consider environ["SERVER_PORT"] also
            self._fail(HTTP_BAD_GATEWAY,
                       "Source and destination must have the same host name.")
        elif not destPath.startswith(provider.mountPath + provider.sharePath):
            # Inter-realm copying not supported, since its not possible to 
            # authentication-wise
            self._fail(HTTP_BAD_GATEWAY, 
                       "Inter-realm copy/move is not supported.")

        destPath = destPath[len(provider.mountPath + provider.sharePath):]
        assert destPath.startswith("/")

        # destPath is now relative to current mount/share starting with '/'

        destRes = provider.getResourceInst(destPath, environ)
        destExists = destRes is not None

        destParentRes = provider.getResourceInst(util.getUriParent(destPath), environ)
        
        if not destParentRes or not destParentRes.isCollection:
            self._fail(HTTP_CONFLICT, "Destination parent must be a collection.")

        self._evaluateIfHeaders(srcRes, environ)
        self._evaluateIfHeaders(destRes, environ)
        # Check permissions
        # http://www.webdav.org/specs/rfc4918.html#rfc.section.7.4
        if isMove:
            self._checkWritePermission(srcRes, "infinity", environ)
            # Cannot remove members from locked-0 collections
            if srcParentRes: 
                self._checkWritePermission(srcParentRes, "0", environ)

        # Cannot create or new members in locked-0 collections
        if not destExists: 
            self._checkWritePermission(destParentRes, "0", environ)
        # If target exists, it must not be locked
        self._checkWritePermission(destRes, "infinity", environ)

        if srcPath == destPath:
            self._fail(HTTP_FORBIDDEN, "Cannot copy/move source onto itself")
        elif util.isEqualOrChildUri(srcPath, destPath):
            self._fail(HTTP_FORBIDDEN, "Cannot copy/move source below itself")

        if destExists and environ["HTTP_OVERWRITE"] != "T":
            self._fail(HTTP_PRECONDITION_FAILED,
                       "Destination already exists and Overwrite is set to false")

        # --- Let provider handle the request natively -------------------------
        
        # Errors in copy/move; [ (<ref-url>, <DAVError>), ... ]
        errorList = []  
        successCode = HTTP_CREATED
        if destExists:
            successCode = HTTP_NO_CONTENT

        try:
            if isMove:
                handled = srcRes.handleMove(destPath)
            else:
                isInfinity = environ["HTTP_DEPTH"] == "infinity"
                handled = srcRes.handleCopy(destPath, isInfinity)
            assert handled in (True, False) or type(handled) is list
            if type(handled) is list:
                errorList = handled
                handled = True
        except Exception, e:
            errorList = [ (srcRes.getHref(), asDAVError(e)) ]
            handled = True
        if handled:
            return self._sendResponse(environ, start_response, 
                                      srcRes, HTTP_NO_CONTENT, errorList)

        # --- Cleanup destination before copy/move ----------------------------- 

        srcList = srcRes.getDescendants(addSelf=True)

        srcRootLen = len(srcPath)
        destRootLen = len(destPath)
        
        if destExists:
            if (isMove 
                or not destRes.isCollection 
                or not srcRes.isCollection ):
                # MOVE:
                # If a resource exists at the destination and the Overwrite 
                # header is "T", then prior to performing the move, the server 
                # MUST perform a DELETE with "Depth: infinity" on the 
                # destination resource.
                _logger.debug("Remove dest before move: '%s'" % destRes)
                destRes.delete()
                destRes = None
            else:
                # COPY collection over collection:
                # Remove destination files, that are not part of source, because 
                # source and dest collections must not be merged (9.8.4).
                # This is not the same as deleting the complete dest collection 
                # before copying, because that would also discard the history of 
                # existing resources.
                reverseDestList = destRes.getDescendants(depthFirst=True, addSelf=False)
                srcPathList = [ s.path for s in srcList ]
                _logger.debug("check srcPathList: %s" % srcPathList)
                for dRes in reverseDestList:
                    _logger.debug("check unmatched dest before copy: %s" % dRes)
                    relUrl = dRes.path[destRootLen:]
                    sp = srcPath + relUrl
                    if not sp in srcPathList:
                        _logger.debug("Remove unmatched dest before copy: %s" % dRes)
                        dRes.delete()
        
        # --- Let provider implement recursive move ----------------------------
        # We do this only, if the provider supports it, and no conflicts exist.
        # A provider can implement this very efficiently, without allocating
        # double memory as a copy/delete approach would.
        
        if isMove and srcRes.supportRecursiveMove(destPath): 
            hasConflicts = False
            for s in srcList:
                try:
                    self._evaluateIfHeaders(s, environ)
                except:
                    hasConflicts = True
                    break
            
            if not hasConflicts:
                try:
                    _logger.debug("Recursive move: %s -> '%s'" % (srcRes, destPath))
                    errorList = srcRes.moveRecursive(destPath)
                except Exception, e:
                    errorList = [ (srcRes.getHref(), asDAVError(e)) ]
                return self._sendResponse(environ, start_response, 
                                          srcRes, successCode, errorList)
        
        # --- Copy/move file-by-file using copy/delete -------------------------

        # We get here, if 
        # - the provider does not support recursive moves
        # - this is a copy request  
        #   In this case we would probably not win too much by a native provider
        #   implementation, since we had to handle single child errors anyway.
        # - the source tree is partially locked
        #   We would have to pass this information to the native provider.  
        
        # Hidden paths (paths of failed copy/moves) {<src_path>: True, ...}
        ignoreDict = {}
        
        for sRes in srcList:
            # Skip this resource, if there was a failure copying a parent 
            parentError = False
            for ignorePath in ignoreDict.keys():
                if util.isEqualOrChildUri(ignorePath, sRes.path):
                    parentError = True
                    break
            if parentError:
                _logger.debug("Copy: skipping '%s', because of parent error" % sRes.path)
                continue

            try:
                relUrl = sRes.path[srcRootLen:]
                dPath = destPath + relUrl
                
                self._evaluateIfHeaders(sRes, environ)
                
                # We copy resources and their properties top-down. 
                # Collections are simply created (without members), for
                # non-collections bytes are copied (overwriting target)
                sRes.copyMoveSingle(dPath, isMove)
                
                # If copy succeeded, and it was a non-collection delete it now.
                # So the source tree shrinks while the destination grows and we 
                # don't have to allocate the memory twice.
                # We cannot remove collections here, because we have not yet 
                # copied all children. 
                if isMove and not sRes.isCollection:
                    sRes.delete()
                    
            except Exception, e:
                ignoreDict[sRes.path] = True
                # TODO: the error-href should be 'most appropriate of the source 
                # and destination URLs'. So maybe this should be the destination
                # href sometimes.
                # http://www.webdav.org/specs/rfc4918.html#rfc.section.9.8.5
                errorList.append( (sRes.getHref(), asDAVError(e)) )

        # MOVE: Remove source tree (bottom-up)
        if isMove:
            reverseSrcList = srcList[:]
            reverseSrcList.reverse()
            util.status("Delete after move, ignore=", var=ignoreDict)
            for sRes in reverseSrcList:
                # Non-collections have already been removed in the copy loop.    
                if not sRes.isCollection:
                    continue
                # Skip collections that contain errors (unmoved resources)   
                childError = False
                for ignorePath in ignoreDict.keys():
                    if util.isEqualOrChildUri(sRes.path, ignorePath):
                        childError = True
                        break
                if childError:
                    util.status("Delete after move: skipping '%s', because of child error" % sRes.path)
                    continue

                try:
#                    _logger.debug("Remove source after move: %s" % sRes)
                    util.status("Remove collection after move: %s" % sRes)
                    sRes.delete()
                except Exception, e:
                    errorList.append( (srcRes.getHref(), asDAVError(e)) )
            util.status("ErrorList", var=errorList)
                
        # --- Return response --------------------------------------------------
         
        return self._sendResponse(environ, start_response, 
                                  srcRes, successCode, errorList)




    def doLOCK(self, environ, start_response):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_LOCK
        """
        path = environ["PATH_INFO"]
        provider = self._davProvider
        res = provider.getResourceInst(path, environ)
        lockMan = provider.lockManager

        if lockMan is None:
            # http://www.webdav.org/specs/rfc4918.html#rfc.section.6.3
            self._fail(HTTP_NOT_IMPLEMENTED,
                       "This realm does not support locking.")
        if res and res.preventLocking():
            self._fail(HTTP_FORBIDDEN,
                       "This resource does not support locking.")

        if environ.setdefault("HTTP_DEPTH", "infinity") not in ("0", "infinity"):
            self._fail(HTTP_BAD_REQUEST, "Expected Depth: 'infinity' or '0'.")
        
        self._evaluateIfHeaders(res, environ)

        timeoutsecs = util.readTimeoutValueHeader(environ.get("HTTP_TIMEOUT", ""))
        submittedTokenList = environ["wsgidav.ifLockTokenList"]

        lockinfoEL = util.parseXmlBody(environ, allowEmpty=True)
        
        # --- Special case: empty request body ---------------------------------
        
        if lockinfoEL is None:
            # TODO: @see 9.10.2
            # TODO: 'URL of a resource within the scope of the lock'
            #       Other (shared) locks are unaffected and don't prevent refreshing   
            # TODO: check for valid user
            # TODO: check for If with single lock token
            environ["HTTP_DEPTH"] = "0"  # MUST ignore depth header on refresh

            if res is None:
                self._fail(HTTP_BAD_REQUEST, 
                           "LOCK refresh must specify an existing resource.")
            if len(submittedTokenList) != 1:
                self._fail(HTTP_BAD_REQUEST, 
                           "Expected a lock token (only one lock may be refreshed at a time).")
            elif not lockMan.isUrlLockedByToken(res.getRefUrl(), submittedTokenList[0]):
                self._fail(HTTP_PRECONDITION_FAILED, 
                           "Lock token does not match URL.",
                           errcondition=PRECONDITION_CODE_LockTokenMismatch)
            # TODO: test, if token is owned by user
            
            lock = lockMan.refresh(submittedTokenList[0], timeoutsecs)
            
            # The lock root may be <path>, or a parent of <path>.
            lockPath = provider.refUrlToPath(lock["root"])
            lockRes = provider.getResourceInst(lockPath, environ)
            
            propEL = xml_tools.makePropEL()
            # TODO: handle exceptions in getPropertyValue
            lockdiscoveryEL = lockRes.getPropertyValue("{DAV:}lockdiscovery")
            propEL.append(lockdiscoveryEL)
               
            # Lock-Token header is not returned
            xml = xml_tools.xmlToString(propEL) 
            start_response("200 OK", [("Content-Type", "application/xml"),
                                      ("Content-Length", str(len(xml))),
                                      ("Date", util.getRfc1123Time()),
                                      ])
            return [ xml ]
             
        # --- Standard case: parse xml body ------------------------------------ 
        
        if lockinfoEL.tag != "{DAV:}lockinfo":
            self._fail(HTTP_BAD_REQUEST)   

        locktype = None
        lockscope = None
        lockowner = ""
        lockdepth = environ.setdefault("HTTP_DEPTH", "infinity")

        for linode in lockinfoEL:
            if linode.tag == "{DAV:}lockscope":
                for lsnode in linode:
                    if lsnode.tag == "{DAV:}exclusive": 
                        lockscope = "exclusive" 
                    elif lsnode.tag == "{DAV:}shared": 
                        lockscope = "shared" 
                    break               
            elif linode.tag == "{DAV:}locktype":
                for ltnode in linode:
                    if ltnode.tag == "{DAV:}write": 
                        locktype = "write"   # only type accepted
                    break

            elif linode.tag == "{DAV:}owner":
                # Store whole <owner> tag, so we can use etree.XML() later
                lockowner = xml_tools.xmlToString(linode, pretty_print=False)

            else:
                self._fail(HTTP_BAD_REQUEST, "Invalid node '%s'." % linode.tag)

        if not lockscope:
            self._fail(HTTP_BAD_REQUEST, "Missing or invalid lockscope.") 
        if not locktype:
            self._fail(HTTP_BAD_REQUEST, "Missing or invalid locktype.") 
        
        if environ.get("wsgidav.debug_break"):
            pass # break point

        # TODO: check for locked parents BEFORE creating an empty child
        
        # http://www.webdav.org/specs/rfc4918.html#rfc.section.9.10.4    
        # Locking unmapped URLs: must create an empty resource
        createdNewResource = False
        if res is None:
            parentRes = provider.getResourceInst(util.getUriParent(path), environ)
            if not parentRes or not parentRes.isCollection:
                self._fail(HTTP_CONFLICT, "LOCK-0 parent must be a collection")
            res = parentRes.createEmptyResource(util.getUriName(path))
            createdNewResource = True

        # --- Check, if path is already locked ---------------------------------

        # May raise DAVError(HTTP_LOCKED):
        lock = lockMan.acquire(res.getRefUrl(), 
                               locktype, lockscope, lockdepth, 
                               lockowner, timeoutsecs, 
                               environ["wsgidav.username"], 
                               submittedTokenList)
            
        # Lock succeeded
        propEL = xml_tools.makePropEL()
        # TODO: handle exceptions in getPropertyValue
        lockdiscoveryEL = res.getPropertyValue("{DAV:}lockdiscovery")
        propEL.append(lockdiscoveryEL)
           
        respcode = "200 OK"
        if createdNewResource:
            respcode = "201 Created"

        xml = xml_tools.xmlToString(propEL)
        start_response(respcode, [("Content-Type", "application/xml"),
                                  ("Content-Length", str(len(xml))),
                                  ("Lock-Token", lock["token"]),
                                  ("Date", util.getRfc1123Time()),
                                  ])
        return [ xml ]

        # TODO: LOCK may also fail with HTTP_FORBIDDEN.
        #       In this case we should return 207 multi-status.
        #       http://www.webdav.org/specs/rfc4918.html#rfc.section.9.10.9
        #       Checking this would require to call res.preventLocking()
        #       recursively.
        
#        # --- Locking FAILED: return fault response 
#        if len(conflictList) == 1 and conflictList[0][0]["root"] == res.getRefUrl():
#            # If there is only one error for the root URL, send as simple error response
#            return util.sendStatusResponse(environ, start_response, conflictList[0][1]) 
#         
#        dictStatus = {}
#
#        for lockDict, e in conflictList:
#            dictStatus[lockDict["root"]] = e
#
#        if not res.getRefUrl() in dictStatus:
#            dictStatus[res.getRefUrl()] = DAVError(HTTP_FAILED_DEPENDENCY)
#
#        # Return multi-status fault response
#        multistatusEL = xml_tools.makeMultistatusEL()
#        for nu, e in dictStatus.items():
#            responseEL = etree.SubElement(multistatusEL, "{DAV:}response") 
#            etree.SubElement(responseEL, "{DAV:}href").text = nu
#            etree.SubElement(responseEL, "{DAV:}status").text = "HTTP/1.1 %s" % getHttpStatusString(e)
#            # TODO: all responses should have this(?):
#            if e.contextinfo:
#                etree.SubElement(multistatusEL, "{DAV:}responsedescription").text = e.contextinfo
#        
##        if responsedescription:
##            etree.SubElement(multistatusEL, "{DAV:}responsedescription").text = "\n".join(responsedescription)
#        
#        return util.sendMultiStatusResponse(environ, start_response, multistatusEL)




    def doUNLOCK(self, environ, start_response):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_UNLOCK
        """
        path = environ["PATH_INFO"]
        provider = self._davProvider
        res = self._davProvider.getResourceInst(path, environ)

        lockMan = provider.lockManager
        if lockMan is None:
            self._fail(HTTP_NOT_IMPLEMENTED, "This share does not support locking.")
        elif util.getContentLength(environ) != 0:
            self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
                       "The server does not handle any body content.")
        elif not "HTTP_LOCK_TOKEN" in environ:
            self._fail(HTTP_BAD_REQUEST, "Missing lock token.")

        self._evaluateIfHeaders(res, environ)

        lockToken = environ["HTTP_LOCK_TOKEN"].strip("<>")
        refUrl = res.getRefUrl()

        if not lockMan.isUrlLockedByToken(refUrl, lockToken):
            self._fail(HTTP_CONFLICT,
                       "Resource is not locked by token.",
                       errcondition=PRECONDITION_CODE_LockTokenMismatch)
            
        if not lockMan.isTokenLockedByUser(lockToken, environ["wsgidav.username"]):
            # TODO: there must be a way to allow this for admins.
            #       Maybe test for "remove_locks" in environ["wsgidav.roles"]
            self._fail(HTTP_FORBIDDEN, "Token was created by another user.")

        # TODO: Is this correct?: unlock(a/b/c) will remove Lock for 'a/b' 
        lockMan.release(lockToken)

        return util.sendStatusResponse(environ, start_response, HTTP_NO_CONTENT)




    def doOPTIONS(self, environ, start_response):
        """
        @see http://www.webdav.org/specs/rfc4918.html#HEADER_DAV
        """
        path = environ["PATH_INFO"]
        provider = self._davProvider
        res = provider.getResourceInst(path, environ)

        headers = [("Content-Type", "text/html"),
                   ("Content-Length", "0"),
                   ("DAV", "1,2"),  # TODO: 10.1: 'OPTIONS MUST return DAV header with compliance class "1"'
                                    # TODO: 10.1: In cases where WebDAV is only supported in part of the server namespace, an OPTIONS request to non-WebDAV resources (including "/") SHOULD NOT advertise WebDAV support
                   ("Server", "DAV/2"),
                   ("Date", util.getRfc1123Time()),
                   ]
        
        if path == "/":
            path = "*"  # Hotfix for WinXP
            
        if path == "*":
            # Answer HTTP 'OPTIONS' method on server-level.
            # From RFC 2616
            # If the Request-URI is an asterisk ("*"), the OPTIONS request is 
            # intended to apply to the server in general rather than to a specific 
            # resource. Since a server's communication options typically depend on 
            # the resource, the "*" request is only useful as a "ping" or "no-op" 
            # type of method; it does nothing beyond allowing the client to test the 
            # capabilities of the server. For example, this can be used to test a 
            # proxy for HTTP/1.1 compliance (or lack thereof). 
            start_response("200 OK", headers)        
            return [""]  

        # TODO: should we have something like provider.isReadOnly() and then omit MKCOL PUT DELETE PROPPATCH COPY MOVE?
        # TODO: LOCK UNLOCK is only available, if lockmanager not None
        if res and res.isCollection:
            # Existing collection
            headers.append( ("Allow", "OPTIONS HEAD GET DELETE PROPFIND PROPPATCH COPY MOVE LOCK UNLOCK") )
        elif res:
            # Existing resource
            headers.append( ("Allow", "OPTIONS HEAD GET PUT DELETE PROPFIND PROPPATCH COPY MOVE LOCK UNLOCK") )
            if res.supportRanges(): 
                headers.append( ("Allow-Ranges", "bytes") )
        elif provider.isCollection(util.getUriParent(path), environ):
            # A new resource below an existing collection
            # TODO: should we allow LOCK here? I think it is allowed to lock an non-existing resource
            headers.append( ("Allow", "OPTIONS PUT MKCOL") ) 
        else:
            self._fail(HTTP_NOT_FOUND)

        start_response("200 OK", headers)        
        return [""]




    def doGET(self, environ, start_response):
        return self._sendResource(environ, start_response, isHeadMethod=False)


    def doHEAD(self, environ, start_response):
        return self._sendResource(environ, start_response, isHeadMethod=True)


    def _sendResource(self, environ, start_response, isHeadMethod):
        """
        If-Range     
            If the entity is unchanged, send me the part(s) that I am missing; 
            otherwise, send me the entire new entity     
            If-Range: "737060cd8c284d8af7ad3082f209582d"
            
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.27
        """
        path = environ["PATH_INFO"]
        res = self._davProvider.getResourceInst(path, environ)

        if util.getContentLength(environ) != 0:
            self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
                       "The server does not handle any body content.")
        elif environ.setdefault("HTTP_DEPTH", "0") != "0":
            self._fail(HTTP_BAD_REQUEST, "Only Depth: 0 supported.") 
        elif res is None:
            self._fail(HTTP_NOT_FOUND)         
        elif res.isCollection: 
            self._fail(HTTP_FORBIDDEN, 
                       "Directory browsing not enabled (WsgiDavDirBrowser middleware may be enabled using the dir_browser option).")         

        self._evaluateIfHeaders(res, environ)

        filesize = res.getContentLength()
        if filesize is None: 
            filesize = -1 # flag logic to read until EOF
            
        lastmodified = res.getLastModified()            
        if lastmodified is None: 
            lastmodified = -1
         
        entitytag = res.getEtag()         
        if entitytag is None:
            entitytag = "[]"

        ## Ranges      
        doignoreranges = (not res.supportContentLength() 
                          or not res.supportRanges()
                          or filesize == 0)
        if "HTTP_RANGE" in environ and "HTTP_IF_RANGE" in environ and not doignoreranges:
            ifrange = environ["HTTP_IF_RANGE"]
            # Try as http-date first (Return None, if invalid date string)
            secstime = util.parseTimeString(ifrange)
            if secstime:
                if lastmodified != secstime:
                    doignoreranges = True
            else:
                # Use as entity tag
                ifrange = ifrange.strip("\" ")
                if entitytag is None or ifrange != entitytag:
                    doignoreranges = True

        ispartialranges = False
        if "HTTP_RANGE" in environ and not doignoreranges:
            ispartialranges = True
            listRanges, _totallength = util.obtainContentRanges(environ["HTTP_RANGE"], filesize)
            if len(listRanges) == 0:
                #No valid ranges present
                self._fail(HTTP_RANGE_NOT_SATISFIABLE)

            # More than one range present -> take only the first range, since 
            # multiple range returns require multipart, which is not supported         
            # obtainContentRanges supports more than one range in case the above 
            # behaviour changes in future
            (rangestart, rangeend, rangelength) = listRanges[0]
        else:
            (rangestart, rangeend, rangelength) = (0L, filesize - 1, filesize)

        ## Content Processing 
        mimetype = res.getContentType()  #provider.getContentType(path)

        responseHeaders = []
        if res.supportContentLength():
            # Content-length must be of type string (otherwise CherryPy server chokes) 
            responseHeaders.append(("Content-Length", str(rangelength)))
        if res.supportModified():
            responseHeaders.append(("Last-Modified", util.getRfc1123Time(lastmodified)))
        responseHeaders.append(("Content-Type", mimetype))
        responseHeaders.append(("Date", util.getRfc1123Time()))
        if res.supportEtag():
            responseHeaders.append(("ETag", '"%s"' % entitytag))
 
        if ispartialranges:
#            responseHeaders.append(("Content-Ranges", "bytes " + str(rangestart) + "-" + str(rangeend) + "/" + str(rangelength)))
            responseHeaders.append(("Content-Range", "bytes %s-%s/%s" % (rangestart, rangeend, filesize)))
            start_response("206 Partial Content", responseHeaders)   
        else:
            start_response("200 OK", responseHeaders)

        # Return empty body for HEAD requests
        if isHeadMethod:
            yield ""
            return

        fileobj = res.getContent()

        if not doignoreranges:
            fileobj.seek(rangestart)

        contentlengthremaining = rangelength
        while 1:
            if contentlengthremaining < 0 or contentlengthremaining > BLOCK_SIZE:
                readbuffer = fileobj.read(BLOCK_SIZE)
            else:
                readbuffer = fileobj.read(contentlengthremaining)
            yield readbuffer
            contentlengthremaining -= len(readbuffer)
            if len(readbuffer) == 0 or contentlengthremaining == 0:
                break
        fileobj.close()
        return




#    def doTRACE(self, environ, start_response):
#        """ TODO: TRACE pending, but not essential."""
#        self._fail(HTTP_NOT_IMPLEMENTED)
