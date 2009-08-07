# -*- coding: iso-8859-1 -*-

"""
request_server
=============

:Author: Ho Chun Wei, fuzzybr80(at)gmail.com (author of original PyFileServer)
:Author: Martin Wendt, moogle(at)wwwendt.de 
:Copyright: Lesser GNU Public License, see LICENSE file attached with package


WSGI application that handles one single WebDAV request.

See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
"""
from pprint import pprint
from urlparse import urlparse
#import sys
import util

__docformat__ = 'reStructuredText'


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

#import websupportfuncs
import lock_manager

from lxml import etree
   

BLOCK_SIZE = 8192


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
        assert 'wsgidav.verbose' in environ
        # TODO: allow anonymous somehow: this should run, even if http_authenticator middleware is not installed
#        assert 'http_authenticator.username' in environ
        if not 'http_authenticator.username' in environ:
            util.log("*** missing 'http_authenticator.username' in environ")

        environ['wsgidav.username'] = environ.get('http_authenticator.username', "anonymous") 
        requestmethod =  environ['REQUEST_METHOD']

        # Convert 'infinity' and 'T'/'F' to a common case
        if environ.get("HTTP_DEPTH") is not None: 
            environ["HTTP_DEPTH"] = environ["HTTP_DEPTH"].lower() 
        if environ.get("HTTP_OVERWRITE") is not None: 
            environ["HTTP_OVERWRITE"] = environ["HTTP_OVERWRITE"].upper() 

        # Dispatch HTTP request methods to 'doMETHOD()' handlers
        method = getattr(self, 'do%s' % requestmethod, None)
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
        if self._verbose >= 2:
            util.log("Raising DAVError %s" % e.getUserInfo())
        raise e



    def _log(self, environ, msg, var=None):
        if self.verbose >= 2:
            util.log(msg, var)
        

    
    
    def _checkWritePermission(self, path, depth, environ):
        """Check, if write access is allowed, otherwise raise DAVError."""
        dav = self._davProvider
        lockMan = dav.lockManager
        if lockMan is None:
            return True

        refUrl = dav.getRefUrl(path)
        
        if 'wsgidav.conditions.if' not in environ:
            util.parseIfHeaderDict(environ)

        conflictList = lockMan.checkAccessPermission(dav, 
                                                     refUrl, 
                                                     environ["wsgidav.ifLockTokenList"], 
                                                     "write", 
                                                     depth, 
                                                     environ["wsgidav.username"])

        # If any conflict was detected, raise one of them
        for _lock, e in conflictList:
            raise e
        return




    def _evaluateIfHeaders(self, path, environ):
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
        dav = self._davProvider
        resInfos = dav.getInfoDict(path)
        # TODO: bail out, if not exists (resInfos is None)?

        # Add parsed If header to environ
        if 'wsgidav.conditions.if' not in environ:
            util.parseIfHeaderDict(environ)
        ifDict = environ['wsgidav.conditions.if']

        # Raise HTTP_PRECONDITION_FAILED or HTTP_NOT_MODIFIED, if standard 
        # HTTPcondition fails
        lastmodified = -1 # nonvalid modified time
        entitytag = '[]' # Non-valid entity tag
        if dav.exists(path):
            if resInfos["modified"] is not None:
                lastmodified = resInfos["modified"]            
            if resInfos["etag"] is not None:
                entitytag = resInfos["etag"]            

        if ('HTTP_IF_MODIFIED_SINCE' in environ 
            or 'HTTP_IF_UNMODIFIED_SINCE' in environ 
            or 'HTTP_IF_MATCH' in environ 
            or 'HTTP_IF_NONE_MATCH' in environ):
            util.evaluateHTTPConditionals(dav, path, lastmodified, entitytag, environ)

        if not 'HTTP_IF' in environ:
            return

        # Raise HTTP_PRECONDITION_FAILED, if DAV 'If' condition fails  
        # TODO: handle empty locked resources
        # TODO: handle unmapped locked resources
#            isnewfile = not dav.exists(mappedpath)

        refUrl = dav.getRefUrl(path)
        lockMan = dav.lockManager
        locktokenlist = []
        if lockMan:
            lockList = lockMan.getIndirectUrlLockList(refUrl, environ['wsgidav.username'])
            for lock in lockList:
                locktokenlist.append(lock["token"])

        if not util.testIfHeaderDict(dav, path, ifDict, refUrl, locktokenlist, entitytag):
            self._fail(HTTP_PRECONDITION_FAILED, "'If' header condition failed.") 

        return
    
    
    
    
    def doPROPFIND(self, environ, start_response):
        """
        TODO: does not yet support If and If HTTP Conditions
        @see http://www.webdav.org/specs/rfc4918.html#METHOD_PROPFIND
        """
        path = environ["PATH_INFO"]
        dav = self._davProvider

        # RFC: By default, the PROPFIND method without a Depth header MUST act as if a "Depth: infinity" header was included.
        environ.setdefault('HTTP_DEPTH', 'infinity')
        if not environ["HTTP_DEPTH"] in ("0", "1", "infinity"):            
            self._fail(HTTP_BAD_REQUEST, 
                       "Invalid Depth header: '%s'." % environ["HTTP_DEPTH"])

        if environ["HTTP_DEPTH"] == "infinity" and not self.allowPropfindInfinite:
            self._fail(HTTP_FORBIDDEN, 
                       "PROPFIND 'infinite' was disabled for security reasons.",
                       preconditionCode=PRECONDITION_CODE_PropfindFiniteDepth)    
        
        self._evaluateIfHeaders(path, environ)

        # Parse PROPFIND request
        requestEL = util.parseXmlBody(environ, allowEmpty=True)
        if requestEL is None:   
            # An empty PROPFIND request body MUST be treated as a request for 
            # the names and values of all properties.
            requestEL = etree.XML("<D:propfind xmlns:D='DAV:'><D:allprop/></D:propfind>")

        if requestEL.tag != "{DAV:}propfind":
            self._fail(HTTP_BAD_REQUEST)   
        
        if not dav.exists(path):
            self._fail(HTTP_NOT_FOUND)

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
        
        reslist = dav.getDescendants(path, depth=environ["HTTP_DEPTH"], addSelf=True)
        if environ['wsgidav.verbose'] >= 3:
            pprint(reslist, indent=4)
        
        # TODO: get additional namespace mapping from dav.getNamespaceMap()?
        multistatusEL = etree.Element("{DAV:}multistatus", nsmap={"D": "DAV:"})
        responsedescription = []
        
        for respath in reslist:

            if propFindMode == "allprop": 
                propList = dav.getProperties(respath, mode="allprop")
            elif propFindMode == "propname":
                propList = dav.getProperties(respath, mode="propname", namesOnly=True)
            else:
                propList = dav.getProperties(respath, mode="named", nameList=propNameList)

#            href = util.makeCompleteUrl(environ, respath)
            href = dav.getHref(respath)
            # TODO: OK?:
#            href = href.decode("iso_8859_1")  # Convert to unicode, because ASCII is not enough, and iso_8859_1 is not allowed for lxml

            util.addPropertyResponse(multistatusEL, href, propList)

        if responsedescription:
            etree.SubElement(multistatusEL, "{DAV:}responsedescription").text = "\n".join(responsedescription)
        
        return util.sendMultiStatusResponse(environ, start_response, multistatusEL)




    def doPROPPATCH(self, environ, start_response):
        """Handle PROPPATCH request to set or remove a property.
        
        @see http://www.webdav.org/specs/rfc4918.html#METHOD_PROPPATCH
        """
        
        path = environ["PATH_INFO"]
        dav = self._davProvider

        # Only accept Depth: 0 (but assume this, if omitted)
        environ.setdefault('HTTP_DEPTH', '0')
        if environ['HTTP_DEPTH'] != '0':
            self._fail(HTTP_BAD_REQUEST, "Depth must be '0'.")
        
        self._evaluateIfHeaders(path, environ)
        # TODO: some properties may not be affected by locks?
        self._checkWritePermission(path, "0", environ)

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
                if propnode.tag != '{DAV:}prop':
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
                dav.setPropertyValue(path, propname, propvalue, dryRun=True)
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
                    dav.setPropertyValue(path, propname, propvalue, dryRun=False)
                    # Set value to None, so the response xml contains empty tags
                    propResponseList.append( (propname, None) )
                except Exception, e:
                    e = asDAVError(e)
                    propResponseList.append( (propname, e) )
                    responsedescription.append(e.getUserInfo())

        # Generate response XML
        multistatusEL = etree.Element("{DAV:}multistatus", nsmap={"D": "DAV:"})
#        href = util.makeCompleteUrl(environ, path) 
        href = dav.getHref(path)
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
        dav = self._davProvider

        # Do not understand ANY request body entities
        if util.getContentLength(environ) != 0:
            self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
                       "The server does not handle any body content.")

        # Only accept Depth: 0 (but assume this, if omitted)
        if environ.setdefault('HTTP_DEPTH', '0') != '0':
            self._fail(HTTP_BAD_REQUEST, "Depth must be '0'.")
        
        if dav.exists(path):
            self._fail(HTTP_METHOD_NOT_ALLOWED,
                       "MKCOL can only be executed on an unmapped URL.")         

        parentdir = dav.getParent(path)
        if not dav.isCollection(parentdir):
            self._fail(HTTP_CONFLICT, "Parent must be an existing collection.")          

        self._evaluateIfHeaders(path, environ)
        # Check for write permissions on the PARENT
        self._checkWritePermission(parentdir, "0", environ)

        dav.createCollection(path)

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
        dav = self._davProvider

        # Do not understand ANY request body entities
        if util.getContentLength(environ) != 0:
            self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
                       "The server does not handle any body content.")
        
        if not dav.exists(path):
            self._fail(HTTP_NOT_FOUND)         

        if dav.isCollection(path): 
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

        self._evaluateIfHeaders(path, environ)
        self._checkWritePermission(path, environ["HTTP_DEPTH"], environ)

        # Get a list of all resources (parents after children, so we can remove 
        # them in that order)
        childLocList = dav.getDescendants(path, depthFirst=True, depth=environ['HTTP_DEPTH'], addSelf=True)
#        if environ['wsgidav.verbose'] >= 3:
#            print "getDescendants"
#            pprint(childLocList, indent=4)

        dictError = {} # Errors in deletion; { <url>: <DAVError>, ... } 
        dictHidden = {}  # Hidden errors, ancestors of failed deletes
        for childPath in childLocList:
            if childPath in dictHidden:
                dictHidden[dav.getParent(childPath)] = ''
                continue            

            try:
                # 9.6.1.: Any headers included with delete must be applied in processing every resource to be deleted
                self._evaluateIfHeaders(childPath, environ)
#                self._checkWritePermission(childPath, environ["HTTP_DEPTH"], environ)

                dav.remove(childPath)
                
            except Exception, e:
                dictError[childPath] = asDAVError(e)
                dictHidden[dav.getParent(childPath)] = ''

            else:
                if dav.exists(childPath) and childPath not in dictError:
                    # Double-check, if deletion succeeded
                    dictError[childPath] = DAVError(HTTP_INTERNAL_ERROR, 
                                                   "Resource could not be deleted.")
                    dictHidden[dav.getParent(childPath)] = ''

        # Send response
        if len(dictError) == 1 and path in dictError:
            return util.sendSimpleResponse(environ, start_response, dictError[path])
        
        elif len(dictError) > 0:
            multistatusEL = etree.Element("{DAV:}multistatus", nsmap={"D": "DAV:"})
            
            for errpath, e in dictError.items():
                responseEL = etree.SubElement(multistatusEL, "{DAV:}response") 
                etree.SubElement(responseEL, "{DAV:}href").text = dav.getHref(errpath)
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
        dav = self._davProvider
        path = environ["PATH_INFO"]
        parentPath = dav.getParent(path)
        
        if dav.isCollection(path):
            self._fail(HTTP_METHOD_NOT_ALLOWED, "Cannot PUT to a collection")
        elif not dav.isCollection(parentPath):
            self._fail(HTTP_CONFLICT, "PUT parent must be a collection")

        self._evaluateIfHeaders(path, environ)
        if dav.exists(path):
            self._checkWritePermission(path, "0", environ)
        else:
            self._checkWritePermission(parentPath, "0", environ)

        isnewfile = not dav.isResource(path)
#        if not isnewfile:
#            if dav.supportLastModified(path):
#                lastmodified = dav.getLastModified(path)            
#            else:
#                lastmodified = -1
#            
#            if dav.supportEntityTag(path):
#                entitytag = dav.getEntityTag(path)         
#            else:
#                entitytag = '[]'
#        else:
#            lastmodified = -1
#            entitytag = '[]'

            # must check locking on collection if is new file - adding entry to collection
#            urlparentpath = websupportfuncs.getLevelUpURL(displaypath)      
#            if lock_manager.isUrlLocked(dav.lockManager, urlparentpath):
#            if dav.isLocked(dav.getParent(path)):
#                self.evaluateSingleIfConditionalDoException(dav.getContainingCollection(path), urlparentpath, environ, start_response, checkLock=True)
#                self.evaluateSingleIfConditionalDoException(dav.getParent(path), environ, start_response, checkLock=True)

        # isUrlLocked returns lock type - None if not locked
#        if dav.exists(path) or lock_manager.isUrlLocked(dav.lockManager, displaypath):
#        if dav.exists(path) or dav.isLocked(path):
#            self.evaluateSingleIfConditionalDoException(path, environ, start_response, checkLock=True)
#        self.evaluateSingleHTTPConditionalsDoException(path, environ, start_response)

        ## Test for unsupported stuff
        if 'HTTP_CONTENT_ENCODING' in environ:
            self._fail(HTTP_NOT_IMPLEMENTED,
                       "Content-encoding header is not supported.")
        if 'HTTP_CONTENT_RANGE' in environ:
            self._fail(HTTP_NOT_IMPLEMENTED,
                       "Content-range header is not supported.")

        ## Start Content Processing
#        if 'HTTP_CONTENT_LENGTH' in environ:
#            try:
#                contentlength = long(environ.get('HTTP_CONTENT_LENGTH', -1))
#            except ValueError: 
#                contentlength = -1 #read as much as possible
#        # TODO: contentlength may be undefined here
        contentlength = util.getContentLength(environ)

        
        try:      
            fileobj = dav.openResourceForWrite(path, contenttype=environ.get('HTTP_CONTENT_TYPE'))
            contentlengthremaining = contentlength
            # TODO: what happens, if contentlength != len(stream)? 
            while 1:
                util.debug("sc", "PUT: read from wsgi.input")
                if contentlengthremaining < 0 or contentlengthremaining > BLOCK_SIZE:
                    readbuffer = environ['wsgi.input'].read(BLOCK_SIZE)
                else:
                    readbuffer = environ['wsgi.input'].read(contentlengthremaining)
                contentlengthremaining -= len(readbuffer)
                util.debug("sc", "PUT: fileobj.write(%s..., len=%s)" % (readbuffer[:10], len(readbuffer)))
                fileobj.write(readbuffer)
                if len(readbuffer) == 0 or contentlengthremaining == 0:
                    break
            util.debug("sc", "PUT: fileobj.close()")
            fileobj.close()

        except Exception, e:
            self._fail(e)

        util.debug("sc", "PUT: sendSimpleResponse")
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
        dav = self._davProvider
        propMan = dav.propManager
#        lockMan = dav.lockManager
        
        srcRealm = environ['SCRIPT_NAME']
        srcPath = environ["PATH_INFO"]
#        srcParentLoc = dav.getParent(srcPath)
        isCollection = dav.isCollection(srcPath)

        if not dav.exists(srcPath):
            self._fail(HTTP_NOT_FOUND)         
        if 'HTTP_DESTINATION' not in environ:
            self._fail(HTTP_BAD_REQUEST, "Missing required Destination header.")
        if util.getContentLength(environ) != 0:
            self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
                       "The server does not handle any body content.")
        
        if isCollection:
            # The COPY method on a collection without a Depth header MUST act as if a Depth header with value "infinity" was included. A client may submit a Depth header on a COPY on a collection with a value of "0" or "infinity". 
            if not environ.setdefault("HTTP_DEPTH", "infinity") in ("0", "infinity"):
                self._fail(HTTP_BAD_REQUEST, "Invalid Depth header for collection.")
        else:
            # It's an existing resource, only accept Depth 0 
            # TODO: correct logic? ( litmus 'copymove: 3 (copy_simple)' seems to send 'infinity' for a simple resource)
            if environ.get("HTTP_DEPTH") == "infinity":
                environ["HTTP_DEPTH"] = "0"
            
            if environ.setdefault("HTTP_DEPTH", "0") != "0":
                self._fail(HTTP_BAD_REQUEST, "Invalid Depth header for resource.")

        if not environ.setdefault("HTTP_OVERWRITE", "T") in ("T", "F"):
            self._fail(HTTP_BAD_REQUEST, "Invalid Overwrite header.")

        # 
        
        destScheme, destNetloc, destPath, \
        _destParams, _destQuery, _destFrag = urlparse(environ["HTTP_DESTINATION"], 
                                                      allow_fragments=False) # Return fragments as part of <path>


        # destPath starts with '/' 
        # Destination header may be quoted (e.g. DAV Explorer sends unquoted, Windows quoted)
         
        destPath = urllib.unquote(destPath)
        destNormUrl = "/" + destPath.lstrip("/")
        if isCollection:
            destNormUrl = destNormUrl.rstrip("/") + "/"
        
        # TODO: We could turn a copy across realms into a PUT (reusing the credentials we have)
        if destScheme and destScheme != environ["wsgi.url_scheme"]:
            self._fail(HTTP_BAD_GATEWAY,
                       "Source and destination must have the same scheme.")
        elif destNetloc and destNetloc.lower() != environ["HTTP_HOST"].lower():
            # TODO: this should consider environ["SERVER_PORT"] also
            self._fail(HTTP_BAD_GATEWAY,
                       "Source and destination must have the same host name.")
        elif not destNormUrl.startswith(srcRealm + "/"):
            #inter-realm copying not supported, since its not possible to authentication-wise
            self._fail(HTTP_BAD_GATEWAY, "Inter-realm copy/move is not supported.")

        destUrl = "/" + destNormUrl[len(srcRealm+"/"):]
        destParentUrl = dav.getParent(destUrl)
        if not dav.isCollection(destParentUrl):
            self._fail(HTTP_CONFLICT, "Parent must be a collection.")

        destExists = dav.exists(destUrl)

        self._evaluateIfHeaders(srcPath, environ)
        self._evaluateIfHeaders(destUrl, environ)
        if isMove:
            self._checkWritePermission(srcPath, "infinity", environ)
#            self._checkWritePermission(srcParentLoc, "infinity", environ) # TODO: really?
        self._checkWritePermission(destUrl, environ["HTTP_DEPTH"], environ)
#        self._checkWritePermission(destParentUrl, environ["HTTP_DEPTH"], environ) # TODO: really?

        if srcPath == destUrl: # TODO: case aware?
            self._fail(HTTP_FORBIDDEN, "Cannot copy/move source onto itself")
        # TODO: test for recursion: /a/ -> /a/b/

        if destExists and environ["HTTP_OVERWRITE"] != "T":
            self._fail(HTTP_PRECONDITION_FAILED,
                       "Target already exists and Overwrite is set to false")


        srcRootLen = len(srcPath)
        destRootLen = len(destUrl)
        
        srcList = dav.getDescendants(srcPath, addSelf=True)

        # --- Cleanup target collection ----------------------------------------
        # TODO: double-check this: This must be bullet proof, otherwise unwanted files may be deleted
        if destExists and environ["HTTP_DEPTH"] == "infinity":
            # TODO: we don't delete destination collection members when depth==0, OK? 
            if isMove:
                # MOVE:
                # If a resource exists at the destination and the Overwrite header is "T", 
                # then prior to performing the move, the server MUST perform a 
                # DELETE with "Depth: infinity" on the destination resource. 
                destList = dav.getDescendants(destUrl, depthFirst=True, addSelf=True)
                for d in destList:
                    if environ['wsgidav.verbose'] >= 2:
                        util.log("Remove dest before move: '%s'" % d)
                    dav.remove(d)
            else:
                # COPY:
                # Remove destination files, that are not part of source, because source 
                # and dest collections must not be merged (9.8.4).
                # This is not the same as deleting the complete dest collection 
                # before copying, because that would also discard the history of 
                # existing resources.
                destList = dav.getDescendants(destUrl, depthFirst=True, addSelf=False)
                for d in destList:
                    relUrl = d[destRootLen:]
                    s = srcPath + relUrl
                    if not s in srcList:
                        if environ['wsgidav.verbose'] >= 2:
                            util.log("Remove unmatched dest before copy: '%s'" % d)
                        dav.remove(d)
        
        # --- Copy/move from source to dest ------------------------------------ 
        dictError = {}
        for s in srcList:
            refS = dav.getRefUrl(s)
            relUrl = s[srcRootLen:]
            d = destUrl + relUrl
            normD = destNormUrl + relUrl
            
            # Skip, if there was already an error while processing the parent
            parentError = False
            for errUrl in dictError.keys():
                if d.startswith(errUrl):  # TODO: util.isChildUrl(parent, child)
                    parentError = True
                    break
            if parentError:
                if environ['wsgidav.verbose'] >= 2:
                    util.log("Copy: skipping '%s', because of parent error" % (d))
                continue
            
            try:
                self._evaluateIfHeaders(s, environ)
                
                # TODO: support  native MOVE in AL!
                # MOVE is frequently used by clients to rename a file without changing its parent collection, so it's not appropriate to reset all live properties that are set at resource creation. For example, the DAV:creationdate property value SHOULD remain the same after a MOVE.

                if dav.isCollection(s):
                    if not dav.exists(d):
                        if environ['wsgidav.verbose'] >= 2:
                            util.log("Create collection '%s'" % d)
                        dav.createCollection(d)
                    else:
                        if environ['wsgidav.verbose'] >= 2:
                            util.log("Skipping existing collection '%s'" % d)
                else:   
                    if environ['wsgidav.verbose'] >= 2:
                        util.log("Copy '%s' -> '%s'" % (s, d))
                    # AL can delete/write or do an in-place overwrite
                    dav.copyResource(s, d)
                if propMan:
                    propMan.copyProperties(refS, normD)     

            except Exception, e:
                dictError[d] = asDAVError(e)

        if isMove:
            # MOVE: Remove source
            # TODO: this is what PyFileServer 0.2 implemented. We should add native move-support to AL 
            srcList = dav.getDescendants(srcPath, depthFirst=True, addSelf=True)
            for s in srcList:
                if environ['wsgidav.verbose'] >= 2:
                    util.log("Remove source after move '%s'" % s)
                # TODO: try/except:
                dav.remove(s)

        # Return error response
        if len(dictError) == 1 and destUrl in dictError:
            return util.sendSimpleResponse(environ, start_response, dictError[destUrl])
        elif len(dictError) > 0:
            # Multi-value result should not contain 424 (Failed Dependency), 201 or 204 
            multistatusEL = etree.Element("{DAV:}multistatus", nsmap={"D": "DAV:"})
            
            for url, e in dictError.items():
                responseEL = etree.SubElement(multistatusEL, "{DAV:}response") 
                etree.SubElement(responseEL, "{DAV:}href").text = dav.getHref(url)
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
        dav = self._davProvider
        lockMan = dav.lockManager
        path = environ["PATH_INFO"]
        refUrl = dav.getRefUrl(path)
        
        if lockMan is None:
            self._fail(HTTP_NOT_IMPLEMENTED, # TODO: is this the correct status code?
                       "This realm does not support locking.")

        if environ.setdefault("HTTP_DEPTH", "infinity") not in ("0", "infinity"):
            self._fail(HTTP_BAD_REQUEST, "Expected Depth: 'infinity' or '0'.")
        
        self._evaluateIfHeaders(path, environ)

        resourceExists = dav.exists(path)
        timeoutsecs = lock_manager.readTimeoutValueHeader(environ.get('HTTP_TIMEOUT', ''))
        submittedTokenList = environ['wsgidav.ifLockTokenList']

        lockinfoEL = util.parseXmlBody(environ, allowEmpty=True)
        
        # --- Special case: empty request body ---------------------------------
        
        if lockinfoEL is None:
            # TODO: @see 9.10.2
            # TODO: 'URL of a resource within the scope of the lock'
            #       Other (shared) locks are unaffected and don't prevent refreshing   
            # TODO: check for valid user
            # TODO: check for If with single lock token
            environ['HTTP_DEPTH'] = '0'  # MUST ignore depth header on refresh

            if not resourceExists:
                self._fail(HTTP_BAD_REQUEST, 
                           "LOCK refresh must specify an existing resource.")
            if len(submittedTokenList) != 1:
                self._fail(HTTP_BAD_REQUEST, 
                           "Expected a lock token (only one lock may be refreshed at a time).")
            elif not lockMan.isUrlLockedByToken(refUrl, submittedTokenList[0]):
                self._fail(HTTP_BAD_REQUEST, "Lock token does not match URL.")
            # TODO: test, if token is owned by user

            lock = lockMan.refreshLock(submittedTokenList[0], timeoutsecs)
            
            # The lock root may be <path>, or a parent of <path>.
            lockPath = dav.refUrlToPath(lock["root"])

            propEL = etree.Element("{DAV:}prop", nsmap={"D" : "DAV:"})
            # TODO: handle exceptions in getPropertyValue
            lockdiscoveryEL = dav.getPropertyValue(lockPath, '{DAV:}lockdiscovery')
            propEL.append(lockdiscoveryEL)
               
            # Lock-Token header is not returned 
            start_response("200 OK", [('Content-Type','application/xml'),
                                      ("Date", util.getRfc1123Time()),
                                      ])
            return ["<?xml version='1.0' ?>", 
                    etree.tostring(propEL, pretty_print=True) ]
            
        # --- Standard case: parse xml body ------------------------------------ 
        
        if lockinfoEL.tag != "{DAV:}lockinfo":
            self._fail(HTTP_BAD_REQUEST)   

        locktype = None
        lockscope = None
        lockowner = ''
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
                        locktype = 'write'   # only type accepted
                    break

            elif linode.tag == "{DAV:}owner":
                # Store whole <owner> tag, so we can use etree.XML() later
                lockowner = etree.tostring(linode, pretty_print=False)

            else:
                self._fail(HTTP_BAD_REQUEST, "Invalid node '%s'." % linode.tag)

        if not lockscope:
            self._fail(HTTP_BAD_REQUEST, "Missing or invalid locksope.") 
        if not locktype:
            self._fail(HTTP_BAD_REQUEST, "Missing or invalid locktype.") 
            
        # TODO: implement 9.10.4: Locking Unmapped URLs: must create an empty resource
        if not resourceExists:
            dav.createEmptyResource(path) 

        # --- Check, if path is already locked ---------------------------

        lockResultList = lockMan.getCheckedLock(dav, 
                                                refUrl, 
                                                locktype, lockscope, lockdepth, lockowner, timeoutsecs, 
                                                environ['wsgidav.username'], 
                                                submittedTokenList)

        if environ.get("wsgidav.debug_break"):
            pass # break point
            
        lockToken = None 
        if len(lockResultList) == 1 and lockResultList[0][1] is None:
            # Lock succeeded
            lockToken = lockResultList[0][0]
    
            propEL = etree.Element("{DAV:}prop", nsmap={"D" : "DAV:"})
            # TODO: handle exceptions in getPropertyValue
            lockdiscoveryEL = dav.getPropertyValue(path, '{DAV:}lockdiscovery')
            propEL.append(lockdiscoveryEL)
               
            respcode = "200 OK"
            if not resourceExists:
                respcode = "201 Created"
    
            start_response(respcode, [('Content-Type', 'application/xml'),
                                      ('Lock-Token', lockToken["token"]),
                                      ("Date", util.getRfc1123Time()),
                                      ])
            return ["<?xml version='1.0' ?>", # TODO: required?
                    etree.tostring(propEL, pretty_print=True) ]

        # --- Locking FAILED: return fault response 
        if len(lockResultList) == 1 and lockResultList[0][0]["root"] == refUrl:
            # If there is only one error for the root URL, send as simple error response
            return util.sendSimpleResponse(environ, start_response, lockResultList[0][1]) 
         
        dictStatus = {}
        if not refUrl in lockResultList:  # FIXME: in doesnt work here
            dictStatus[refUrl] = DAVError(HTTP_FAILED_DEPENDENCY)

        for lockDict, e in lockResultList:
            dictStatus[lockDict["root"]] = e

        # Return multi-status fault response
        multistatusEL = etree.Element("{DAV:}multistatus", nsmap={"D": "DAV:"})
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
        dav = self._davProvider

        lockMan = dav.lockManager
        if lockMan is None:
            self._fail(HTTP_NOT_IMPLEMENTED, "This realm does not support locking.")
            
        if util.getContentLength(environ) != 0:
            self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
                       "The server does not handle any body content.")
        
        if not 'HTTP_LOCK_TOKEN' in environ:
            self._fail(HTTP_BAD_REQUEST, "Missing lock token.")

        self._evaluateIfHeaders(path, environ)

        lockToken = environ['HTTP_LOCK_TOKEN'].strip('<>')
        refUrl = dav.getRefUrl(path)

        if not lockMan.isUrlLockedByToken(refUrl, lockToken):
            self._fail(HTTP_CONFLICT,
                       "Resource is not locked by token.",
                       preconditionCode=PRECONDITION_CODE_LockTokenMismatch)
            
        if not lockMan.isTokenLockedByUser(lockToken, environ['wsgidav.username']):
            # TODO: there must be a way to allow this for admins.
            #       Maybe test for "remove_locks" in environ["wsgidav.roles"]
            self._fail(HTTP_FORBIDDEN, "Token was created by another user.")

        # TODO: Is this correct?: unlock(a/b/c) will remove Lock for 'a/b' 
        lockMan.deleteLock(lockToken)

        return util.sendSimpleResponse(environ, start_response, HTTP_NO_CONTENT)




    def doOPTIONS(self, environ, start_response):
        """
        @see http://www.webdav.org/specs/rfc4918.html#HEADER_DAV
        """
        dav = self._davProvider
        path = environ["PATH_INFO"]
#        requestpath = urllib.unquote(environ["PATH_INFO"])

        headers = [('Content-Type', 'text/html'),
                   ('Content-Length', '0'),
                   ('DAV', '1,2'),  # TODO: 10.1: 'OPTIONS MUST return DAV header with compliance class "1"'
                                    # TODO: 10.1: In cases where WebDAV is only supported in part of the server namespace, an OPTIONS request to non-WebDAV resources (including "/") SHOULD NOT advertise WebDAV support
                   ('Server', 'DAV/2'),
                   ('Date', util.getRfc1123Time()),
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
            start_response('200 OK', headers)        
            return ['']  

        if dav.isCollection(path):
            headers.append( ('Allow', 'OPTIONS HEAD GET DELETE PROPFIND PROPPATCH COPY MOVE LOCK UNLOCK') )
        elif dav.isResource(path):
            headers.append( ('Allow', 'OPTIONS HEAD GET PUT DELETE PROPFIND PROPPATCH COPY MOVE LOCK UNLOCK') )
            if dav.supportRanges():
                headers.append( ('Allow-Ranges', 'bytes') )
        elif dav.isCollection(dav.getParent(path)):
            # TODO: should we allow LOCK here?
            headers.append( ('Allow', 'OPTIONS PUT MKCOL') ) 
        else:
            self._fail(HTTP_NOT_FOUND)

        start_response('200 OK', headers)        
        return ['']




    def doGET(self, environ, start_response):
        return self._sendResource(environ, start_response, isHeadMethod=False)


    def doHEAD(self, environ, start_response):
        return self._sendResource(environ, start_response, isHeadMethod=True)

#    def get(self, environ, start_response):
#        """
#        From paste.fileapp.py
#        """
#        is_head = environ['REQUEST_METHOD'].upper() == 'HEAD'
#        if 'max-age=0' in CACHE_CONTROL(environ).lower():
#            self.update(force=True) # RFC 2616 13.2.6
#        else:
#            self.update()
#        if not self.content:
#            if not os.path.exists(self.filename):
#                exc = HTTPNotFound(
#                    'The resource does not exist',
#                    comment="No file at %r" % self.filename)
#                return exc(environ, start_response)
#            try:
#                file = open(self.filename, 'rb')
#            except (IOError, OSError), e:
#                exc = HTTPForbidden(
#                    'You are not permitted to view this file (%s)' % e)
#                return exc.wsgi_application(
#                    environ, start_response)
#        retval = DataApp.get(self, environ, start_response)
#        if isinstance(retval, list):
#            # cached content, exception, or not-modified
#            if is_head:
#                return ['']
#            return retval
#        (lower, content_length) = retval
#        if is_head:
#            return ['']
#        file.seek(lower)
#        file_wrapper = environ.get('wsgi.file_wrapper', None)
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
        dav = self._davProvider
        resInfo = dav.getInfoDict(path)

        if util.getContentLength(environ) != 0:
            self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
                       "The server does not handle any body content.")
        elif environ.setdefault("HTTP_DEPTH", "0") != "0":
            self._fail(HTTP_BAD_REQUEST, "Only Depth: 0 supported.") 
        elif not dav.exists(path):
            self._fail(HTTP_NOT_FOUND)         
        elif dav.isCollection(path): 
            self._fail(HTTP_FORBIDDEN, 
                       "Directory browsing not supported (try the WsgiDavDirBrowser middleware).")         

        self._evaluateIfHeaders(path, environ)

        if resInfo["contentLength"] is not None: #dav.supportContentLength(path):
            filesize = resInfo["contentLength"]
        else:
            filesize = -1 # flag logic to read until EOF
            
        if resInfo["modified"] is not None: #dav.isInfoTypeSupported(path, "modified"):
            lastmodified = resInfo["modified"]            
        else:
            lastmodified = -1
         
        if resInfo["etag"] is not None: #dav.isInfoTypeSupported(path, "etag"):
            entitytag = resInfo["etag"]         
        else:
            entitytag = '[]'

        ## Ranges      
        doignoreranges = (resInfo["contentLength"] is None #not dav.supportContentLength(path) 
                          or not resInfo["supportRanges"] #dav.supportRanges(path)
                          or filesize == 0)
        if 'HTTP_RANGE' in environ and 'HTTP_IF_RANGE' in environ and not doignoreranges:
            ifrange = environ['HTTP_IF_RANGE']
            #try as http-date first (Return None, if invalid date string)
#            secstime = httpdatehelper.getsecstime(ifrange)
            secstime = util.parseTimeString(ifrange)
            if secstime:
                if lastmodified != secstime:
                    doignoreranges = True
            else:
                #use as entity tag
                ifrange = ifrange.strip("\" ")
#                if (not dav.isInfoTypeSupported(path, "etag")) or ifrange != entitytag:
                if resInfo["etag"] is None or ifrange != entitytag:
                    doignoreranges = True

        ispartialranges = False
        if 'HTTP_RANGE' in environ and not doignoreranges:
            ispartialranges = True
            listRanges, _totallength = util.obtainContentRanges(environ['HTTP_RANGE'], filesize)
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
        mimetype = resInfo["contentType"] #dav.getContentType(path)

        responseHeaders = []
        if dav.isInfoTypeSupported(path, "contentLength"): #dav.supportContentLength(path):
            # Content-length must be of type string (otherwise CherryPy server chokes) 
            responseHeaders.append(('Content-Length', str(rangelength)))
        if dav.isInfoTypeSupported(path, "modified"): #dav.isInfoTypeSupported(path, "modified"):
            responseHeaders.append(('Last-Modified', util.getRfc1123Time(lastmodified)))
        responseHeaders.append(('Content-Type', mimetype))
        responseHeaders.append(('Date', util.getRfc1123Time()))
        if dav.isInfoTypeSupported(path, "etag"):
            responseHeaders.append(('ETag', '"%s"' % entitytag))
 
        if ispartialranges:
            responseHeaders.append(('Content-Ranges', 'bytes ' + str(rangestart) + '-' + str(rangeend) + '/' + str(rangelength)))
            start_response('206 Partial Content', responseHeaders)   
        else:
            start_response('200 OK', responseHeaders)

        if isHeadMethod:
            yield ""
            return
#            return [ "" ]

        fileobj = dav.openResourceForRead(path)

        # TODO: use Filewrapper? 
#        file_wrapper = environ.get('wsgi.file_wrapper', None)
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
