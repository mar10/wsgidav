"""
requestresolver
===============

:Module: pyfileserver.requestresolver
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com
:Project: PyFileServer, http://pyfilesync.berlios.de/
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

PyFileServer file sharing
-------------------------

PyFileServer allows the user to specify in PyFileServer.conf a number of 
realms, and a number of users for each realm. 

Realms
   Each realm corresponds to a filestructure on disk to be stored, 
   for example::
   
      addrealm('pubshare','/home/public/share') 
   
   would allow the users to access using WebDAV the directory/file 
   structure at /home/public/share from the url 
   http://<servername:port>/<approot>/pubshare

   The realm name is set as '/pubshare'

   e.g. /home/public/share/PyFileServer/LICENSE becomes accessible as
   http://<servername:port>/<approot>/pubshare/PyFileServer/LICENSE

Users
   A number of username/password pairs can be set for each realm::
      
      adduser('pubshare', 'username', 'password', 'description/unused')
   
   would add a username/password pair to realm /pubshare.

Note: if developers wish to maintain a separate users database, you can 
write your own domain controller for the HTTPAuthenticator. See 
httpauthentication.py and pyfiledomaincontroller.py for more details.


Request Resolver
----------------

This module is specific to the PyFileServer application

WSGI Middleware for Resolving Realm and Paths for the PyFileServer 
application.

Usage::

   from pyfileserver.requestresolver import RequestResolver
   WSGIApp = RequestResolver(InternalWSGIApp)

The RequestResolver resolves the requested URL to the following values 
placed in the environ dictionary. First it resolves the corresponding
realm::

   url: http://<servername:port>/<approot>/pubshare/PyFileServer/LICENSE
   environ['pyfileserver.mappedrealm'] = /pubshare

Based on the configuration given, the resource abstraction layer for the
realm is determined. if no configured abstraction layer is found, the
default abstraction layer fileabstractionlayer.FilesystemAbstractionLayer()
is used::
   
   environ['pyfileserver.resourceAL'] = fileabstractionlayer.MyOwnFilesystemAbstractionLayer()

The path identifiers for the requested url are then resolved using the
resource abstraction layer::

   environ['pyfileserver.mappedpath'] = /home/public/share/PyFileServer/LICENSE 
   environ['pyfileserver.mappedURI'] = /pubshare/PyFileServer/LICENSE

in this case, FilesystemAbstractionLayer resolves any relative paths 
to its canonical absolute path

The RequestResolver also resolves any value in the Destination request 
header, if present, to::
   
   Destination: http://<servername:port>/<approot>/pubshare/PyFileServer/LICENSE-dest
   environ['pyfileserver.destrealm'] = /pubshare
   environ['pyfileserver.destpath'] = /home/public/share/PyFileServer/LICENSE-dest 
   environ['pyfileserver.destURI'] = /pubshare/PyFileServer/LICENSE
   environ['pyfileserver.destresourceAL'] = fileabstractionlayer.MyOwnFilesystemAbstractionLayer()
   

Interface
---------

classes::
   
   RequestResolver: Request resolver for PyFileServer
"""


#Remarks:
#@@: If this were just generalized URL mapping, you'd map it like:
#    Incoming:
#        SCRIPT_NAME=<approot>; PATH_INFO=/pubshare/PyFileServer/LICENSE
#    After transforamtion:
#        SCRIPT_NAME=<approot>/pubshare; PATH_INFO=/PyFileServer/LICENSE
#    Then you dispatch to the application that serves '/home/public/share/'
#
#    This uses SCRIPT_NAME and PATH_INFO exactly how they are intended to be
#    used -- they give context about where you are (SCRIPT_NAME) and what you
#    still have to handle (PATH_INFO)
#
#    An example of an dispatcher that does this is paste.urlmap, and you use it
#    like:
#
#      urlmap = paste.urlmap.URLMap()
#      # urlmap is a WSGI application
#      urlmap['/pubshare'] = PyFileServerForPath('/home/public/share')
#
#    Now, that requires that you have a server that is easily
#    instantiated, but that's kind of a separate concern -- what you
#    really want is to do more general configuration at another level.  E.g.,
#    you might have::
#
#      app = config(urlmap, config_file)
#
#    Which adds the configuration from that file to the request, and
#    PyFileServerForPath then fetches that configuration.  paste.deploy
#    has another way of doing that at instantiation-time; either way
#    though you want to inherit configuration you can still use more general
#    dispatching.
#
#    Incidentally some WebDAV servers do redirection based on the user
#    agent (Zope most notably).  This is because of how WebDAV reuses
#    GET in an obnxious way, so that if you want to use WebDAV on pages
#    that also include dynamic content you have to mount the whole
#    thing at another point in the URL space, so you can GET the
#    content without rendering the dynamic parts.  I don't actually
#    like using user agents -- I'd rather mount the same resources at
#    two different URLs -- but it's just an example of another kind of
#    dispatching that can be done at a higher level.
#


__docformat__ = 'reStructuredText'

# Python Built-in imports
import urllib
import re

# PyFileServer Imports
import processrequesterrorhandler
from processrequesterrorhandler import HTTPRequestException
import websupportfuncs
import httpdatehelper

class RequestResolver(object):

    def __init__(self, application):
        self._application = application
      
    def __call__(self, environ, start_response):
        self._srvcfg = environ['pyfileserver.config']

        requestmethod =  environ['REQUEST_METHOD']
        requestpath = urllib.unquote(environ['PATH_INFO'])

        if requestmethod == 'TRACE':
            return self.doTRACE(environ, start_response)
      
        if requestpath == '*' and requestmethod == 'OPTIONS':
            return self.doOPTIONS(environ, start_response)

        if requestpath == '/' and requestmethod == 'OPTIONS':  #hotfix for WinXP
            return self.doOPTIONS(environ, start_response)

        if 'config_mapping' not in environ['pyfileserver.config']:
            if requestmethod == 'GET': 
                self.printConfigErrorMessage()
            else:
                raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_FOUND)
    
        (mappedrealm, mappedpath, displaypath, resourceAL) = self.resolveRealmURI(environ['pyfileserver.config'], requestpath)            
   
        if mappedrealm is None:
            raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_FOUND)

        environ['pyfileserver.mappedrealm'] = mappedrealm
        environ['pyfileserver.mappedpath'] = mappedpath 
        environ['pyfileserver.mappedURI'] = displaypath
        environ['pyfileserver.resourceAL'] = resourceAL

        if 'HTTP_DESTINATION' in environ:
            desturl = websupportfuncs.getRelativeURL(environ['HTTP_DESTINATION'], environ)
            (destrealm, destpath, destdisplaypath, destresourceAL) = self.resolveRealmURI(environ['pyfileserver.config'], desturl)            
      
            if destrealm is None:
                 raise HTTPRequestException(processrequesterrorhandler.HTTP_BAD_REQUEST)
   
            environ['pyfileserver.destrealm'] = destrealm
            environ['pyfileserver.destpath'] = destpath 
            environ['pyfileserver.destURI'] = destdisplaypath
            environ['pyfileserver.destresourceAL'] = destresourceAL
      

        if requestmethod == 'OPTIONS':
            return self.doOPTIONSSpec(environ, start_response)
      
        return self._application(environ, start_response)

    #TRACE pending, but not essential
    def doTRACE(self, environ, start_response):
        raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_IMPLEMENTED)
      
    def doOPTIONS(self, environ, start_response):
        headers = []
        headers.append( ('Content-Type', 'text/html') )
        headers.append( ('Content-Length','0') )
        headers.append( ('DAV','1,2') )
        headers.append( ('Server','DAV/2') )
        headers.append( ('Date',httpdatehelper.getstrftime()) )
        start_response('200 OK', headers)        
        return ['']  

    def doOPTIONSSpec(self, environ, start_response):
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
        
    def resolveRealmURI(self, srvcfg, requestpath):

        mapcfg = srvcfg['config_mapping']
        resALcfg = srvcfg['resAL_mapping']
        resALreg = srvcfg['resAL_library']

        # sorting by reverse length
        mapcfgkeys = mapcfg.keys()
        mapcfgkeys.sort(key = len, reverse = True)

        mapdirprefix = ''

        for tmp_mapdirprefix in mapcfgkeys:
            # @@: Case sensitivity should be an option of some sort here; 
            #     os.path.normpath might give the prefered case for a filename.
            if requestpath.upper() == tmp_mapdirprefix.upper() or requestpath.upper().startswith(tmp_mapdirprefix.upper() + "/"):
                mapdirprefix = tmp_mapdirprefix   
                break
        else:
            # leaving it to caller function to raise exception - different exception
            # applicable for resolving base or destination urls.
            return (None, None, None, None)

        resourceAL = resALreg['*'] # default set up mainappwrapper.py
        if mapdirprefix in resALcfg:
            if resALcfg[mapdirprefix] in resALreg:
                resourceAL = resALreg[resALcfg[mapdirprefix]]

        
        # no security risk here - the relativepath (part of the URL) is canonized using
        # normpath, and then the share directory name is added. So it is not possible to 
        # use ..s to peruse out of the share directory.
        relativepath = requestpath[len(mapdirprefix):]
        localheadpath = mapcfg[mapdirprefix]
        
        if relativepath.strip("/") == "":
            return (mapdirprefix, localheadpath, mapdirprefix + "/", resourceAL) 
         
        mappedpath = resourceAL.resolvePath(localheadpath, relativepath.strip("/").split("/"))  
        displaypathlist = resourceAL.breakPath(localheadpath, mappedpath)
   
        displaypath = mapdirprefix + "/" + "/".join(displaypathlist)
  
        if resourceAL.isCollection(mappedpath): 
            displaypath = displaypath + "/"

        return (mapdirprefix, mappedpath, displaypath, resourceAL)    

    
    def printConfigErrorMessage(self):        
        message = """\
<html><head><title>Welcome to PyFileServer</title></head>
<body>
<h1>Welcome to PyFileServer</h1>
<p>Thank you for using <a href="http://pyfilesync.berlios.de/">PyFileServer</a> .If you are seeing this message, you have either not specified any realm/mappings to be shared or PyFileServer is having difficulties reading your configuration file. Please check that you have specified a valid configuration file.</p>
</body>        
</html>        
        """
        start_response('200 OK', [('Cache-Control','no-cache'), ('Content-Type', 'text/html'), ('Date',httpdatehelper.getstrftime())])
        return [message]          
    
