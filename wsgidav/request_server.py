# -*- coding: iso-8859-1 -*-

"""
request_server
==============

:Author: Ho Chun Wei, fuzzybr80(at)gmail.com (author of original PyFileServer)
:Author: Martin Wendt, moogle(at)wwwendt.de 
:Copyright: Lesser GNU Public License, see LICENSE file attached with package


WSGI application that handles one single WebDAV request.

See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
"""
from pprint import pprint
from urlparse import urlparse
import socket
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

import lock_manager

# Trick PyDev to do intellisense and don't produce warnings:
from util import etree #@UnusedImport
if False: from xml.etree import ElementTree as etree     #@Reimport
   
__docformat__ = "reStructuredText"

_logger = util.getModuleLogger(__name__)

BLOCK_SIZE = 8192



# TODO: use this?
#class _FileIter(object):
##        From paste.fileapp.py
#
#    def __init__(self, file, block_size=None, size=None):
#        self.file = file
#        self.size = size
#        self.block_size = block_size or BLOCK_SIZE
#
#    def __iter__(self):
#        return self
#
#    def next(self):
#        chunk_size = self.block_size
#        if self.size is not None:
#            if chunk_size > self.size:
#                chunk_size = self.size
#            self.size -= chunk_size
#        data = self.file.read(chunk_size)
#        if not data:
#            raise StopIteration
#        return data
#
#    def close(self):
#        self.file.close()



class RequestServer(object):

    def __init__(self, davProvider):
        self._davProvider = davProvider
        self.allowPropfindInfinite = True
        self._verbose = 2
        util.debug("sc", "RequestServer: __init__")

    def __del__(self):
        util.debug("sc", "RequestServer: __del__")

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

        # Dispatch HTTP request methods to 'doMETHOD()' handlers
        method = getattr(self, "do%s" % requestmethod, None)
        if not method:
            self._fail(HTTP_METHOD_NOT_ALLOWED)

        if environ.get("wsgidav.debug_break"):
            pass # Set a break point here
            
        for v in method(environ, start_response):
            util.debug("sc", "RequestServer: yield start")
            yield v
            util.debug("sc", "RequestServer: yield end")
        return
#        return method(environ, start_response)


    def _fail(self, value, contextinfo=None, srcexception=None, preconditionCode=None):
        """Wrapper to raise (and log) DAVError."""
        if isinstance(value, Exception):
            e = asDAVError(value)
        else:  
            e = DAVError(value, contextinfo, srcexception, preconditionCode)
        util.log("Raising DAVError %s" % e.getUserInfo())
        raise e



    def _checkWritePermission(self, res, depth, environ):
        """Check, if write access is allowed, otherwise raise DAVError."""
        lockMan = self._davProvider.lockManager
        if lockMan is None or res is None:
            return True

        refUrl = res.getRefUrl()
        
        if "wsgidav.conditions.if" not in environ:
            util.parseIfHeaderDict(environ)

        conflictList = lockMan.checkAccessPermission(refUrl, 
                                                     environ["wsgidav.ifLockTokenList"], 
                                                     "write", 
                                                     depth, 
                                                     environ["wsgidav.username"])

        # If any conflict was detected, raise one of them
        for _lock, e in conflictList:
            raise e
        return




    def _evaluateIfHeaders(self, res, environ):
        """Apply HTTP headers on <path>, raising DAVError if conditions fail.
         
        Add environ['wsgidav.conditions.if'] and environ['wsgidav.ifLockTokenList'].
        Handle these headers:
        
          - If-Match, If-Modified-Since, If-None-Match, If-Unmodified-Since:
            Raising HTTP_PRECONDITION_FAILED or HTTP_NOT_MODIFIED
          - If:
            Raising HTTP_PRECONDITION_FAILED

        @see http://www.webdav.org/specs/rfc2518.html#HEADER_If
        @see util.evaluateHTTPConditionals
        """
        # Bail out, if res doeas not exist
        if res is None:
            return

        # Add parsed If header to environ
        if "wsgidav.conditions.if" not in environ:
            util.parseIfHeaderDict(environ)
        ifDict = environ["wsgidav.conditions.if"]

        # Raise HTTP_PRECONDITION_FAILED or HTTP_NOT_MODIFIED, if standard 
        # HTTP condition fails
        lastmodified = -1 # nonvalid modified time
        entitytag = "[]" # Non-valid entity tag
        if res.modified() is not None:
            lastmodified = res.modified()            
        if res.etag() is not None:
            entitytag = res.etag()            

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
        res = self._davProvider.getResourceInst(path)

        # RFC: By default, the PROPFIND method without a Depth header MUST act as if a "Depth: infinity" header was included.
        environ.setdefault("HTTP_DEPTH", "infinity")
        if not environ["HTTP_DEPTH"] in ("0", "1", "infinity"):            
            self._fail(HTTP_BAD_REQUEST, 
                       "Invalid Depth header: '%s'." % environ["HTTP_DEPTH"])

        if environ["HTTP_DEPTH"] == "infinity" and not self.allowPropfindInfinite:
            self._fail(HTTP_FORBIDDEN, 
                       "PROPFIND 'infinite' was disabled for security reasons.",
                       preconditionCode=PRECONDITION_CODE_PropfindFiniteDepth)    

        if res is None:
            self._fail(HTTP_NOT_FOUND)
        
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
                if propFindMode: # RFC: allprop and propname are mutually exclusive
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
        if environ["wsgidav.verbose"] >= 3:
            pprint(reslist, indent=4)
        
        # TODO: get additional namespace mapping from provider.getNamespaceMap()?
        multistatusEL = util.makeMultistatusEL()
        responsedescription = []
        
        for child in reslist:

            if propFindMode == "allprop": 
                propList = child.getProperties(mode="allprop")
            elif propFindMode == "propname":
                propList = child.getProperties(mode="propname", namesOnly=True)
            else:
                propList = child.getProperties(mode="named", nameList=propNameList)

            href = child.getHref()
            # TODO: OK?:
#            href = href.decode("iso_8859_1")  # Convert to unicode, because ASCII is not enough, and iso_8859_1 is not allowed for lxml

            util.addPropertyResponse(multistatusEL, href, propList)

        if responsedescription:
            etree.SubElement(multistatusEL, "{DAV:}responsedescription").text = "\n".join(responsedescription)
            
#        print util.xmlToString(multistatusEL, pretty_print=True)
        return util.sendMultiStatusResponse(environ, start_response, multistatusEL)




    def doPROPPATCH(self, environ, start_response):
        """Handle PROPPATCH request to set or remove a property.
        
        @see http://www.webdav.org/specs/rfc4918.html#METHOD_PROPPATCH
        """
        path = environ["PATH_INFO"]
        res = self._davProvider.getResourceInst(path)

        # Only accept Depth: 0 (but assume this, if omitted)
        environ.setdefault("HTTP_DEPTH", "0")
        if environ["HTTP_DEPTH"] != "0":
            self._fail(HTTP_BAD_REQUEST, "Depth must be '0'.")
        
        if res is None:
            self._fail(HTTP_NOT_FOUND)

        self._evaluateIfHeaders(res, environ)
        # TODO: some properties may not be affected by locks?
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
        multistatusEL = util.makeMultistatusEL()
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
#        res = provider.getResourceInst(path)

        # Do not understand ANY request body entities
        if util.getContentLength(environ) != 0:
            self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
                       "The server does not handle any body content.")

        # Only accept Depth: 0 (but assume this, if omitted)
        if environ.setdefault("HTTP_DEPTH", "0") != "0":
            self._fail(HTTP_BAD_REQUEST, "Depth must be '0'.")
        
        if provider.exists(path):
            self._fail(HTTP_METHOD_NOT_ALLOWED,
                       "MKCOL can only be executed on an unmapped URL.")         

        parentRes = provider.getResourceInst(util.getUriParent(path))
        if not parentRes or not parentRes.isCollection():
            self._fail(HTTP_CONFLICT, "Parent must be an existing collection.")          

        # TODO: should we check If headers here?
#        self._evaluateIfHeaders(res, environ)
        # Check for write permissions on the PARENT
        self._checkWritePermission(parentRes, "0", environ)

        parentRes.createCollection(util.getUriName(path))

        return util.sendSimpleResponse(environ, start_response, HTTP_CREATED)



    
    # TODO: implement POST? See RFC 9.5 'POST for collections'
#    def doPOST(self, environ, start_response):
#        # @see http://www.webdav.org/specs/rfc4918.html#METHOD_POST
#        self._fail(processrequesterrorhandler.HTTP_METHOD_NOT_ALLOWED)         



    
    def doDELETE(self, environ, start_response):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_DELETE
        """
        path = environ["PATH_INFO"]
        provider = self._davProvider
        res = provider.getResourceInst(path)

        # Do not understand ANY request body entities
        if util.getContentLength(environ) != 0:
            self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
                       "The server does not handle any body content.")
        
        if res is None:
            self._fail(HTTP_NOT_FOUND)         

        if res.isCollection(): 
            # Delete over collection
            # "The DELETE method on a collection MUST act as if a "Depth: infinity" header was used on it. 
            # A client MUST NOT submit a Depth header with a DELETE on a collection with any value but infinity."
            if environ.setdefault("HTTP_DEPTH", "infinity") != "infinity":
                self._fail(HTTP_BAD_REQUEST,
                           "Only Depth: infinity is supported for collections.")         
        else:
            # TODO: should we default to '0', or raise if no Depth is given?
            if environ.setdefault("HTTP_DEPTH", "0") != "0":
                self._fail(HTTP_BAD_REQUEST,
                           "Only Depth: 0 is supported for resources.")         

        self._evaluateIfHeaders(res, environ)
        self._checkWritePermission(res, environ["HTTP_DEPTH"], environ)

        # Get a list of all resources (parents after children, so we can remove 
        # them in that order)
        childList = res.getDescendants(depthFirst=True, depth=environ["HTTP_DEPTH"], addSelf=True)

        dictError = {} # Errors in deletion; { <ref-url>: <DAVError>, ... } 
        dictHidden = {}  # Hidden errors, ancestors of failed deletes {<path>: ""}
        for childRes in childList:
            if childRes.path in dictHidden:
#                dictHidden[provider.getParent(childPath)] = ""
                dictHidden[childRes.getParentPath()] = ""
                continue            
            try:
                # 9.6.1.: Any headers included with delete must be applied in processing every resource to be deleted
                self._evaluateIfHeaders(childRes, environ)
#                self._checkWritePermission(childRes, environ["HTTP_DEPTH"], environ)
                childRes.remove()
                
            except Exception, e:
                dictError[childRes.getHref()] = asDAVError(e)
                dictHidden[childRes.getParentPath()] = ""

            else:
                # Double-check, if deletion succeeded
                if provider.exists(childRes.path) and childRes.getHref() not in dictError:
                    dictError[childRes.getHref()] = DAVError(HTTP_INTERNAL_ERROR, 
                                                             "Resource could not be deleted.")
                    dictHidden[childRes.getParentPath()] = ""

        # Send response
        if len(dictError) == 1 and res.getHref() in dictError:
            return util.sendSimpleResponse(environ, start_response, dictError[res.getHref()])
        
        elif len(dictError) > 0:
            multistatusEL = util.makeMultistatusEL()
            
            for refurl, e in dictError.items():
                responseEL = etree.SubElement(multistatusEL, "{DAV:}response") 
                etree.SubElement(responseEL, "{DAV:}href").text = refurl
                etree.SubElement(responseEL, "{DAV:}status").text = "HTTP/1.1 %s" % getHttpStatusString(e)

            return util.sendMultiStatusResponse(environ, start_response, multistatusEL)
        # Status OK
        return util.sendSimpleResponse(environ, start_response, HTTP_NO_CONTENT)




    def doPUT(self, environ, start_response):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_PUT
        """
        # @@: As noted in request_resolver.py, this should just be using
        # PATH_INFO, and the object should have path as an
        # argument to the constructor.  This is a larger architectural
        # issue, not fixed trivially, but it will make this interact
        # much better with other WSGI components
        path = environ["PATH_INFO"]
        provider = self._davProvider
        res = provider.getResourceInst(path)
        parentRes = provider.getResourceInst(util.getUriParent(path))
        
        isnewfile = res is None

        ## Test for unsupported stuff
        if "HTTP_CONTENT_ENCODING" in environ:
            self._fail(HTTP_NOT_IMPLEMENTED,
                       "Content-encoding header is not supported.")
        if "HTTP_CONTENT_RANGE" in environ:
            self._fail(HTTP_NOT_IMPLEMENTED,
                       "Content-range header is not supported.")

        if res and res.isCollection():
            self._fail(HTTP_METHOD_NOT_ALLOWED, "Cannot PUT to a collection")
        elif not parentRes.isCollection(): # TODO: allow parentRes==None?
            self._fail(HTTP_CONFLICT, "PUT parent must be a collection")

        self._evaluateIfHeaders(res, environ)

        if isnewfile:
            self._checkWritePermission(parentRes, "0", environ)
        else:
            self._checkWritePermission(res, "0", environ)

        ## Start Content Processing
        # Content-Length may be 0 or greater. (Set to -1 if missing or invalid.) 
        WORKAROUND_BAD_LENGTH = True
        try:
            contentlength = max(-1, long(environ.get("CONTENT_LENGTH", -1)))
        except ValueError: 
            contentlength = -1
        
        if contentlength < 0 and not WORKAROUND_BAD_LENGTH:
            self._fail(HTTP_BAD_REQUEST, 
                       "PUT request with invalid Content-Length: (%s)" % environ.get("CONTENT_LENGTH"))
        
        try:      
            fileobj = res.openResourceForWrite(contenttype=environ.get("CONTENT_TYPE"))

            if environ.get("HTTP_TRANSFER_ENCODING", "").lower() == "chunked":
                l = int(environ["wsgi.input"].readline(), 16)
                while l > 0:
                    buf = environ["wsgi.input"].read(l)
                    fileobj.write(buf)
                    environ["wsgi.input"].readline()
                    l = int(environ["wsgi.input"].readline(), 16)
                    
            elif contentlength == 0:
                # XP and Vista MiniRedir submit PUT with Content-Length 0, 
                # before LOCK and the real PUT. So we have to accept this. 
                # TODO: review this
                _logger.info("PUT: Content-Length == 0. Creating empty file...")
                
            elif contentlength < 0:
                # If CONTENT_LENGTH is invalid, we may try to workaround this
                # by reading until the end of the stream. This may block however!
                # The iterator produced small chnunks of varying size, but not
                # sure, if we always get everything before it times out.
                # TODO: review this
                _logger.warning("PUT with invalid Content-Length (%s). Trying to read all (this may timeout)..." % environ.get("CONTENT_LENGTH"))
                nb = 0
                try:
                    for s in environ["wsgi.input"]:
                        _logger.debug("PUT: read from wsgi.input.__iter__, len=%s" % len(s))
                        fileobj.write(s)
                        nb += len (s)
                except socket.timeout:
                    _logger.warning("PUT: input timed out after writing %s bytes" % nb)
                    
            else:
                assert contentlength > 0
                contentremain = contentlength
                while contentremain > 0:
                    n = min(contentremain, BLOCK_SIZE)
                    readbuffer = environ["wsgi.input"].read(n)
                    fileobj.write(readbuffer)
                    contentremain -= len(readbuffer)
                     
            fileobj.close()

        except Exception, e:
            _logger.exception("PUT: byte copy failed")
            self._fail(e)

        if isnewfile:
            return util.sendSimpleResponse(environ, start_response, HTTP_CREATED)
        return util.sendSimpleResponse(environ, start_response, HTTP_NO_CONTENT)




    def doCOPY(self, environ, start_response):
        return self._copyOrMove(environ, start_response, False)




    def doMOVE(self, environ, start_response):
        return self._copyOrMove(environ, start_response, True)




    def _copyOrMove(self, environ, start_response, isMove):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_COPY
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_MOVE
        """
        provider = self._davProvider
        srcPath = environ["PATH_INFO"]
        srcRes = provider.getResourceInst(srcPath)

        propMan = provider.propManager

        if srcRes is None:
            self._fail(HTTP_NOT_FOUND)         
        if "HTTP_DESTINATION" not in environ:
            self._fail(HTTP_BAD_REQUEST, "Missing required Destination header.")
        if not environ.setdefault("HTTP_OVERWRITE", "T") in ("T", "F"):
            self._fail(HTTP_BAD_REQUEST, "Invalid Overwrite header.")
        if util.getContentLength(environ) != 0:
            # RFC 2518 defined support for <propertybehavior>.
            # This was dropped with RFC 4918. 
            # Still clients may send it (e.g. DAVExplorer 0.9.1 File-Copy) sends 
            # <A:propertybehavior xmlns:A="DAV:"> <A:keepalive>*</A:keepalive> </A:propertybehavior>
            _logger.warning("Ignored copy/move  body: %s" % environ["wsgi.input"].read(util.getContentLength(environ)))
#            self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
#                       "The server does not handle any body content.")
        
        isCollection = srcRes.isCollection()
        if isCollection:
            # The COPY method on a collection without a Depth header MUST act as 
            # if a Depth header with value "infinity" was included. 
            # A client may submit a Depth header on a COPY on a collection with 
            # a value of "0" or "infinity". 
            if not environ.setdefault("HTTP_DEPTH", "infinity") in ("0", "infinity"):
                self._fail(HTTP_BAD_REQUEST, "Invalid Depth header for collection.")
        else:
            # It's an existing resource, only accept Depth 0
            
            # TODO: correct logic? ( litmus 'copymove: 3 (copy_simple)' seems to 
            # send 'infinity' for a simple resource)
            if environ.get("HTTP_DEPTH") == "infinity":
                environ["HTTP_DEPTH"] = "0"
            
            if environ.setdefault("HTTP_DEPTH", "0") != "0":
                self._fail(HTTP_BAD_REQUEST, "Invalid Depth header for resource.")

        ## Get destination path and check for cross-realm access
        # TODO: We could turn a copy across realms into a PUT (reusing the credentials we have)

        # Destination header may be quoted (e.g. DAV Explorer sends unquoted, Windows quoted)
        destinationHeader = urllib.unquote(environ["HTTP_DESTINATION"])
        
        destScheme, destNetloc, destPath, \
        _destParams, _destQuery, _destFrag = urlparse(destinationHeader, 
                                                      allow_fragments=False) # Return fragments as part of <path>

#        util.log("COPY: destPath='%s'" % destPath)
        if isCollection:
            destPath = destPath.rstrip("/") + "/"
        
        if destScheme and destScheme.lower() != environ["wsgi.url_scheme"].lower():
            self._fail(HTTP_BAD_GATEWAY,
                       "Source and destination must have the same scheme.")
        elif destNetloc and destNetloc.lower() != environ["HTTP_HOST"].lower():
            # TODO: this should consider environ["SERVER_PORT"] also
            self._fail(HTTP_BAD_GATEWAY,
                       "Source and destination must have the same host name.")
        elif not destPath.startswith(provider.mountPath + provider.sharePath):
            # Inter-realm copying not supported, since its not possible to authentication-wise
            self._fail(HTTP_BAD_GATEWAY, 
                       "Inter-realm copy/move is not supported.")

        destPath = destPath[len(provider.mountPath + provider.sharePath):]
        assert destPath.startswith("/")

        destRes = provider.getResourceInst(destPath)
        destExists = destRes is not None
        
        # destPath is now relative to current mount/share starting with '/'
#        util.log("COPY  -> destPath='%s'" % destPath)

        destParentRes = provider.getResourceInst(util.getUriParent(destPath))
        
        if not destParentRes or not destParentRes.isCollection():
            self._fail(HTTP_CONFLICT, "Parent must be a collection.")

        self._evaluateIfHeaders(srcRes, environ)
        self._evaluateIfHeaders(destRes, environ)
        if isMove:
            self._checkWritePermission(srcRes, "infinity", environ)
#            self._checkWritePermission(srcParentRes, "infinity", environ) # TODO: really?
        self._checkWritePermission(destRes, environ["HTTP_DEPTH"], environ)
#        self._checkWritePermission(destParentRes, environ["HTTP_DEPTH"], environ) # TODO: really?

        if srcPath == destPath:
            self._fail(HTTP_FORBIDDEN, "Cannot copy/move source onto itself")
        elif util.isEqualOrChildUri(srcPath, destPath):
            self._fail(HTTP_FORBIDDEN, "Cannot copy/move source below itself")

        if destExists and environ["HTTP_OVERWRITE"] != "T":
            self._fail(HTTP_PRECONDITION_FAILED,
                       "Target already exists and Overwrite is set to false")


        srcRootLen = len(srcPath)
        destRootLen = len(destPath)
        
        srcList = srcRes.getDescendants(addSelf=True)
        srcPathList = [ s.path for s in srcList ]

        # --- Cleanup target collection ----------------------------------------
        # TODO: double-check this: This must be bullet proof, otherwise unwanted files may be deleted
        if destExists and environ["HTTP_DEPTH"] == "infinity":
            # TODO: we don't delete destination collection members when depth==0, OK? 
            if isMove:
                # MOVE:
                # If a resource exists at the destination and the Overwrite header is "T", 
                # then prior to performing the move, the server MUST perform a 
                # DELETE with "Depth: infinity" on the destination resource. 
                destList = destRes.getDescendants(depthFirst=True, addSelf=True)
                for dRes in destList:
                    if environ["wsgidav.verbose"] >= 2:
                        _logger.debug("Remove dest before move: '%s'" % dRes)
                    dRes.remove()
            else:
                # COPY:
                # Remove destination files, that are not part of source, because source 
                # and dest collections must not be merged (9.8.4).
                # This is not the same as deleting the complete dest collection 
                # before copying, because that would also discard the history of 
                # existing resources.
                destList = destRes.getDescendants(depthFirst=True, addSelf=False)
                for dRes in destList:
                    relUrl = dRes.path[destRootLen:]
                    sp = srcPath + relUrl
                    if not sp in srcPathList:
                        if environ["wsgidav.verbose"] >= 2:
                            _logger.debug("Remove unmatched dest before copy: '%s'" % dRes)
                        dRes.remove()
        
        # --- Copy/move from source to dest ------------------------------------ 
        dictError = {}
        for sRes in srcList:
            relUrl = sRes.path[srcRootLen:]
#            dRes = provider.getResourceInst(destPath + relUrl)
            dPath = destPath + relUrl
            
            # Skip, if there was already an error while processing the parent
            parentError = False
            for errUrl in dictError.keys():
                if dPath.startswith(errUrl):  # TODO: util.isChildUri(parent, child)
                    parentError = True
                    break
            if parentError:
                _logger.debug("Copy: skipping '%s', because of parent error" % dRes)
                continue
            
            try:
                self._evaluateIfHeaders(sRes, environ)
                
                # TODO: support  native MOVE in DAVProvider
                # MOVE is frequently used by clients to rename a file without 
                # changing its parent collection, so it's not appropriate to 
                # reset all live properties that are set at resource creation. 
                # For example, the DAV:creationdate property value SHOULD remain 
                # the same after a MOVE.

                if sRes.isCollection():
                    if not dRes.exists():
                        if environ["wsgidav.verbose"] >= 2:
                            _logger.debug("Create collection '%s'" % dPath)
                        provider.createCollection(dPath)
                    else:
                        _logger.debug("Skipping existing collection '%s'" % dRes)
                else:   
                    if environ["wsgidav.verbose"] >= 2:
                        _logger.debug("Copy '%s' -> '%s'" % (sRes, dRes))
                    # AL can delete/write or do an in-place overwrite
                    sRes.copyResource(dPath)

                if propMan:
                    refS = sRes.getRefUrl()
                    refD = dRes.getRefUrl()
                    propMan.copyProperties(refS, refD)     

            except Exception, e:
                dictError[dPath] = asDAVError(e)

        if isMove:
            # MOVE: Remove source
            # TODO: this is what PyFileServer 0.2 implemented. 
            # We should add native move-support to DAVProvider instead. 
            srcList = srcRes.getDescendants(depthFirst=True, addSelf=True)
            for sRes in srcList:
                _logger.debug("Remove source after move '%s'" % sRes)
                # TODO: try/except:
                sRes.remove()

        # Return error response
        if len(dictError) == 1 and destPath in dictError:
            return util.sendSimpleResponse(environ, start_response, dictError[destPath])
        elif len(dictError) > 0:
            # Multi-value result should not contain 424 (Failed Dependency), 201 or 204 
            multistatusEL = util.makeMultistatusEL()
            
            for url, e in dictError.items():
                responseEL = etree.SubElement(multistatusEL, "{DAV:}response") 
                href = self._davProvider.getResourceInst(url).getHref()
                etree.SubElement(responseEL, "{DAV:}href").text = href
                etree.SubElement(responseEL, "{DAV:}status").text = "HTTP/1.1 %s" % getHttpStatusString(e)
                # TODO: add e.strerror to <responsedescription>

            return util.sendMultiStatusResponse(environ, start_response, multistatusEL)
        # Return OK
        if destExists:
            return util.sendSimpleResponse(environ, start_response, HTTP_NO_CONTENT)
        return util.sendSimpleResponse(environ, start_response, HTTP_CREATED)




    def doLOCK(self, environ, start_response):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_LOCK
        """
        path = environ["PATH_INFO"]
        provider = self._davProvider
        res = provider.getResourceInst(path)
        lockMan = provider.lockManager
        
        if lockMan is None:
            # http://www.webdav.org/specs/rfc4918.html#rfc.section.6.3
            # TODO: is this the correct status code?
            self._fail(HTTP_NOT_IMPLEMENTED,
                       "This realm does not support locking.")

        if environ.setdefault("HTTP_DEPTH", "infinity") not in ("0", "infinity"):
            self._fail(HTTP_BAD_REQUEST, "Expected Depth: 'infinity' or '0'.")
        
        self._evaluateIfHeaders(res, environ)

#        resourceExists = res.exists()
        refUrl = res.getRefUrl()
        timeoutsecs = lock_manager.readTimeoutValueHeader(environ.get("HTTP_TIMEOUT", ""))
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
            elif not lockMan.isUrlLockedByToken(refUrl, submittedTokenList[0]):
                self._fail(HTTP_BAD_REQUEST, "Lock token does not match URL.")
            # TODO: test, if token is owned by user

            lock = lockMan.refresh(submittedTokenList[0], timeoutsecs)
            
            # The lock root may be <path>, or a parent of <path>.
            lockPath = provider.refUrlToPath(lock["root"])
            lockRes = provider.getResourceInst(lockPath)
            
            propEL = util.makePropEL()
            # TODO: handle exceptions in getPropertyValue
            lockdiscoveryEL = lockRes.getPropertyValue("{DAV:}lockdiscovery")
            propEL.append(lockdiscoveryEL)
               
#            print "LOCK", lockPath
#            print util.xmlToString(propEL, pretty_print=True)

            # Lock-Token header is not returned 
            start_response("200 OK", [("Content-Type","application/xml"),
                                      ("Date", util.getRfc1123Time()),
                                      ])
            return ["<?xml version='1.0' encoding='UTF-8' ?>", 
                    util.xmlToString(propEL, pretty_print=True) 
                    ]
            
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
                lockowner = util.xmlToString(linode, pretty_print=False)

            else:
                self._fail(HTTP_BAD_REQUEST, "Invalid node '%s'." % linode.tag)

        if not lockscope:
            self._fail(HTTP_BAD_REQUEST, "Missing or invalid locksope.") 
        if not locktype:
            self._fail(HTTP_BAD_REQUEST, "Missing or invalid locktype.") 
        
        # --- Check, if path is already locked ---------------------------
#        print "LOCK.ac", refUrl

        # TODO: lock.acquire should be easier to test for 'success' 
        
        lockResultList = lockMan.acquire(refUrl, 
                                         locktype, lockscope, lockdepth, lockowner, timeoutsecs, 
                                         environ["wsgidav.username"], 
                                         submittedTokenList)

        resourceExists = (res is not None)
        # http://www.webdav.org/specs/rfc4918.html#rfc.section.9.10.4    
        # Locking unmapped URLs: must create an empty resource
        if not resourceExists:
            res = provider.createEmptyResource(path) 

        if environ.get("wsgidav.debug_break"):
            pass # break point
            
        lockToken = None 
        if len(lockResultList) == 1 and lockResultList[0][1] is None:
            # Lock succeeded
            lockToken = lockResultList[0][0]
    
            propEL = util.makePropEL()
            # TODO: handle exceptions in getPropertyValue
            lockdiscoveryEL = res.getPropertyValue("{DAV:}lockdiscovery")
            propEL.append(lockdiscoveryEL)
               
            respcode = "200 OK"
            if not resourceExists:
                respcode = "201 Created"
    
            start_response(respcode, [("Content-Type", "application/xml"),
                                      ("Lock-Token", lockToken["token"]),
                                      ("Date", util.getRfc1123Time()),
                                      ])
            return ["<?xml version='1.0' encoding='UTF-8' ?>", # TODO: required?
                    util.xmlToString(propEL, pretty_print=True) ]

        # --- Locking FAILED: return fault response 
        if len(lockResultList) == 1 and lockResultList[0][0]["root"] == refUrl:
            # If there is only one error for the root URL, send as simple error response
            return util.sendSimpleResponse(environ, start_response, lockResultList[0][1]) 
         
        dictStatus = {}
        if not refUrl in lockResultList:  # FIXME: in doesn't work here
            dictStatus[refUrl] = DAVError(HTTP_FAILED_DEPENDENCY)

        for lockDict, e in lockResultList:
            dictStatus[lockDict["root"]] = e

        # Return multi-status fault response
        multistatusEL = util.makeMultistatusEL()
        for nu, e in dictStatus.items():
            responseEL = etree.SubElement(multistatusEL, "{DAV:}response") 
            etree.SubElement(responseEL, "{DAV:}href").text = nu
            etree.SubElement(responseEL, "{DAV:}status").text = "HTTP/1.1 %s" % getHttpStatusString(e)
            # TODO: all responses should have this(?):
            if e.contextinfo:
                etree.SubElement(multistatusEL, "{DAV:}responsedescription").text = e.contextinfo
        
#        if responsedescription:
#            etree.SubElement(multistatusEL, "{DAV:}responsedescription").text = "\n".join(responsedescription)
        
        return util.sendMultiStatusResponse(environ, start_response, multistatusEL)




    def doUNLOCK(self, environ, start_response):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#METHOD_UNLOCK
        """
        path = environ["PATH_INFO"]
        provider = self._davProvider
        res = self._davProvider.getResourceInst(path)

        lockMan = provider.lockManager
        if lockMan is None:
            self._fail(HTTP_NOT_IMPLEMENTED, "This realm does not support locking.")
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
                       preconditionCode=PRECONDITION_CODE_LockTokenMismatch)
            
        if not lockMan.isTokenLockedByUser(lockToken, environ["wsgidav.username"]):
            # TODO: there must be a way to allow this for admins.
            #       Maybe test for "remove_locks" in environ["wsgidav.roles"]
            self._fail(HTTP_FORBIDDEN, "Token was created by another user.")

        # TODO: Is this correct?: unlock(a/b/c) will remove Lock for 'a/b' 
        lockMan.release(lockToken)

        return util.sendSimpleResponse(environ, start_response, HTTP_NO_CONTENT)




    def doOPTIONS(self, environ, start_response):
        """
        @see http://www.webdav.org/specs/rfc4918.html#HEADER_DAV
        """
        path = environ["PATH_INFO"]
        provider = self._davProvider
        res = provider.getResourceInst(path)

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
        if res.isCollection():
            # Existing collection
            headers.append( ("Allow", "OPTIONS HEAD GET DELETE PROPFIND PROPPATCH COPY MOVE LOCK UNLOCK") )
        elif res.isResource():
            # Existing resource
            headers.append( ("Allow", "OPTIONS HEAD GET PUT DELETE PROPFIND PROPPATCH COPY MOVE LOCK UNLOCK") )
            if res.supportRanges(): 
                headers.append( ("Allow-Ranges", "bytes") )
        elif provider.isCollection(util.getUriParent(path)):
            # A new resource below an existing collection
            # TODO: should we allow LOCK here? I think it is allowed to lock an non-existin gresource
            headers.append( ("Allow", "OPTIONS PUT MKCOL") ) 
        else:
            self._fail(HTTP_NOT_FOUND)

        start_response("200 OK", headers)        
        return [""]




    def doGET(self, environ, start_response):
        return self._sendResource(environ, start_response, isHeadMethod=False)


    def doHEAD(self, environ, start_response):
        return self._sendResource(environ, start_response, isHeadMethod=True)

#    def get(self, environ, start_response):
#        """
#        From paste.fileapp.py
#        """
#        is_head = environ["REQUEST_METHOD"].upper() == "HEAD"
#        if "max-age=0" in CACHE_CONTROL(environ).lower():
#            self.update(force=True) # RFC 2616 13.2.6
#        else:
#            self.update()
#        if not self.content:
#            if not os.path.exists(self.filename):
#                exc = HTTPNotFound(
#                    "The resource does not exist",
#                    comment="No file at %r" % self.filename)
#                return exc(environ, start_response)
#            try:
#                file = open(self.filename, "rb")
#            except (IOError, OSError), e:
#                exc = HTTPForbidden(
#                    "You are not permitted to view this file (%s)" % e)
#                return exc.wsgi_application(
#                    environ, start_response)
#        retval = DataApp.get(self, environ, start_response)
#        if isinstance(retval, list):
#            # cached content, exception, or not-modified
#            if is_head:
#                return [""]
#            return retval
#        (lower, content_length) = retval
#        if is_head:
#            return [""]
#        file.seek(lower)
#        file_wrapper = environ.get("wsgi.file_wrapper", None)
#        if file_wrapper:
#            return file_wrapper(file, BLOCK_SIZE)
#        else:
#            return _FileIter(file, size=content_length)

    
    def _sendResource(self, environ, start_response, isHeadMethod):
        """
        If-Range     
            If the entity is unchanged, send me the part(s) that I am missing; 
            otherwise, send me the entire new entity     
            If-Range: "737060cd8c284d8af7ad3082f209582d"
            
        @see: http://www.w3.org/Protocols/rfc2616/rfc2616-sec14.html#sec14.27
        """
        path = environ["PATH_INFO"]
        res = self._davProvider.getResourceInst(path)

        if util.getContentLength(environ) != 0:
            self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
                       "The server does not handle any body content.")
        elif environ.setdefault("HTTP_DEPTH", "0") != "0":
            self._fail(HTTP_BAD_REQUEST, "Only Depth: 0 supported.") 
        elif res is None:
            self._fail(HTTP_NOT_FOUND)         
        elif res.isCollection(): 
            self._fail(HTTP_FORBIDDEN, 
                       "Directory browsing not supported (try the WsgiDavDirBrowser middleware).")         

        self._evaluateIfHeaders(res, environ)

        filesize = res.contentLength()
        if filesize is None: 
            filesize = -1 # flag logic to read until EOF
            
        lastmodified = res.modified()            
        if lastmodified is None: 
            lastmodified = -1
         
        entitytag = res.etag()         
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
#                if (not provider.isInfoTypeSupported(path, "etag")) or ifrange != entitytag:
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
#            totallength = filesize

        ## Content Processing 
        mimetype = res.contentType()  #provider.getContentType(path)

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
            responseHeaders.append(("Content-Ranges", "bytes " + str(rangestart) + "-" + str(rangeend) + "/" + str(rangelength)))
            start_response("206 Partial Content", responseHeaders)   
        else:
            start_response("200 OK", responseHeaders)

        if isHeadMethod:
            yield ""
            return
#            return [ "" ]

        fileobj = res.openResourceForRead()

        # TODO: use Filewrapper? 
#        file_wrapper = environ.get("wsgi.file_wrapper", None)
#        if file_wrapper:
#            return file_wrapper(fileobj, BLOCK_SIZE)
#        else:
#            return _FileIter(fileobj, size=rangelength)
    
        if not doignoreranges:
            fileobj.seek(rangestart)

        contentlengthremaining = rangelength
        while 1:
            if contentlengthremaining < 0 or contentlengthremaining > BLOCK_SIZE:
                readbuffer = fileobj.read(BLOCK_SIZE)
            else:
                readbuffer = fileobj.read(contentlengthremaining)
            util.debug("sc", "GET yield start..., len=%s" % len(readbuffer))
            yield readbuffer
            util.debug("sc", "GET yield end.")
            contentlengthremaining -= len(readbuffer)
            if len(readbuffer) == 0 or contentlengthremaining == 0:
                break
        util.debug("sc", "fileobj.close()...")
        fileobj.close()
        util.debug("sc", "fileobj.close().")
        return




#    def doTRACE(self, environ, start_response):
#        """ TODO: TRACE pending, but not essential."""
#        self._fail(HTTP_NOT_IMPLEMENTED)
