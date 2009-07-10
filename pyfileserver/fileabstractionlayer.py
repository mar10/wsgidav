"""
fileabstractionlayer
====================

:Module: pyfileserver.fileabstractionlayer
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com
:Project: PyFileServer, http://pyfilesync.berlios.de/
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

This module is specific to the PyFileServer application. It provides two 
classes ``FilesystemAbstractionLayer`` and ``ReadOnlyFilesystemAbstractionLayer``.

Abstraction Layers must provide the methods as described in 
abstractionlayerinterface_

.. _abstractionlayerinterface : interfaces/abstractionlayerinterface.py

See extrequestserver.py for more information about resource abstraction layers in 
PyFileServer

"""

__docformat__ = 'reStructuredText'

import os
import sys
import md5
import mimetypes
import shutil
import stat

from processrequesterrorhandler import HTTPRequestException
import processrequesterrorhandler
import httpdatehelper

BUFFER_SIZE = 8192

class FilesystemAbstractionLayer(object):
   
   def getResourceDescriptor(self, respath):
      resdesc = self.getResourceDescription(respath)
      ressize = str(self.getContentLength(respath)) + " B"
      resmod = httpdatehelper.getstrftime(self.getLastModified(respath))
      if os.path.isdir(respath):      
         ressize = ""
      return [resdesc, ressize, resmod]
   
   def getResourceDescription(self, respath):
      if os.path.isdir(respath):
         return "Directory"
      elif os.path.isfile(respath):
         return "File"
      else:
         return "Unknown"

   def getContentType(self, respath):
      if os.path.isfile(respath):
         (mimetype, mimeencoding) = mimetypes.guess_type(respath); 
         if mimetype == '' or mimetype is None:
            mimetype = 'application/octet-stream' 
         return mimetype
      else:
         return "text/html"

   def getLastModified(self, respath):
         statresults = os.stat(respath)
         return statresults[stat.ST_MTIME]      
   
   def getContentLength(self, respath):
      if not os.path.isfile(respath):
         return 0
      else:
         statresults = os.stat(respath)
         return statresults[stat.ST_SIZE]      
   
   def getEntityTag(self, respath):
      if not os.path.isfile(respath):
         return md5.new(respath).hexdigest()   
      if sys.platform == 'win32':
         statresults = os.stat(respath)
         return md5.new(respath).hexdigest() + '-' + str(statresults[stat.ST_MTIME]) + '-' + str(statresults[stat.ST_SIZE])
      else:
         statresults = os.stat(respath)
         return str(statresults[stat.ST_INO]) + '-' + str(statresults[stat.ST_MTIME]) + '-' + str(statresults[stat.ST_SIZE])

   def matchEntityTag(self, respath, entitytag):
      return entitytag == self.getEntityTag(respath)

   def isCollection(self, respath):
      return os.path.isdir(respath)
   
   def isResource(self, respath):
      return os.path.isfile(respath)
   
   def exists(self, respath):
      return os.path.exists(respath)
   
   def createCollection(self, respath):
      os.mkdir(respath)
   
   def deleteCollection(self, respath):
      os.rmdir(respath)

   def supportEntityTag(self, respath):
      return True

   def supportLastModified(self, respath):
      return True
   
   def supportContentLength(self, respath):
      return True
   
   def supportRanges(self, respath):
      return True
   
   def openResourceForRead(self, respath):
      mime = self.getContentType(respath)
      if mime.startswith("text"):
         return file(respath, 'r', BUFFER_SIZE)
      else:
         return file(respath, 'rb', BUFFER_SIZE)
   
   def openResourceForWrite(self, respath, contenttype=None):
      if contenttype is None:
         istext = False
      else:
         istext = contenttype.startswith("text")            
      if istext:
         return file(respath, 'w', BUFFER_SIZE)
      else:
         return file(respath, 'wb', BUFFER_SIZE)
   
   def deleteResource(self, respath):
      os.unlink(respath)
   
   def copyResource(self, respath, destrespath):
      shutil.copy2(respath, destrespath)
   
   def getContainingCollection(self, respath):
      return os.path.dirname(respath)
   
   def getCollectionContents(self, respath):
      return os.listdir(respath)
      
   def joinPath(self, rescollectionpath, resname):
      return os.path.join(rescollectionpath, resname)

   def splitPath(self, respath):
      return os.path.split(respath)

   def writeProperty(self, respath, propertyname, propertyns, propertyvalue):
      raise HTTPRequestException(processrequesterrorhandler.HTTP_CONFLICT)               

   def removeProperty(self, respath, propertyname, propertyns):
      raise HTTPRequestException(processrequesterrorhandler.HTTP_CONFLICT)               

   def getProperty(self, respath, propertyname, propertyns):
      if propertyns == 'DAV:':
         isfile = os.path.isfile(respath)
         if propertyname == 'creationdate':
             statresults = os.stat(respath)
             return httpdatehelper.getstrftime(statresults[stat.ST_CTIME])
         elif propertyname == 'getcontenttype':
             return self.getContentType(respath)
         elif propertyname == 'resourcetype':
            if os.path.isdir(respath):
               return '<D:collection />'            
            else:
               return ''   
         elif propertyname == 'getlastmodified':
            statresults = os.stat(respath)
            return httpdatehelper.getstrftime(statresults[stat.ST_MTIME])
         elif propertyname == 'getcontentlength':
            if isfile:
               statresults = os.stat(respath)
               return str(statresults[stat.ST_SIZE])
            raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_FOUND)               
         elif propertyname == 'getetag':
            return self.getEntityTag(respath)
      raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_FOUND)               
   
   def isPropertySupported(self, respath, propertyname, propertyns):
      supportedliveprops = ['creationdate', 'getcontenttype','resourcetype','getlastmodified', 'getcontentlength', 'getetag']
      if propertyns != "DAV:" or propertyname not in supportedliveprops:
         return False      
      return True
   
   def getSupportedPropertyNames(self, respath):
      appProps = []
      #DAV properties for all resources
      appProps.append( ('DAV:','creationdate') )
      appProps.append( ('DAV:','getcontenttype') )
      appProps.append( ('DAV:','resourcetype') )
      appProps.append( ('DAV:','getlastmodified') )   
      if os.path.isfile(respath):
         appProps.append( ('DAV:','getcontentlength') )
         appProps.append( ('DAV:','getetag') )
      return appProps
   
   def resolvePath(self, resheadpath, urlelementlist):
      relativepath = os.sep.join(urlelementlist)
      if relativepath.endswith(os.sep):
         relativepath = relativepath[:-len(os.sep)] # remove suffix os.sep since it causes error (SyntaxError) with os.path functions
     
      normrelativepath = ''
      if relativepath != '':          # avoid adding of .s
         normrelativepath = os.path.normpath(relativepath)   

      return resheadpath + os.sep + normrelativepath

   def breakPath(self, resheadpath, respath):      
      relativepath = respath[len(resheadpath):].strip(os.sep)
      return relativepath.split(os.sep)


class ReadOnlyFilesystemAbstractionLayer(object):

   def getResourceDescriptor(self, respath):
      resdesc = self.getResourceDescription(respath)
      ressize = str(self.getContentLength(respath)) + " B"
      resmod = httpdatehelper.getstrftime(self.getLastModified(respath))
      if os.path.isdir(respath):      
         ressize = ""
      return [resdesc, ressize, resmod]
   
   def getResourceDescription(self, respath):
      if os.path.isdir(respath):
         return "Directory"
      elif os.path.isfile(respath):
         return "File"
      else:
         return "Unknown"

   def getContentType(self, respath):
      if os.path.isfile(respath):
         (mimetype, mimeencoding) = mimetypes.guess_type(respath); 
         if mimetype == '' or mimetype is None:
            mimetype = 'application/octet-stream' 
         return mimetype
      else:
         return "text/html"

   def getLastModified(self, respath):
         statresults = os.stat(respath)
         return statresults[stat.ST_MTIME]      
   
   def getContentLength(self, respath):
      if not os.path.isfile(respath):
         return 0
      else:
         statresults = os.stat(respath)
         return statresults[stat.ST_SIZE]      
   
   def getEntityTag(self, respath):
      if not os.path.isfile(respath):
         return md5.new(respath).hexdigest()   
      if sys.platform == 'win32':
         statresults = os.stat(respath)
         return md5.new(respath).hexdigest() + '-' + str(statresults[stat.ST_MTIME]) + '-' + str(statresults[stat.ST_SIZE])
      else:
         statresults = os.stat(respath)
         return str(statresults[stat.ST_INO]) + '-' + str(statresults[stat.ST_MTIME]) + '-' + str(statresults[stat.ST_SIZE])

   def matchEntityTag(self, respath, entitytag):
      return entitytag == self.getEntityTag(respath)

   def isCollection(self, respath):
      return os.path.isdir(respath)
   
   def isResource(self, respath):
      return os.path.isfile(respath)
   
   def exists(self, respath):
      return os.path.exists(respath)
   
   def createCollection(self, respath):
      raise HTTPRequestException(processrequesterrorhandler.HTTP_FORBIDDEN)               
   
   def deleteCollection(self, respath):
      raise HTTPRequestException(processrequesterrorhandler.HTTP_FORBIDDEN)               

   def supportEntityTag(self, respath):
      return True

   def supportLastModified(self, respath):
      return True
   
   def supportContentLength(self, respath):
      return True
   
   def supportRanges(self, respath):
      return True
   
   def openResourceForRead(self, respath):
      mime = self.getContentType(respath)
      if mime.startswith("text"):
         return file(respath, 'r', BUFFER_SIZE)
      else:
         return file(respath, 'rb', BUFFER_SIZE)
   
   def openResourceForWrite(self, respath, contenttype=None):
      raise HTTPRequestException(processrequesterrorhandler.HTTP_FORBIDDEN)               
   
   def deleteResource(self, respath):
      raise HTTPRequestException(processrequesterrorhandler.HTTP_FORBIDDEN)               
   
   def copyResource(self, respath, destrespath):
      raise HTTPRequestException(processrequesterrorhandler.HTTP_FORBIDDEN)               
   
   def getContainingCollection(self, respath):
      return os.path.dirname(respath)
   
   def getCollectionContents(self, respath):
      return os.listdir(respath)
      
   def joinPath(self, rescollectionpath, resname):
      return os.path.join(rescollectionpath, resname)

   def splitPath(self, respath):
      return os.path.split(respath)

   def writeProperty(self, respath, propertyname, propertyns, propertyvalue):
      raise HTTPRequestException(processrequesterrorhandler.HTTP_CONFLICT)               

   def removeProperty(self, respath, propertyname, propertyns):
      raise HTTPRequestException(processrequesterrorhandler.HTTP_CONFLICT)               

   def getProperty(self, respath, propertyname, propertyns):
      if propertyns == 'DAV:':
         isfile = os.path.isfile(respath)
         if propertyname == 'creationdate':
             statresults = os.stat(respath)
             return httpdatehelper.getstrftime(statresults[stat.ST_CTIME])
         elif propertyname == 'getcontenttype':
             return self.getContentType(respath)
         elif propertyname == 'resourcetype':
            if os.path.isdir(respath):
               return '<D:collection />'            
            else:
               return ''   
         elif propertyname == 'getlastmodified':
            statresults = os.stat(respath)
            return httpdatehelper.getstrftime(statresults[stat.ST_MTIME])
         elif propertyname == 'getcontentlength':
            if isfile:
               statresults = os.stat(respath)
               return str(statresults[stat.ST_SIZE])
            raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_FOUND)               
         elif propertyname == 'getetag':
            return self.getEntityTag(respath)
      raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_FOUND)               
   
   def isPropertySupported(self, respath, propertyname, propertyns):
      supportedliveprops = ['creationdate', 'getcontenttype','resourcetype','getlastmodified', 'getcontentlength', 'getetag']
      if propertyns != "DAV:" or propertyname not in supportedliveprops:
         return False      
      return True
   
   def getSupportedPropertyNames(self, respath):
      appProps = []
      #DAV properties for all resources
      appProps.append( ('DAV:','creationdate') )
      appProps.append( ('DAV:','getcontenttype') )
      appProps.append( ('DAV:','resourcetype') )
      appProps.append( ('DAV:','getlastmodified') )   
      if os.path.isfile(respath):
         appProps.append( ('DAV:','getcontentlength') )
         appProps.append( ('DAV:','getetag') )
      return appProps
   
   def resolvePath(self, resheadpath, urlelementlist):
      relativepath = os.sep.join(urlelementlist)
      if relativepath.endswith(os.sep):
         relativepath = relativepath[:-len(os.sep)] # remove suffix os.sep since it causes error (SyntaxError) with os.path functions
     
      normrelativepath = ''
      if relativepath != '':          # avoid adding of .s
         normrelativepath = os.path.normpath(relativepath)   

      return resheadpath + os.sep + normrelativepath

   def breakPath(self, resheadpath, respath):      
      relativepath = respath[len(resheadpath):].strip(os.sep)
      return relativepath.split(os.sep)

      