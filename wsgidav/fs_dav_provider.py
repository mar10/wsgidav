# (c) 2009 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Author of original PyFileServer: Ho Chun Wei, fuzzybr80(at)gmail.com
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Implementation of a DAV provider that serves resource from a file system.
 
ReadOnlyFilesystemProvider implements a DAV resource provider that publishes 
a file system for read-only access.
Write attempts will raise HTTP_FORBIDDEN.

FilesystemProvider inherits from ReadOnlyFilesystemProvider and implements the
missing write access functionality. 

See `Developers info`_ for more information about the WsgiDAV architecture.

.. _`Developers info`: http://docs.wsgidav.googlecode.com/hg/html/develop.html  
"""
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN
from wsgidav.dav_provider import DAVProvider, DAVResource

import util
import os
import mimetypes
import shutil
import stat


__docformat__ = "reStructuredText"

_logger = util.getModuleLogger(__name__)

BUFFER_SIZE = 8192

    
#===============================================================================
# FileResource
#===============================================================================
class FileResource(DAVResource):
    """Represents a single existing DAV resource instance.

    See also DAVResource and FilesystemProvider.
    """
    def __init__(self, provider, path, isCollection, environ, filePath):
        super(FileResource, self).__init__(provider, path, isCollection, environ)
        self._filePath = filePath
        self._dict = None
        # Setting the name from the file path should fix the case on Windows
        self.name = os.path.basename(self._filePath)
        self.name = self.name.encode("utf8")
        


    def _init(self):
        """Read resource information into self._dict, for cached access.
        
        See DAVResource._init()
        """
        # TODO: recalc self.path from <self._filePath>, to fix correct file system case
        #       On windows this would lead to correct URLs
        self.provider._count_getResourceInstInit += 1
        if not os.path.exists(self._filePath):
            raise RuntimeError("Path must exist: %s" % self._filePath)
        
        statresults = os.stat(self._filePath)
        # The file system may have non-files (e.g. links)
        isFile = os.path.isfile(self._filePath)

        displayType = "File"
        if self.isCollection:
            displayType = "Directory"
        elif not isFile:
            displayType = "Unknown"
        
        self._dict = {
            "contentLength": None,
            "contentType": None, 
            "created": statresults[stat.ST_CTIME],
            "displayType": displayType,
            "etag": util.getETag(self._filePath), # TODO: should be resource-only?
            "modified": statresults[stat.ST_MTIME],
            }
        # Some resource-only infos: 
        if isFile:
            self._dict["contentLength"] = statresults[stat.ST_SIZE]
        
            (mimetype, _mimeencoding) = mimetypes.guess_type(self.path)  
            if not mimetype:
                mimetype = "application/octet-stream" 
            self._dict["contentType"] = mimetype

        return

    
    def _getInfo(self, info):
        if self._dict is None:
            self._init()
        return self._dict.get(info)   

    # Getter methods for standard live properties     
    def getContentLanguage(self):
        return None
    def getContentLength(self):
        return self._getInfo("contentLength")
    def getContentType(self):
        return self._getInfo("contentType")
    def getCreationDate(self):
        return self._getInfo("created")
    def getDisplayName(self):
        return self.name
    def displayType(self):
        return self._getInfo("displayType")
    def getEtag(self):
        return self._getInfo("etag")
    def getLastModified(self):
        return self._getInfo("modified")

    def supportRanges(self):
        return True
    
    def getMemberNames(self):
        """Return list of (direct) collection member names (UTF-8 byte strings).
        
        See DAVResource.getMemberNames()
        """
        # On Windows NT/2k/XP and Unix, if path is a Unicode object, the result 
        # will be a list of Unicode objects. 
        # Undecodable filenames will still be returned as string objects    
        # If we don't request unicode, for example Vista may return a '?' 
        # instead of a special character. The name would then be unusable to
        # build a distinct URL that references this resource.

        nameList = []
        # self._filePath is unicode, so os.listdir returns unicode as well
        assert isinstance(self._filePath, unicode) 
        for name in os.listdir(self._filePath):
            assert isinstance(name, unicode)
            # Skip non files (links and mount points)
            fp = os.path.join(self._filePath, name)
            if not os.path.isdir(fp) and not os.path.isfile(fp):
                _logger.debug("Skipping non-file %s" % fp)
                continue
            name = name.encode("utf8")
            nameList.append(name)
        return nameList


    # --- Properties -----------------------------------------------------------
    # TODO: RFC 4918 states that {DAV:}displayname 'SHOULD NOT be protected' 
    # so we could implement {DAV:}displayname as RW, if propMan is available
    # Maybe in a 'create-on-write' way.   
    # http://www.webdav.org/specs/rfc4918.html#rfc.section.15.2     
#    def setPropertyValue(self, propname, value, dryRun=False):
#        """Set a property value or remove a property.
#        
#        See DAVResource.setPropertyValue(). 
#        """
#        raise DAVError(HTTP_FORBIDDEN) 


     
    # --- Read / write ---------------------------------------------------------
    
    def createEmptyResource(self, name):
        """Create an empty (length-0) resource.
        
        See DAVResource.createEmptyResource()
        """
        assert self.isCollection
        assert not "/" in name
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)               
        path = util.joinUri(self.path, name) 
        fp = self.provider._locToFilePath(path)
        f = open(fp, "w")
        f.close()
        return self.provider.getResourceInst(path, self.environ)
    

    def createCollection(self, name):
        """Create a new collection as member of self.
        
        See DAVResource.createCollection()
        """
        assert self.isCollection
        assert not "/" in name
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)               
        path = util.joinUri(self.path, name) 
        fp = self.provider._locToFilePath(path)
        os.mkdir(fp)


    def getContent(self):
        """Open content as a stream for reading.
         
        See DAVResource.getContent()
        """
        assert not self.isCollection
        # issue 28: if we open in text mode, \r\n is converted to one byte.
        # So the file size reported by Windows differs from len(..), thus
        # content-length will be wrong. 
#        mime = self.getContentType()
#        if mime.startswith("text"):
#            return file(self._filePath, "r", BUFFER_SIZE)
        return file(self._filePath, "rb", BUFFER_SIZE)
   

    def beginWrite(self, contentType=None):
        """Open content as a stream for writing.
         
        See DAVResource.beginWrite()
        """
        assert not self.isCollection
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)               
        mode = "wb"
        if contentType and contentType.startswith("text"):
            mode = "w"
        _logger.debug("beginWrite: %s, %s" % (self._filePath, mode))
        return file(self._filePath, mode, BUFFER_SIZE)

    
    def delete(self):
        """Remove this resource or collection (recursive).
        
        See DAVResource.delete()
        """
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)               
        if self.isCollection:
#            os.rmdir(self._filePath)
            shutil.rmtree(self._filePath, ignore_errors=False)
        else:
            os.unlink(self._filePath)
        self.removeAllProperties(True)
        self.removeAllLocks(True)
            

    def copyMoveSingle(self, destPath, isMove):
        """See DAVResource.copyMoveSingle() """
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)               
        fpDest = self.provider._locToFilePath(destPath)
        assert not util.isEqualOrChildUri(self.path, destPath)
        if self.isCollection:
            # Create destination collection, if not exists
            if not os.path.exists(fpDest):
                os.mkdir(fpDest)
            try:
                # may raise: [Error 5] Permission denied: u'C:\\temp\\litmus\\ccdest'
                shutil.copystat(self._filePath, fpDest)
            except Exception, e:
                _logger.debug("Could not copy folder stats: %s" % e)
        else:
            # Copy file (overwrite, if exists)
            shutil.copy2(self._filePath, fpDest)
        # (Live properties are copied by copy2 or copystat)
        # Copy dead properties
        propMan = self.provider.propManager
        if propMan:
            destRes = self.provider.getResourceInst(destPath, self.environ)
            if isMove:
                propMan.moveProperties(self.getRefUrl(), destRes.getRefUrl(), 
                                       withChildren=False)
            else:
                propMan.copyProperties(self.getRefUrl(), destRes.getRefUrl())
               

    def supportRecursiveMove(self, destPath):
        """Return True, if moveRecursive() is available (see comments there)."""
        return True

    
    def moveRecursive(self, destPath):
        """See DAVResource.moveRecursive() """
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)               
        fpDest = self.provider._locToFilePath(destPath)
        assert not util.isEqualOrChildUri(self.path, destPath)
        assert not os.path.exists(fpDest)
        _logger.debug("moveRecursive(%s, %s)" % (self._filePath, fpDest))
        shutil.move(self._filePath, fpDest)
        # (Live properties are copied by copy2 or copystat)
        # Move dead properties
        if self.provider.propManager:
            destRes = self.provider.getResourceInst(destPath, self.environ)
            self.provider.propManager.moveProperties(self.getRefUrl(), destRes.getRefUrl(), 
                                                     withChildren=True)
               


    
#===============================================================================
# FilesystemProvider
#===============================================================================
class FilesystemProvider(DAVProvider):

    def __init__(self, rootFolderPath, readonly=False):
        if not rootFolderPath or not os.path.exists(rootFolderPath):
            raise ValueError("Invalid root path: %s" % rootFolderPath)
        super(FilesystemProvider, self).__init__()
        self.rootFolderPath = os.path.abspath(rootFolderPath)
        self.readonly = readonly

        
    def __repr__(self):
        rw = "Read-Write"
        if self.readonly:
            rw = "Read-Only"
        return "%s for path '%s' (%s)" % (self.__class__.__name__, 
                                          self.rootFolderPath, rw)


    def _locToFilePath(self, path):
        """Convert resource path to a unicode absolute file path."""
        assert self.rootFolderPath is not None
        pathInfoParts = path.strip("/").split("/")
        
        r = os.path.abspath(os.path.join(self.rootFolderPath, *pathInfoParts))
        if not r.startswith(self.rootFolderPath):
            raise RuntimeError("Security exception: tried to access file outside root.")
        r = util.toUnicode(r)
#        print "_locToFilePath(%s): %s" % (path, r)
        return r  

    
    def getResourceInst(self, path, environ):
        """Return info dictionary for path.

        See DAVProvider.getResourceInst()
        """
        self._count_getResourceInst += 1
        fp = self._locToFilePath(path)
        if not os.path.exists(fp):
            return None
        return FileResource(self, path, os.path.isdir(fp), environ, fp)
