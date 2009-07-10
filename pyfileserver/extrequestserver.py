"""
extrequestserver
================

:Module: pyfileserver.extrequestserver
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com
:Project: PyFileServer, http://pyfilesync.berlios.de/
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

This is the main implementation module for the various webDAV methods. Each 
method is implemented as a do<METHOD> generator function that is a wsgi 
subapplication::

   class RequestServer(object)

      constructor :
         __init__(self, propertymanager, 
                        lockmanager)
   
      main application:      
         __call__(self, environ, start_response)

      application methods:
         doPUT(self, environ, start_response)
         doOPTIONS(self, environ, start_response)
         doGETHEADDirectory(self, environ, start_response)
         doGETHEADFile(self, environ, start_response)
         doMKCOL(self, environ, start_response)
         doDELETE(self, environ, start_response)
         doPROPPATCH(self, environ, start_response)
         doPROPFIND(self, environ, start_response)
         doCOPY(self, environ, start_response)
         doMOVE(self, environ, start_response)
         doLOCK(self, environ, start_response)
         doUNLOCK(self, environ, start_response)

      misc methods:
         evaluateSingleIfConditionalDoException(self, mappedpath, displaypath, 
                                   environ, start_response, checkLock = False)
         evaluateSingleHTTPConditionalsDoException(self, mappedpath, 
                                          displaypath, environ, start_response)
   
This module is specific to the PyFileServer application.


Supporting Objects
------------------

The RequestServer takes two supporting objects:   
   
propertymanager
   An object that provides storage for dead properties assigned for webDAV resources.
   
   PropertyManagers must provide the methods as described in 
   ``pyfileserver.interfaces.propertymanagerinterface``

   See propertylibrary.PropertyManager for a sample implementation
   using shelve.

lockmanager
   An object that provides storage for locks made on webDAV resources.
   
   LockManagers must provide the methods as described in 
   ``pyfileserver.interfaces.lockmanagerinterface``

   See locklibrary.LockManager for a sample implementation
   using shelve.

The RequestServer also uses a resource abstraction layer placed in 
``environ['pyfileserver.resourceAL']`` by requestresolver.py

abstractionlayer
   An object that provides a basic interface to resources. 
   
   This layer allows developers to write layers allowing the application to share
   resources other than filesystems. 

   Abstraction Layers must provide the methods as described in 
   ``pyfileserver.interfaces.abstractionlayerinterface``
   
   See fileabstractionlayer.FilesystemAbstractionLayer and
   fileabstractionlayer.ReadOnlyFilesystemAbstractionLayer for sample
   implementations based on filesystems.

"""

__docformat__ = 'reStructuredText'


import urllib
import re
import StringIO
import traceback
import sys

from processrequesterrorhandler import HTTPRequestException
import processrequesterrorhandler

import websupportfuncs
import httpdatehelper
import propertylibrary
import locklibrary

from xml.dom.ext.reader import Sax2
import xml.dom.ext
from xml.dom import implementation, Node

BUFFER_SIZE = 8192
BUF_SIZE = 8192

class RequestServer(object):
    def __init__(self, propertymanager, lockmanager):
        self._propertymanager = propertymanager
        self._lockmanager = lockmanager

    def __call__(self, environ, start_response):

        assert 'pyfileserver.mappedrealm' in environ
        assert 'pyfileserver.mappedpath' in environ
        assert 'pyfileserver.mappedURI' in environ
        assert 'pyfileserver.resourceAL' in environ
        assert 'httpauthentication.username' in environ 

        environ['pyfileserver.username'] = environ['httpauthentication.username'] 
        requestmethod =  environ['REQUEST_METHOD']   
        mapdirprefix = environ['pyfileserver.mappedrealm']
        mappedpath = environ['pyfileserver.mappedpath']
        displaypath =  environ['pyfileserver.mappedURI']
        resourceAL = environ['pyfileserver.resourceAL']

        if (requestmethod == 'GET' or requestmethod == 'HEAD'):
            if resourceAL.isCollection(mappedpath): 
                return self.doGETHEADDirectory(environ, start_response)
            elif resourceAL.isResource(mappedpath):
                return self.doGETHEADFile(environ, start_response)
            else:
                raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_FOUND)               


        # @@: You could do this in a table/data-driven way, like:
        # class RequestServer(object):
        #     httpmethods = {}
        #     def doPUT(): ...
        #     httpmethods['PUT'] = doPUT
        #     def __call__(...):
        #         return self.httpmethods[REQUEST_METHOD](self, environ, start_response)
        #
        # Or like:
        #     def __call__(self):
        #         meth = getattr(self, 'do%s' % REQUEST_METHOD, None)
        #         if meth is None: # method not allowed
        #         else:
        #             return meth(environ, start_response)

        elif requestmethod == 'PUT':
            return self.doPUT(environ, start_response)
        elif requestmethod == 'DELETE':
            return self.doDELETE(environ, start_response)
        elif requestmethod == 'OPTIONS':
            return self.doOPTIONS(environ, start_response)
        elif requestmethod == 'MKCOL':
            return self.doMKCOL(environ, start_response)
        elif requestmethod == 'PROPPATCH':
            return self.doPROPPATCH(environ, start_response)
        elif requestmethod == 'PROPFIND':
            return self.doPROPFIND(environ, start_response)
        elif requestmethod == 'COPY':
            return self.doCOPY(environ, start_response)
        elif requestmethod == 'MOVE':
            return self.doMOVE(environ, start_response)
        elif requestmethod == 'LOCK':
            return self.doLOCK(environ, start_response)
        elif requestmethod == 'UNLOCK':
            return self.doUNLOCK(environ, start_response)
        else:
            raise HTTPRequestException(processrequesterrorhandler.HTTP_METHOD_NOT_ALLOWED)


    def doPUT(self, environ, start_response):
        # @@: As noted in requestresolver.py, this should just be using
        # PATH_INFO, and the object should have mappedpath as an
        # argument to the constructor.  This is a larger architectural
        # issue, not fixed trivially, but it will make this interact
        # much better with other WSGI components
        mappedpath = environ['pyfileserver.mappedpath']
        displaypath =  environ['pyfileserver.mappedURI']
        resourceAL = environ['pyfileserver.resourceAL']

        if resourceAL.isCollection(mappedpath):
            raise HTTPRequestException(processrequesterrorhandler.HTTP_BAD_REQUEST)

        if not resourceAL.isCollection(resourceAL.getContainingCollection(mappedpath)):
            raise HTTPRequestException(processrequesterrorhandler.HTTP_BAD_REQUEST)

        isnewfile = not resourceAL.isResource(mappedpath)
        if not isnewfile:
            if resourceAL.supportLastModified(mappedpath):
                lastmodified = resourceAL.getLastModified(mappedpath)            
            else:
                lastmodified = -1
            
            if resourceAL.supportEntityTag(mappedpath):
                entitytag = resourceAL.getEntityTag(mappedpath)         
            else:
                entitytag = '[]'
        else:
            lastmodified = -1
            entitytag = '[]'

            # must check locking on collection if is new file - adding entry to collection
            urlparentpath = websupportfuncs.getLevelUpURL(displaypath)      
            if locklibrary.isUrlLocked(self._lockmanager, urlparentpath):
                self.evaluateSingleIfConditionalDoException(resourceAL.getContainingCollection(mappedpath), urlparentpath, environ, start_response, checkLock=True)

        # isUrlLocked returns lock type - None if not locked
        if resourceAL.exists(mappedpath) or locklibrary.isUrlLocked(self._lockmanager, displaypath):
            self.evaluateSingleIfConditionalDoException( mappedpath, displaypath, environ, start_response, checkLock=True)
        self.evaluateSingleHTTPConditionalsDoException( mappedpath, displaypath, environ, start_response)

        ## Test for unsupported stuff
        if 'HTTP_CONTENT_ENCODING' in environ:
            raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_IMPLEMENTED)

        if 'HTTP_CONTENT_RANGE' in environ:
            raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_IMPLEMENTED)

        ## Start Content Processing
        if 'HTTP_CONTENT_LENGTH' in environ:
            try:
                contentlength = long(environ.get('HTTP_CONTENT_LENGTH', -1))
            except ValueError: 
                contentlength = -1 #read as much as possible

        try:      
            fileobj = resourceAL.openResourceForWrite(mappedpath, contenttype=environ.get('HTTP_CONTENT_TYPE', None))
            contentlengthremaining = contentlength

            while 1:
                if contentlengthremaining < 0 or contentlengthremaining > BUFFER_SIZE:
                    readbuffer = environ['wsgi.input'].read(BUFFER_SIZE)
                else:
                    readbuffer = environ['wsgi.input'].read(contentlengthremaining)
                contentlengthremaining -= len(readbuffer)
                fileobj.write(readbuffer)
                if len(readbuffer) == 0 or contentlengthremaining == 0:
                    break
            fileobj.close()
            locklibrary.checkLocksToAdd(self._lockmanager, displaypath)
            
        except HTTPRequestException, e:
            raise
        except Exception, e:
            raise HTTPRequestException(processrequesterrorhandler.HTTP_INTERNAL_ERROR, srcexception=e) 

        if isnewfile:
            start_response('201 Created', [('Content-Type', 'text/html'), ('Content-Length','0'), ('Date',httpdatehelper.getstrftime())])
        else:
            start_response('200 OK', [('Content-Type', 'text/html'), ('Content-Length','0'), ('Date',httpdatehelper.getstrftime())])

        return ['']


    def doOPTIONS(self, environ, start_response):
        resourceAL = environ['pyfileserver.resourceAL']

        headers = []
        if resourceAL.isCollection(environ['pyfileserver.mappedpath']):
            headers.append( ('Allow','OPTIONS HEAD GET DELETE PROPFIND PROPPATCH COPY MOVE LOCK UNLOCK') )
        elif resourceAL.isResource(environ['pyfileserver.mappedpath']):
            headers.append( ('Allow','OPTIONS HEAD GET PUT DELETE PROPFIND PROPPATCH COPY MOVE LOCK UNLOCK') )
            if resourceAL.supportRanges():
                headers.append( ('Allow-Ranges','bytes') )
        elif resourceAL.isCollection(resourceAL.getContainingCollection(environ['pyfileserver.mappedpath'])):
            headers.append( ('Allow','OPTIONS PUT MKCOL') )
        else:
            raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_FOUND)
        headers.append( ('Content-Type', 'text/html') )
        headers.append( ('Content-Length','0') )
        headers.append( ('DAV','1,2') )
        headers.append( ('Server','DAV/2') )
        headers.append( ('Date',httpdatehelper.getstrftime()) )
        start_response('200 OK', headers)        
        return ['']     


    def doGETHEADDirectory(self, environ, start_response):

        if environ['REQUEST_METHOD'] == 'HEAD':
            start_response('200 OK', [('Content-Type', 'text/html'), ('Date',httpdatehelper.getstrftime())])
            return ['']

        environ['HTTP_DEPTH'] = '0' #nothing else allowed
        mappedpath = environ['pyfileserver.mappedpath']
        mapdirprefix = environ['pyfileserver.mappedrealm']
        displaypath =  environ['pyfileserver.mappedURI']
        resourceAL = environ['pyfileserver.resourceAL']

        self.evaluateSingleIfConditionalDoException( mappedpath, displaypath, environ, start_response)
        self.evaluateSingleHTTPConditionalsDoException( mappedpath, displaypath, environ, start_response)

        trailer = environ.get('pyfileserver.trailer', '')
        
        # cStringIO not used for fear of unicode filenames
        o_list = [];        
        o_list.append('<html><head><title>PyFileServer - Index of %s </title>' % (displaypath,))
        o_list.append("""\
<style type="text/css">
img { border: 0; padding: 0 2px; vertical-align: text-bottom; }
td  { font-family: monospace; padding: 2px 3px; text-align: right; vertical-align: bottom; white-space: pre; }
td:first-child { text-align: left; padding: 2px 10px 2px 3px; }
table { border: 0; }
a.symlink { font-style: italic; }
</style>        
</head>        
<body>
""")
        o_list.append('<H1>%s</H1>' % (displaypath,))
        o_list.append("<hr/><table>")

        if displaypath == mapdirprefix or displaypath == mapdirprefix + '/':
            o_list.append('<tr><td colspan="4">Top level share</td></tr>')
        else:
            o_list.append('<tr><td colspan="4"><a href="' + websupportfuncs.getLevelUpURL(displaypath) + '">Up to higher level</a></td></tr>')

        for f in resourceAL.getCollectionContents(mappedpath):
            reshref = websupportfuncs.cleanUpURL(displaypath + '/' + f)
            pathname = resourceAL.joinPath(mappedpath, f)

            descriptorarray = resourceAL.getResourceDescriptor(pathname)
            

            o_list.append('<tr><td><A href="%s">%s</A></td><td>' % (reshref, f))
            o_list.append('</td><td></td><td>'.join(descriptorarray))
            o_list.append('</td></tr>\n')
            
            #</td><td>%s</td><td></td><td>%s</td><td></td><td>%s</td></tr>\n' % (reshref, f, label, filesize, filemodifieddate))
        o_list.append('</table><hr/>\n%s<BR>\n%s\n</body></html>' % (trailer,httpdatehelper.getstrftime()))


        start_response('200 OK', [('Content-Type', 'text/html'), ('Date',httpdatehelper.getstrftime())])
        return [''.join(o_list)]


    # supports If and HTTP If Conditionals
    def doGETHEADFile(self, environ, start_response):

        environ['HTTP_DEPTH'] = '0' #nothing else allowed
        mappedpath = environ['pyfileserver.mappedpath']
        displaypath =  environ['pyfileserver.mappedURI']
        resourceAL = environ['pyfileserver.resourceAL']

        self.evaluateSingleIfConditionalDoException( mappedpath, displaypath, environ, start_response)
        self.evaluateSingleHTTPConditionalsDoException( mappedpath, displaypath, environ, start_response)

        if resourceAL.supportContentLength(mappedpath):
            filesize = resourceAL.getContentLength(mappedpath)
        else:
            filesize = -1 # flag logic to read until EOF
        if resourceAL.supportLastModified(mappedpath):
            lastmodified = resourceAL.getLastModified(mappedpath)            
        else:
            lastmodified = -1
         
        if resourceAL.supportEntityTag(mappedpath):
            entitytag = resourceAL.getEntityTag(mappedpath)         
        else:
            entitytag = '[]'

        ## Ranges      
        doignoreranges = (not resourceAL.supportContentLength(mappedpath)) or (not resourceAL.supportRanges(mappedpath))
        if 'HTTP_RANGE' in environ and 'HTTP_IF_RANGE' in environ and not doignoreranges:
            ifrange = environ['HTTP_IF_RANGE']
            #try as http-date first
            secstime = httpdatehelper.getsecstime(ifrange)
            if secstime:
                if lastmodified != secstime:
                    doignoreranges = True
            else:
                #use as entity tag
                ifrange = ifrange.strip("\" ")
                if (not resourceAL.supportEntityTag(mappedpath)) or ifrange != entitytag:
                    doignoreranges = True

        ispartialranges = False
        if 'HTTP_RANGE' in environ and not doignoreranges:
            ispartialranges = True
            listRanges, totallength = websupportfuncs.obtainContentRanges(environ['HTTP_RANGE'], filesize)
            if len(listRanges) == 0:
                #No valid ranges present
                raise HTTPRequestException(processrequesterrorhandler.HTTP_RANGE_NOT_SATISFIABLE)

            #More than one range present -> take only the first range, since multiple range returns require multipart, which is not supported         
            #obtainContentRanges supports more than one range in case the above behaviour changes in future
            (rangestart, rangeend, rangelength) = listRanges[0]
        else:
            (rangestart, rangeend, rangelength) = (0L, filesize - 1, filesize)
            totallength = filesize

        ## Content Processing 
        mimetype = resourceAL.getContentType(mappedpath)

        responseHeaders = []
        if resourceAL.supportContentLength(mappedpath):
            responseHeaders.append(('Content-Length', rangelength))
        if resourceAL.supportLastModified(mappedpath):
            responseHeaders.append(('Last-Modified', httpdatehelper.getstrftime(lastmodified)))
        responseHeaders.append(('Content-Type', mimetype))
        responseHeaders.append(('Date', httpdatehelper.getstrftime()))
        if resourceAL.supportEntityTag(mappedpath):
            responseHeaders.append(('ETag', '"%s"' % entitytag))
 
        if ispartialranges:
            responseHeaders.append(('Content-Ranges', 'bytes ' + str(rangestart) + '-' + str(rangeend) + '/' + rangelength))
            start_response('206 Partial Content', responseHeaders)   
        else:
            start_response('200 OK', responseHeaders)

        if environ['REQUEST_METHOD'] == 'HEAD':
            yield ''
            return

        fileobj = resourceAL.openResourceForRead(mappedpath)

        if not doignoreranges:
            fileobj.seek(rangestart)

        contentlengthremaining = rangelength
        while 1:
            if contentlengthremaining < 0 or contentlengthremaining > BUFFER_SIZE:
                readbuffer = fileobj.read(BUFFER_SIZE)
            else:
                readbuffer = fileobj.read(contentlengthremaining)
            yield readbuffer
            contentlengthremaining -= len(readbuffer)
            if len(readbuffer) == 0 or contentlengthremaining == 0:
                break
        fileobj.close()
        return


    def doMKCOL(self, environ, start_response):               
        
        # check content length for request body entries
        try:
            contentlengthtoread = long(environ.get('CONTENT_LENGTH', 0))
        except ValueError: # This gets raised when something invalid is given
            contentlengthtoread = 0 
        if contentlengthtoread != 0:
            #Do not understand ANY request body entities
            raise HTTPRequestException(processrequesterrorhandler.HTTP_MEDIATYPE_NOT_SUPPORTED)
            
        environ['HTTP_DEPTH'] = '0' #nothing else allowed
        mappedpath = environ['pyfileserver.mappedpath']
        displaypath =  environ['pyfileserver.mappedURI']
        resourceAL = environ['pyfileserver.resourceAL']

        # isUrlLocked returns Lock Type - None if not locked
        if resourceAL.exists(mappedpath) or locklibrary.isUrlLocked(self._lockmanager, displaypath):
            self.evaluateSingleIfConditionalDoException( mappedpath, displaypath, environ, start_response, checkLock=True)
        self.evaluateSingleHTTPConditionalsDoException( mappedpath, displaypath, environ, start_response)

        if resourceAL.exists(mappedpath):
            raise HTTPRequestException(processrequesterrorhandler.HTTP_METHOD_NOT_ALLOWED)         

        # check if parent collection is locked
        parentdir = resourceAL.getContainingCollection(mappedpath)
        urlparentpath = websupportfuncs.getLevelUpURL(displaypath)      
        if locklibrary.isUrlLocked(self._lockmanager, urlparentpath):
            self.evaluateSingleIfConditionalDoException( parentdir, urlparentpath, environ, start_response, checkLock=True)

        if not resourceAL.isCollection(parentdir):
            # @@: This should give an error messages about why the conflict occurred:
            raise HTTPRequestException(processrequesterrorhandler.HTTP_CONFLICT)          
        try:   
            resourceAL.createCollection(mappedpath)
            locklibrary.checkLocksToAdd(self._lockmanager, displaypath)
        except HTTPRequestException, e:
            raise
        except Exception, e:
            raise HTTPRequestException(processrequesterrorhandler.HTTP_INTERNAL_ERROR, srcexception=e) 

        if resourceAL.exists(mappedpath):
            start_response("201 Created", [('Content-Length',0)])
        else:
            start_response("200 OK", [('Content-Length',0)])
        return ['']


    def doDELETE(self, environ, start_response):
        mappedpath = environ['pyfileserver.mappedpath']
        displaypath =  environ['pyfileserver.mappedURI']
        resourceAL = environ['pyfileserver.resourceAL']

        if not resourceAL.exists(mappedpath):
            raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_FOUND)         

        if resourceAL.isCollection(mappedpath): #delete over collection
            environ['HTTP_DEPTH'] = 'infinity'
        else:
            environ['HTTP_DEPTH'] = '0'

        actionList = websupportfuncs.getDepthActionList(resourceAL, mappedpath, displaypath, environ['HTTP_DEPTH'], False)

        dictError = {} #errors in deletion
        dictHidden = {} #hidden errors, ancestors of failed deletes
        for (filepath, filedisplaypath) in actionList:
            if filepath in dictHidden:
                dictHidden[resourceAL.getContainingCollection(filepath)] = ''
                continue            
            try:
                urlparentpath = websupportfuncs.getLevelUpURL(filedisplaypath)
                if locklibrary.isUrlLocked(self._lockmanager, urlparentpath):
                    self.evaluateSingleIfConditionalDoException( resourceAL.getContainingCollection(filepath), urlparentpath, environ, start_response, True)

                self.evaluateSingleIfConditionalDoException( filepath, filedisplaypath, environ, start_response, True)
                self.evaluateSingleHTTPConditionalsDoException( filepath, filedisplaypath, environ, start_response)

                if resourceAL.isCollection(filepath):
                    resourceAL.deleteCollection(filepath)
                else:
                    resourceAL.deleteResource(filepath)
                propertylibrary.removeProperties(self._propertymanager, filedisplaypath)
                locklibrary.removeAllLocksFromUrl(self._lockmanager, filedisplaypath)
            except HTTPRequestException, e:
                dictError[filedisplaypath] = processrequesterrorhandler.interpretErrorException(e)
                dictHidden[resourceAL.getContainingCollection(filepath)] = ''
            except Exception, e:
#                print repr(e)
#                print traceback.format_exception_only(sys.exc_type, sys.exc_value)
                dictError[filedisplaypath] = '500 Internal Server Error'
                dictHidden[resourceAL.getContainingCollection(filepath)] = ''
            else:
                if resourceAL.exists(filepath) and filedisplaypath not in dictError:
                    dictError[filedisplaypath] = '500 Internal Server Error'
                    dictHidden[resourceAL.getContainingCollection(filepath)] = ''

        if len(dictError) == 1 and displaypath in dictError:
            start_response(dictError[displaypath], [('Content-Length','0')])
            yield ''      
        elif len(dictError) > 0:
            start_response('207 Multi Status', [('Content-Length','0')])
            yield "<?xml version='1.0' ?>\n<D:multistatus xmlns:D='DAV:'>"
            for filedisplaypath in dictError.keys():
                yield "<D:response>\n<D:href>" + websupportfuncs.constructFullURL(filedisplaypath, environ) + "</D:href>"            
                yield "<D:status>HTTP/1.1 " + dictError[filedisplaypath] + "</D:status>\n</D:response>"            
            yield "</D:multistatus>"
        else:
            start_response('204 No Content', [('Content-Length','0')])
            yield ''
        return


    def doPROPPATCH(self, environ, start_response):
        environ['HTTP_DEPTH'] = '0' #nothing else allowed
        mappedpath = environ['pyfileserver.mappedpath']
        displaypath =  environ['pyfileserver.mappedURI']
        resourceAL = environ['pyfileserver.resourceAL']

        self.evaluateSingleIfConditionalDoException( mappedpath, displaypath, environ, start_response, checkLock=True)
        self.evaluateSingleHTTPConditionalsDoException( mappedpath, displaypath, environ, start_response)

        try:
            contentlengthtoread = long(environ.get('CONTENT_LENGTH', 0))
        except ValueError:
            contentlengthtoread = 0

        requestbody = ''
        if contentlengthtoread > 0:
            requestbody = environ['wsgi.input'].read(contentlengthtoread)

        try:
            doc = Sax2.Reader().fromString(requestbody)
        except Exception, e:
            raise HTTPRequestException(processrequesterrorhandler.HTTP_BAD_REQUEST, srcexception=e)   
        pproot = doc.documentElement
        if pproot.namespaceURI != 'DAV:' or pproot.localName != 'propertyupdate':
            raise HTTPRequestException(processrequesterrorhandler.HTTP_BAD_REQUEST)   

        propupdatelist = []
        for ppnode in pproot.childNodes:
            if ppnode.namespaceURI != 'DAV:' or ppnode.localName not in ('remove', 'set'):
                continue

            for propnode in ppnode.childNodes:
                if propnode.namespaceURI != 'DAV:' or propnode.localName != 'prop':
                    continue

                for propertynode in propnode.childNodes: 
                    if propertynode.nodeType != xml.dom.Node.ELEMENT_NODE: 
                        continue

                    propvalue = None
                    if ppnode.localName == 'set':
                        if len(propertynode.childNodes) == 1 and propertynode.firstChild.nodeType == xml.dom.Node.TEXT_NODE:
                            propvalue = propertynode.firstChild.nodeValue
                        else:
                            propvaluestream = StringIO.StringIO()
                            for childnode in propertynode.childNodes:
                                xml.dom.ext.PrettyPrint(childnode, stream=propvaluestream)
                            propvalue = propvaluestream.getvalue()
                            propvaluestream.close()
                            
                    verifyns = propertynode.namespaceURI or ''
                    propupdatelist.append( ( verifyns , propertynode.localName , ppnode.localName , propvalue) )

        successflag = True
        writeresultlist = []
        for (propns, propname , propmethod , propvalue) in propupdatelist:
            try:         
                propertylibrary.writeProperty(self._propertymanager, resourceAL, mappedpath, displaypath, propns, propname , propmethod , propvalue, False)
            except HTTPRequestException, e:
                writeresult = processrequesterrorhandler.interpretErrorException(e)
            except:
                writeresult = '500 Internal Server Error'
            else:
                writeresult = '200 OK'
            writeresultlist.append( (propns, propname, writeresult) )
            successflag = successflag and writeresult == "200 OK"

        start_response('207 Multistatus', [('Content-Type','text/xml'), ('Date',httpdatehelper.getstrftime())])

        if successflag:
            yield "<?xml version='1.0' ?>\n<D:multistatus xmlns:D='DAV:'>\n<D:response>"
            yield "<D:href>" + websupportfuncs.constructFullURL(displaypath, environ) + "</D:href>"    
            laststatus = ''
            for (propns, propname , propmethod , propvalue) in propupdatelist:
                try:
                    propertylibrary.writeProperty(self._propertymanager, resourceAL, mappedpath, displaypath, propns, propname , propmethod , propvalue, True)
                except HTTPRequestException, e:
                    propstatus = processrequesterrorhandler.interpretErrorException(e)
                except:
                    propstatus = '500 Internal Server Error'
                else:
                    propstatus = '200 OK'
                if laststatus == '':
                    yield "<D:propstat>\n<D:prop>"                                  
                if propstatus != laststatus and laststatus != '':
                    yield "</D:prop>\n<D:status>HTTP/1.1 " + laststatus + "</D:status>\n</D:propstat>\n<D:propstat>\n<D:prop>" 
                if propns == 'DAV:':
                    yield "<D:" + propname + "/>"
                else:
                    if propns is not None and propns != '':
                        yield "<A:" + propname + " xmlns:A='" + propns + "'/>"
                    else:
                        yield "<" + propname + " xmlns='" + propns + "'/>"
                laststatus = propstatus
            if laststatus != '':
                yield "</D:prop>\n<D:status>HTTP/1.1 " + laststatus + "</D:status>\n</D:propstat>"         
            yield "</D:response>\n</D:multistatus>"
        else:
            yield "<?xml version='1.0' ?>\n<D:multistatus xmlns:D='DAV:'>\n<D:response>"
            yield "<D:href>" + websupportfuncs.constructFullURL(displaypath, environ) + "</D:href>"    
            laststatus = ''
            for (propns, propname, propstatus) in writeresultlist:
                if propstatus == '200 OK':
                    propstatus = '424 Failed Dependency'
                if laststatus == '':
                    yield "<D:propstat>\n<D:prop>"                                  
                if propstatus != laststatus and laststatus != '':
                    yield "</D:prop>\n<D:status>HTTP/1.1 " + laststatus + "</D:status>\n</D:propstat>\n<D:propstat>\n<D:prop>" 
                if propns == 'DAV:':
                    yield "<D:" + propname + "/>"
                else:
                    if propns is not None and propns != '':
                        yield "<A:" + propname + " xmlns:A='" + propns + "'/>"
                    else:
                        yield "<" + propname + " xmlns='" + propns + "'/>"
                laststatus = propstatus
            if laststatus != '':
                yield "</D:prop>\n<D:status>HTTP/1.1 " + laststatus + "</D:status>\n</D:propstat>"         
            yield "</D:response>\n</D:multistatus>"
        return

    # does not yet support If and If HTTP Conditions   
    def doPROPFIND(self, environ, start_response):

        environ.setdefault('HTTP_DEPTH', '0')            
        mappedpath = environ['pyfileserver.mappedpath']
        displaypath =  environ['pyfileserver.mappedURI']
        resourceAL = environ['pyfileserver.resourceAL']

        try:
            contentlengthtoread = long(environ.get('CONTENT_LENGTH', 0))
        except ValueError:
            contentlengthtoread = 0

        requestbody = ''
        if contentlengthtoread > 0:
            requestbody = environ['wsgi.input'].read(contentlengthtoread)

        if requestbody == '':
            requestbody = "<D:propfind xmlns:D='DAV:'><D:allprop/></D:propfind>"      

        try:
            doc = Sax2.Reader().fromString(requestbody)
        except Exception, e:
            raise HTTPRequestException(processrequesterrorhandler.HTTP_BAD_REQUEST, srcexception=e)   

        pfroot = doc.documentElement
        if pfroot.namespaceURI != 'DAV:' or pfroot.localName != 'propfind':
            raise HTTPRequestException(processrequesterrorhandler.HTTP_BAD_REQUEST)   

        if not resourceAL.exists(mappedpath):
            raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_FOUND)

        reslist = websupportfuncs.getDepthActionList(resourceAL, mappedpath, displaypath, environ['HTTP_DEPTH'], True)

        propList = []
        propFindMode = 3
        for pfnode in pfroot.childNodes:
            if pfnode.namespaceURI == 'DAV:' and pfnode.localName == 'allprop':
                propFindMode = 1  
                break
            if pfnode.namespaceURI == 'DAV:' and pfnode.localName == 'propname':
                propFindMode = 2       
                break
            if pfnode.namespaceURI == 'DAV:' and pfnode.localName == 'prop':
                pfpList = pfnode.childNodes
                for pfpnode in pfpList:
                    if pfpnode.nodeType == xml.dom.Node.ELEMENT_NODE:
                        verifyns = pfpnode.namespaceURI or ''
                        propList.append( (verifyns, pfpnode.localName) )       

        start_response('207 Multistatus', [('Content-Type','text/xml'), ('Date',httpdatehelper.getstrftime())])

        yield "<?xml version='1.0' ?>"
        yield "<D:multistatus xmlns:D='DAV:'>"
        for (respath , resdisplayname) in reslist:
            yield "<D:response>"
            yield "<D:href>" + websupportfuncs.constructFullURL(resdisplayname, environ) + "</D:href>"    

            if propFindMode == 1 or propFindMode == 2:
                propList = propertylibrary.getApplicablePropertyNames(self._propertymanager, self._lockmanager, resourceAL, respath, resdisplayname)

            if propFindMode == 2:
                yield "<D:propstat>\n<D:prop>"
                for (propns, propname) in propList:
                    if propns == 'DAV:':
                        yield "<D:" + propname + "/>"
                    else:
                        if propns is not None and propns != '':
                            yield "<A:" + propname + " xmlns:A='" + propns + "'/>"
                        else:
                            yield "<" + propname + " xmlns='" + propns + "'/>"
                yield "</D:prop>\n<D:status>HTTP/1.1 200 OK</D:status>\n</D:propstat>"
            else:
                laststatus = ''
                for (propns, propname) in propList:
                    try:
#                       self.evaluateSingleIfConditionalDoException( filepath, filedisplaypath, environ, start_response)
#                       self.evaluateSingleHTTPConditionalsDoException( filepath, filedisplaypath, environ, start_response)
                        propvalue = propertylibrary.getProperty(self._propertymanager, self._lockmanager, resourceAL, respath, resdisplayname, propns, propname)   
                        propstatus = "200 OK"
                    except HTTPRequestException, e:
                        propvalue = ''
                        propstatus = processrequesterrorhandler.interpretErrorException(e)
                    except Exception, e:
#                        print repr(e)
#                        print traceback.format_exception_only(sys.exc_type, sys.exc_value)
                        propvalue = ''
                        propstatus = '500 Internal Server Error'
                    if laststatus == '':
                        yield "<D:propstat>\n<D:prop>"                                  
                    if propstatus != laststatus and laststatus != '':
                        yield "</D:prop>\n<D:status>HTTP/1.1 " + laststatus + "</D:status>\n</D:propstat>\n<D:propstat>\n<D:prop>" 
                    if propvalue is None:
                        propvalue = '';               
                    if propns == 'DAV:':
                        yield "<D:" + propname + ">"
                        yield propvalue.encode('utf-8') 
                        yield "</D:"+propname+">"
                    else:
                        if propns != None and propns != '':
                            yield "<A:" + propname + " xmlns:A='" + propns + "' >"
                            yield propvalue.encode('utf-8') 
                            yield "</A:"+propname+">"
                        else:
                            yield "<" + propname + " xmlns='" + propns + "' >"
                            yield propvalue.encode('utf-8') 
                            yield "</"+propname+">"
                    laststatus = propstatus
                if laststatus != '':
                    yield "</D:prop>\n<D:status>HTTP/1.1 " + laststatus + "</D:status>\n</D:propstat>"         
            yield "</D:response>"
        yield "</D:multistatus>"      
        return 

    def doCOPY(self, environ, start_response):
        mappedrealm = environ['pyfileserver.mappedrealm']
        mappedpath = environ['pyfileserver.mappedpath']
        displaypath =  environ['pyfileserver.mappedURI']
        resourceAL = environ['pyfileserver.resourceAL']

        if not resourceAL.exists(mappedpath):
            raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_FOUND)         

        environ.setdefault('HTTP_DEPTH', 'infinity')         
        if environ['HTTP_DEPTH'] != 'infinity':
            environ['HTTP_DEPTH'] = '0'


        if 'HTTP_DESTINATION' not in environ:
            raise HTTPRequestException(processreuesterrorhandler.HTTP_BAD_REQUEST)

        destrealm = environ['pyfileserver.destrealm']
        destpath = environ['pyfileserver.destpath']
        destdisplaypath = environ['pyfileserver.destURI']  

        destexists = resourceAL.exists(destpath)

        # @@: Thinking back to my comments on dispatching, it would in many ways make
        # this worse.  Unless, however, you turned a copy across realms into a PUT
        # (reusing the credentials you have).
        if mappedrealm != destrealm:
            #inter-realm copying not supported, since its not possible to authentication-wise
            raise HTTPRequestException(processrequesterrorhandler.HTTP_BAD_REQUEST)

        if mappedpath == destpath:
            raise HTTPRequestException(processrequesterrorhandler.HTTP_FORBIDDEN)

        ressrclist = websupportfuncs.getDepthActionList(resourceAL, mappedpath, displaypath, environ['HTTP_DEPTH'], True)
        resdestlist = websupportfuncs.getCopyDepthActionList(ressrclist, mappedpath, displaypath, destpath, destdisplaypath)

        if 'HTTP_OVERWRITE' not in environ:
            environ['HTTP_OVERWRITE'] = 'T'

        # @@: This is a complex and highly nested loop; it should be refactored somehow
        dictError = {}
        dictHidden = {}        
        for cpidx in range(0, len(ressrclist)):
            (filepath, filedisplaypath) = ressrclist[cpidx]     
            (destfilepath, destfiledisplaypath) = resdestlist[cpidx]     
            destparentpath = resourceAL.getContainingCollection(destfilepath)
            if destparentpath not in dictHidden:
                try:
                    self.evaluateSingleHTTPConditionalsDoException( filepath, filedisplaypath, environ, start_response) 
                    self.evaluateSingleIfConditionalDoException( filepath, filedisplaypath, environ, start_response)
                    if resourceAL.exists(destfilepath) or locklibrary.isUrlLocked(self._lockmanager, destfiledisplaypath):
                        self.evaluateSingleIfConditionalDoException( destfilepath, destfiledisplaypath, environ, start_response, True)

                    if not resourceAL.exists(destparentpath):
                        raise HTTPRequestException(processrequesterrorhandler.HTTP_CONFLICT)

                    if not resourceAL.exists(destfilepath):
                        urlparentpath = websupportfuncs.getLevelUpURL(destfiledisplaypath)
                        if locklibrary.isUrlLocked(self._lockmanager, urlparentpath):
                            self.evaluateSingleIfConditionalDoException( resourceAL.getContainingCollection(destfilepath), urlparentpath, environ, start_response, True)


                    if environ['HTTP_OVERWRITE'] == 'F':
                        if resourceAL.exists(destfilepath):
                            raise HTTPRequestException(processrequesterrorhandler.HTTP_PRECONDITION_FAILED)
                    # @@: This should be elif:, not else:if:
                    else: #Overwrite = T
                        if resourceAL.exists(destfilepath):
                            actionList = websupportfuncs.getDepthActionList(resourceAL, destfilepath, destfiledisplaypath, 'infinity', False)
                            FdictHidden = {} #hidden errors, ancestors of failed deletes         
                            # do DELETE with infinity
                            for (Ffilepath, Ffiledisplaypath) in actionList:         
                                if Ffilepath not in FdictHidden:
                                    try:                           
                                        if resourceAL.isCollection(Ffilepath):
                                            resourceAL.deleteCollection(Ffilepath)
                                        else:
                                            resourceAL.deleteResource(Ffilepath)
                                        propertylibrary.removeProperties(self._propertymanager, Ffiledisplaypath)               
                                    except Exception:
                                        pass
                                    if resourceAL.exists(Ffilepath):
                                        FdictHidden[resourceAL.getContainingCollection(Ffilepath)] = ''
                                else:
                                    FdictHidden[resourceAL.getContainingCollection(Ffilepath)] = ''
                            if resourceAL.exists(Ffilepath):
                                raise HTTPRequestException(processrequesterrorhandler.HTTP_INTERNAL_ERROR) 

                    if resourceAL.isCollection(filepath):
                        resourceAL.createCollection(destfilepath)
                    else:   
                        resourceAL.copyResource(filepath, destfilepath)
                    propertylibrary.copyProperties(self._propertymanager, filedisplaypath, destfiledisplaypath)     
                    locklibrary.checkLocksToAdd(self._lockmanager, destfiledisplaypath)

                except HTTPRequestException, e:
                    dictError[destfiledisplaypath] = processrequesterrorhandler.interpretErrorException(e)
                    dictHidden[destfilepath] = ''
                except Exception, e:
                    pass   
                if not resourceAL.exists(destfilepath) and destfiledisplaypath not in dictError:
                    dictError[destfiledisplaypath] = '500 Internal Server Error'    
                    dictHidden[destfilepath] = ''           
            else:
                dictHidden[destfilepath] = ''

        if len(dictError) == 1 and destdisplaypath in dictError:
            start_response(dictError[destdisplaypath], [('Content-Length','0')])
            yield ''      
        elif len(dictError) > 0:
            start_response('207 Multi Status', [('Content-Length','0')])
            yield "<?xml version='1.0' ?>\n<D:multistatus xmlns:D='DAV:'>"
            for filedisplaypath in dictError.keys():
                yield "<D:response>\n<D:href>" + websupportfuncs.constructFullURL(filedisplaypath, environ) + "</D:href>"            
                yield "<D:status>HTTP/1.1 " + dictError[filedisplaypath] + "</D:status>\n</D:response>"            
            yield "</D:multistatus>"
        else:
            if destexists:
                start_response('204 No Content', [('Content-Length','0')])         
            else:
                start_response('201 Created', [('Content-Length','0')])
            yield ''
        return

    def doMOVE(self, environ, start_response):
        mappedrealm = environ['pyfileserver.mappedrealm']
        mappedpath = environ['pyfileserver.mappedpath']
        displaypath =  environ['pyfileserver.mappedURI']
        resourceAL = environ['pyfileserver.resourceAL']

        if not resourceAL.exists(mappedpath):
            raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_FOUND)         

        environ['HTTP_DEPTH'] = 'infinity'


        if 'HTTP_DESTINATION' not in environ:
            raise HTTPRequestException(processreuesterrorhandler.HTTP_BAD_REQUEST)

        destrealm = environ['pyfileserver.destrealm']
        destpath = environ['pyfileserver.destpath']
        destdisplaypath = environ['pyfileserver.destURI']      

        destexists = resourceAL.exists(destpath)

        if mappedrealm != destrealm:
            #inter-realm copying not supported, since its not possible to authentication-wise
            raise HTTPRequestException(processrequesterrorhandler.HTTP_BAD_REQUEST)

        if mappedpath == destpath:
            raise HTTPRequestException(processrequesterrorhandler.HTTP_FORBIDDEN)

        ressrclist = websupportfuncs.getDepthActionList(resourceAL, mappedpath, displaypath, environ['HTTP_DEPTH'], True)
        resdelsrclist = websupportfuncs.getDepthActionList(resourceAL, mappedpath, displaypath, environ['HTTP_DEPTH'], False)

        resdestlist = websupportfuncs.getCopyDepthActionList(ressrclist, mappedpath, displaypath, destpath, destdisplaypath)

        if 'HTTP_OVERWRITE' not in environ:
            environ['HTTP_OVERWRITE'] = 'T'

        dictError = {}
        dictHidden = {}        
        dictDoNotDel = {}
        # @@: Against, this should be refactored to be shorter and less deeply nested
        for cpidx in range(0, len(ressrclist)):
            (filepath, filedisplaypath) = ressrclist[cpidx]     
            (destfilepath, destfiledisplaypath) = resdestlist[cpidx]     
            destparentpath = resourceAL.getContainingCollection(destfilepath)
            if destparentpath not in dictHidden:
                try:
                    self.evaluateSingleHTTPConditionalsDoException( filepath, filedisplaypath, environ, start_response) 
                    self.evaluateSingleIfConditionalDoException( filepath, filedisplaypath, environ, start_response, True)
                    if resourceAL.exists(destfilepath) or locklibrary.isUrlLocked(self._lockmanager, destfiledisplaypath) != None:
                        self.evaluateSingleIfConditionalDoException( destfilepath, destfiledisplaypath, environ, start_response, True)

                    if not resourceAL.exists(destparentpath):
                        raise HTTPRequestException(processrequesterrorhandler.HTTP_CONFLICT)

                    if not resourceAL.exists(filepath):
                        urlparentpath = websupportfuncs.getLevelUpURL(filedisplaypath)
                        if locklibrary.isUrlLocked(self._lockmanager, urlparentpath):
                            self.evaluateSingleIfConditionalDoException( resourceAL.getContainingCollection(filepath), urlparentpath, environ, start_response, True)

                    if not resourceAL.exists(destfilepath):
                        urlparentpath = websupportfuncs.getLevelUpURL(destfiledisplaypath)
                        if locklibrary.isUrlLocked(self._lockmanager, urlparentpath):
                            self.evaluateSingleIfConditionalDoException( resourceAL.getContainingCollection(destfilepath), urlparentpath, environ, start_response, True)

                    if environ['HTTP_OVERWRITE'] == 'F':
                        if resourceAL.exists(destfilepath):
                            raise HTTPRequestException(processrequesterrorhandler.HTTP_PRECONDITION_FAILED)
                    else: #Overwrite = T
                        if resourceAL.exists(destfilepath):
                            actionList = websupportfuncs.getDepthActionList(resourceAL, destfilepath, destfiledisplaypath, 'infinity', False)
                            FdictHidden = {} #hidden errors, ancestors of failed deletes         
                            # do DELETE with infinity
                            for (Ffilepath, Ffiledisplaypath) in actionList:         
                                if Ffilepath not in FdictHidden:
                                    try:                           
                                        if resourceAL.isCollection(Ffilepath):
                                            resourceAL.deleteCollection(Ffilepath)
                                        else:
                                            resourceAL.deleteResource(Ffilepath)
                                        propertylibrary.removeProperties(self._propertymanager, Ffiledisplaypath)               
                                    except Exception:
                                        pass
                                    if resourceAL.exists(Ffilepath):
                                        FdictHidden[resourceAL.getContainingCollection(Ffilepath)] = ''
                                else:
                                    FdictHidden[resourceAL.getContainingCollection(Ffilepath)] = ''
                            if resourceAL.exists(Ffilepath):
                                raise HTTPRequestException(processrequesterrorhandler.HTTP_INTERNAL_ERROR) 

                    if resourceAL.isCollection(filepath):
                        resourceAL.createCollection(destfilepath)
                    else:   
                        resourceAL.copyResource(filepath, destfilepath)
                    propertylibrary.copyProperties(self._propertymanager, filedisplaypath, destfiledisplaypath)     
                    locklibrary.checkLocksToAdd(self._lockmanager, destfiledisplaypath)

                except HTTPRequestException, e:
                    dictError[destfiledisplaypath] = processrequesterrorhandler.interpretErrorException(e)
                    dictHidden[destfilepath] = ''           
                    dictDoNotDel[filepath]=''
                except Exception, e:
                    pass   
                if not resourceAL.exists(destfilepath) and destfiledisplaypath not in dictError:
                    dictError[destfiledisplaypath] = '500 Internal Server Error'    
                    dictHidden[destfilepath] = ''           
                    dictDoNotDel[filepath]=''
            else:
                dictHidden[destfilepath] = ''
                dictDoNotDel[filepath]=''

        # do DELETE with infinity on source
        FdictHidden = {} #hidden errors, ancestors of failed deletes         
        for (Ffilepath, Ffiledisplaypath) in resdelsrclist:         
            if Ffilepath not in FdictHidden and Ffilepath not in dictDoNotDel:
                try:      
                    if resourceAL.isCollection(Ffilepath):
                        resourceAL.deleteCollection(Ffilepath)
                    else:
                        resourceAL.deleteResource(Ffilepath)
                    propertylibrary.removeProperties(self._propertymanager, Ffiledisplaypath)               
                    locklibrary.removeAllLocksFromUrl(self._lockmanager, Ffiledisplaypath)
                except Exception:
                    pass
                if resourceAL.exists(Ffilepath):
                    FdictHidden[resourceAL.getContainingCollection(Ffilepath)] = ''
            else:
                FdictHidden[resourceAL.getContainingCollection(Ffilepath)] = ''

        if len(dictError) == 1 and destdisplaypath in dictError:
            start_response(dictError[destdisplaypath], [('Content-Length','0')])
            yield ''      
        elif len(dictError) > 0:
            start_response('207 Multi Status', [('Content-Length','0')])
            yield "<?xml version='1.0' ?>\n<D:multistatus xmlns:D='DAV:'>"
            for filedisplaypath in dictError.keys():
                yield "<D:response>\n<D:href>" + websupportfuncs.constructFullURL(filedisplaypath, environ) + "</D:href>"            
                yield "<D:status>HTTP/1.1 " + dictError[filedisplaypath] + "</D:status>\n</D:response>"            
            yield "</D:multistatus>"
        else:
            if destexists:
                start_response('204 No Content', [('Content-Length','0')])         
            else:
                start_response('201 Created', [('Content-Length','0')])
            yield ''
        return

    def doLOCK(self, environ, start_response):
        environ.setdefault('HTTP_DEPTH', 'infinity')         
        if environ['HTTP_DEPTH'] != '0':
            environ['HTTP_DEPTH'] = 'infinity'    # only two acceptable

        mappedpath = environ['pyfileserver.mappedpath']
        displaypath =  environ['pyfileserver.mappedURI']
        resourceAL = environ['pyfileserver.resourceAL']

        try:
            contentlengthtoread = long(environ.get('CONTENT_LENGTH', 0))
        except ValueError:
            contentlengthtoread = 0

        requestbody = ''
        if contentlengthtoread > 0:
            requestbody = environ['wsgi.input'].read(contentlengthtoread)

        # reader function will return None on invalid         
        timeoutsecs = locklibrary.readTimeoutValueHeader(environ.get('HTTP_TIMEOUT',''))

        lockfailure = False
        dictStatus = {}

        if requestbody == '':
            #refresh lock only
            environ['HTTP_DEPTH'] = '0'
            reslist = [(mappedpath , displaypath)]

            self.evaluateSingleIfConditionalDoException( mappedpath, displaypath, environ, start_response, checkLock=True)
            self.evaluateSingleHTTPConditionalsDoException( mappedpath, displaypath, environ, start_response)

            optlocklist = environ.get('pyfileserver.conditions.locklistcheck',[])
            for locklisttoken in optlocklist:
                locklibrary.refreshLock(self._lockmanager, locklisttoken,timeoutsecs)
                genlocktoken = locklisttoken

            dictStatus[displaypath] = "200 OK"      
        else:   

            try:
                doc = Sax2.Reader().fromString(requestbody)
            except Exception, e:
                raise HTTPRequestException(processrequesterrorhandler.HTTP_BAD_REQUEST, srcexception=e)   
            liroot = doc.documentElement
            if liroot.namespaceURI != 'DAV:' or liroot.localName != 'lockinfo':
                raise HTTPRequestException(processrequesterrorhandler.HTTP_BAD_REQUEST)   

            locktype = 'write'         # various defaults
            lockscope = 'exclusive'
            lockowner = ''
            lockdepth = environ['HTTP_DEPTH']

            for linode in liroot.childNodes:
                if linode.namespaceURI == 'DAV:' and linode.localName == 'lockscope':
                    for lsnode in linode.childNodes:
                        if lsnode.nodeType != xml.dom.Node.ELEMENT_NODE:
                            continue                       
                        if lsnode.namespaceURI == 'DAV:' and lsnode.localName in ['exclusive','shared']: 
                            lockscope = lsnode.localName 
                        else:
                            raise HTTPRequestException(processrequesterrorhandler.HTTP_PRECONDITION_FAILED)
                        break               
                elif linode.namespaceURI == 'DAV:' and linode.localName == 'locktype':
                    for ltnode in linode.childNodes:
                        if ltnode.nodeType == xml.dom.Node.ELEMENT_NODE:
                            continue
                        if ltnode.namespaceURI == 'DAV:' and ltnode.localName == 'write': 
                            locktype = 'write'   # only type accepted
                        else:
                            raise HTTPRequestException(processrequesterrorhandler.HTTP_PRECONDITION_FAILED)
                        break
                elif linode.namespaceURI == 'DAV:' and linode.localName == 'owner':
                    if len(linode.childNodes) == 1 and linode.firstChild.nodeType == xml.dom.Node.TEXT_NODE:
                        lockowner = linode.firstChild.nodeValue
                    else:
                        lockownerstream = StringIO.StringIO()
                        for childnode in linode.childNodes:
                            xml.dom.ext.PrettyPrint(childnode, stream=lockownerstream)
                        lockowner = lockownerstream.getvalue()
                        lockownerstream.close()                        

            genlocktoken = locklibrary.generateLock(self._lockmanager, environ['pyfileserver.username'], locktype, lockscope, lockdepth, lockowner, websupportfuncs.constructFullURL(displaypath, environ), timeoutsecs)

            reslist = websupportfuncs.getDepthActionList(resourceAL, mappedpath, displaypath, environ['HTTP_DEPTH'], True)
            for (filepath, filedisplaypath) in reslist:
                try:
                    self.evaluateSingleIfConditionalDoException(filepath, filedisplaypath, environ, start_response, False) # need not test for lock - since can try for shared lock
                    self.evaluateSingleHTTPConditionalsDoException(filepath, filedisplaypath, environ, start_response)

                    reschecklist = websupportfuncs.getDepthActionList(resourceAL, filepath, filedisplaypath, '1', True) 

                    #lock over collection may not clash with locks of members   
                    for (rescheckpath, rescheckdisplaypath) in reschecklist:
                        urllockscope = locklibrary.getUrlLockScope(self._lockmanager, rescheckdisplaypath)
                        if urllockscope is None or (urllockscope == 'shared' and lockscope == 'shared') :
                            pass
                        else:
                            raise HTTPRequestException(processrequesterrorhandler.HTTP_LOCKED)

                    locklibrary.addUrlToLock(self._lockmanager, filedisplaypath,genlocktoken)                  
                    dictStatus[filedisplaypath] = "200 OK"            
                except HTTPRequestException, e:
                    dictStatus[filedisplaypath] = processrequesterrorhandler.interpretErrorException(e)
                    lockfailure = True   
                except Exception:
                    dictStatus[filedisplaypath] = "500 Internal Server Error"
                    lockfailure = True

            if lockfailure:
                locklibrary.deleteLock(self._lockmanager, genlocktoken)

        # done everything, now report on status
        if environ['HTTP_DEPTH'] == '0' or len(reslist) == 1:
            if lockfailure:
                respcode = dictStatus[displaypath]   
                start_response( respcode, [('Content-Length','0')])
                yield ''
                return
            else:                     
                start_response( "200 OK", [('Content-Type','text/xml'),('Lock-Token',genlocktoken)])
                yield "<?xml version=\'1.0\' ?>"
                yield "<D:prop xmlns:D=\'DAV:\'><D:lockdiscovery>"            
                try:
                    propvalue = propertylibrary.getProperty(self._propertymanager, self._lockmanager, resourceAL, mappedpath, displaypath, 'DAV:', 'lockdiscovery')   
                    propstatus = "200 OK"
                except HTTPRequestException, e:
                    propvalue = ''
                    propstatus = processrequesterrorhandler.interpretErrorException(e)
                except:
                    propvalue = ''
                    propstatus = '500 Internal Server Error'
                yield propvalue
                yield '</D:lockdiscovery></D:prop>'
                return
        else: 
            if lockfailure:
                start_response("207 Multistatus", [('Content-Type','text/xml')])
            else:
                start_response("200 OK", [('Content-Type','text/xml'),('Lock-Token',genlocktoken)])
            yield "<?xml version='1.0' ?>"
            yield "<D:multistatus xmlns:D='DAV:'>"
            for (filepath, filedisplaypath) in reslist:
                yield "<D:response>"
                yield "<D:href>" + websupportfuncs.constructFullURL(filedisplaypath, environ) + "</D:href>"
                if dictStatus[filedisplaypath] == '200 OK':
                    yield "<D:propstat>"
                    yield "<D:prop><D:lockdiscovery>"
                    try:
                        propvalue = propertylibrary.getProperty(self._propertymanager, self._lockmanager, resourceAL, filepath, filedisplaypath, 'DAV:', 'lockdiscovery')   
                        propstatus = "200 OK"
                    except HTTPRequestException, e:
                        propvalue = ''
                        propstatus = processrequesterrorhandler.interpretErrorException(e)
                    except:
                        propvalue = ''
                        propstatus = '500 Internal Server Error'
                    yield propvalue
                    yield "</D:lockdiscovery></D:prop>"
                    if lockfailure:
                        yield "<D:status>HTTP/1.1 424 Failed Dependency</D:status>"
                    else:
                        yield "<D:status>HTTP/1.1 200 OK</D:status>"
                    yield "</D:propstat>"
                else: 
                    yield "<D:status>HTTP/1.1 " + dictStatus[filedisplaypath] + "</D:status>"
                yield "</D:response>"
            yield "</D:multistatus>"      
        return

    def doUNLOCK(self, environ, start_response):
        mappedpath = environ['pyfileserver.mappedpath']
        displaypath =  environ['pyfileserver.mappedURI']
        resourceAL = environ['pyfileserver.resourceAL']

        self.evaluateSingleIfConditionalDoException( mappedpath, displaypath, environ, start_response)
        self.evaluateSingleHTTPConditionalsDoException( mappedpath, displaypath, environ, start_response)

        if 'HTTP_LOCK_TOKEN' in environ:
            environ['HTTP_LOCK_TOKEN'] = environ['HTTP_LOCK_TOKEN'].strip('<>')
            if locklibrary.isUrlLockedByToken(self._lockmanager, displaypath,environ['HTTP_LOCK_TOKEN']):
                if locklibrary.isTokenLockedByUser(self._lockmanager, environ['HTTP_LOCK_TOKEN'], environ['pyfileserver.username']):
                    locklibrary.deleteLock(self._lockmanager, environ['HTTP_LOCK_TOKEN'])
                    start_response('204 No Content',  [('Content-Length','0')])        
                    return ['']      

        raise HTTPRequestException(processrequesterrorhandler.HTTP_BAD_REQUEST)
        return

    def evaluateSingleIfConditionalDoException(self, mappedpath, displaypath, environ, start_response, checkLock=False):
        resourceAL = environ['pyfileserver.resourceAL']

        if 'HTTP_IF' not in environ:
            if checkLock:
                #isUrlLocked returns lock type, None if unlocked
                if locklibrary.isUrlLocked(self._lockmanager, displaypath):
                    raise HTTPRequestException(processrequesterrorhandler.HTTP_LOCKED)            
            return
        if 'pyfileserver.conditions.if' not in environ:
            environ['pyfileserver.conditions.if'] = websupportfuncs.getIfHeaderDict(environ['HTTP_IF'])
        testDict = environ['pyfileserver.conditions.if']
        isnewfile = not resourceAL.exists(mappedpath)
        if isnewfile:
            lastmodified = -1 # nonvalid modified time
            entitytag = '[]' # Non-valid entity tag
            locktokenlist = locklibrary.getTokenListForUrlByUser(self._lockmanager, displaypath,environ['pyfileserver.username']) #null resources lock token not implemented yet
        else:
            if resourceAL.supportLastModified(mappedpath):
                lastmodified = resourceAL.getLastModified(mappedpath)            
            else:
                lastmodified = -1
            
            if resourceAL.supportEntityTag(mappedpath):
                entitytag = resourceAL.getEntityTag(mappedpath)         
            else:
                entitytag = '[]'

            locktokenlist = locklibrary.getTokenListForUrlByUser(self._lockmanager, displaypath,environ['pyfileserver.username'])

        fullurl = websupportfuncs.constructFullURL(displaypath, environ)
        if not websupportfuncs.testIfHeaderDict(resourceAL, mappedpath, testDict, fullurl, locktokenlist, entitytag):
            raise HTTPRequestException(processrequesterrorhandler.HTTP_PRECONDITION_FAILED) 

        if checkLock and locklibrary.isUrlLocked(self._lockmanager, displaypath):
            hasValidLockToken = False
            for locktoken in locktokenlist:
                headurl = locklibrary.getLockProperty(self._lockmanager, locktoken, 'LOCKHEADURL')
                if websupportfuncs.testForLockTokenInIfHeaderDict(testDict, locktoken, fullurl, headurl):
                    environ['pyfileserver.conditions.locklistcheck'] = [locktoken]
                    hasValidLockToken = True
            if not hasValidLockToken:
                raise HTTPRequestException(processrequesterrorhandler.HTTP_LOCKED)


    def evaluateSingleHTTPConditionalsDoException(self, mappedpath, displaypath, environ, start_response):
        resourceAL = environ['pyfileserver.resourceAL']

        if not ('HTTP_IF_MODIFIED_SINCE' in environ or 'HTTP_IF_UNMODIFIED_SINCE' in environ or 'HTTP_IF_MATCH' in environ or 'HTTP_IF_NONE_MATCH' in environ):
            return
        if resourceAL.exists(mappedpath):
            if resourceAL.supportLastModified(mappedpath):
                lastmodified = resourceAL.getLastModified(mappedpath)            
            else:
                lastmodified = -1
            
            if resourceAL.supportEntityTag(mappedpath):
                entitytag = resourceAL.getEntityTag(mappedpath)         
            else:
                entitytag = '[]'
        else:
            lastmodified = -1 # nonvalid modified time
            entitytag = '[]' # Non-valid entity tag
        websupportfuncs.evaluateHTTPConditionals(resourceAL, mappedpath, lastmodified, entitytag, environ)

