"""
fs_dav_provider
===============

:Author: Martin Wendt, moogle(at)wwwendt.de 
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com (author of original PyFileServer)
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

Implementation of a DAV provider that serves resource from a file system.
 
ReadOnlyFilesystemProvider implements a DAV resource provider that publishes 
a file system for read-only access.
Write attempts will raise HTTP_FORBIDDEN.

FilesystemProvider inherits from ReadOnlyFilesystemProvider and implements the
missing write access functionality. 

See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
"""
#from urllib2 import url
#import urllib2

__docformat__ = "reStructuredText"


import util
import os
import mimetypes
import shutil
import stat

#from dav_error import DAVError, HTTP_FORBIDDEN
from dav_provider import DAVProvider, DAVResource


_logger = util.getModuleLogger(__name__)

BUFFER_SIZE = 8192

    
#===============================================================================
# FileResource
#===============================================================================
class FileResource(DAVResource):
    """Represents a single existing DAV resource instance.

    See also DAVResource and FilesystemProvider.
    """
    def __init__(self, provider, path, isCollection, filePath):
        super(FileResource, self).__init__(provider, path, isCollection)
        self._filePath = filePath
        # Setting the name from the file path should fix the case on Windows
        self._name = os.path.basename(self._filePath)
        self._name = self._name.encode("utf8")
        


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
        if self.isCollection():
            displayType = "Directory"
        elif not isFile:
            displayType = "Unknown"
        
        self._dict = {
            "contentLength": None, # TODO: remove?
            "contentType": "text/html", # TODO: should be None?
            "created": statresults[stat.ST_CTIME],
            "displayName": self._name,
            "displayType": displayType,
            "etag": util.getETag(self._filePath), # TODO: should be resource-only?
#            "isCollection": self._isCollection, 
            "modified": statresults[stat.ST_MTIME],
#            "name": name,
            }
        # Some resource-only infos: 
        if isFile:
            (mimetype, _mimeencoding) = mimetypes.guess_type(self.path)  
            if not mimetype:
                mimetype = "application/octet-stream" 
            self._dict["contentType"] = mimetype

            self._dict["contentLength"] = statresults[stat.ST_SIZE]
            self._dict["supportRanges"] = True
        return

    
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
     
    # --- Read / write ---------------------------------------------------------
    
    def createEmptyResource(self, name):
        """Create an empty (length-0) resource.
        
        See DAVResource.createEmptyResource()
        """
        assert self.isCollection()
        assert not "/" in name
#        raise DAVError(HTTP_FORBIDDEN)               
        path = util.joinUri(self.path, name) 
        fp = self.provider._locToFilePath(path)
        f = open(fp, "w")
        f.close()
        return self.provider.getResourceInst(path)
    

    def createCollection(self, name):
        """Create a new collection as member of self.
        
        See DAVResource.createCollection()
        """
        assert self.isCollection()
        assert not "/" in name
#        raise DAVError(HTTP_FORBIDDEN)               
        path = util.joinUri(self.path, name) 
        fp = self.provider._locToFilePath(path)
        os.mkdir(fp)


    def getContent(self):
        """Open content as a stream for reading.
         
        See DAVResource.getContent()
        """
        assert not self.isCollection()
        mime = self.contentType()
        if mime.startswith("text"):
            return file(self._filePath, "r", BUFFER_SIZE)
        return file(self._filePath, "rb", BUFFER_SIZE)
   

    def openResourceForWrite(self, contentType=None):
        """Open content as a stream for writing.
         
        This method MUST be implemented by all providers that support write 
        access."""
        assert not self.isCollection()
#        raise DAVError(HTTP_FORBIDDEN)               
        mode = "wb"
        if contentType and contentType.startswith("text"):
            mode = "w"
        _logger.debug("openResourceForWrite: %s, %s" % (self._filePath, mode))
        return file(self._filePath, mode, BUFFER_SIZE)

    
    def delete(self):
        """Remove this resource or collection (recursive).
        
        See DAVResource.delete()
        """
#        raise DAVError(HTTP_FORBIDDEN)               
        if self.isCollection():
#            os.rmdir(self._filePath)
            shutil.rmtree(self._filePath, ignore_errors=False)
        else:
            os.unlink(self._filePath)
        self.removeAllProperties(True)
        self.removeAllLocks(True)
            

    def copy(self, destPath):
        """See DAVResource.copy() """
        fpDest = self.provider._locToFilePath(destPath)
        assert not util.isEqualOrChildUri(self.path, destPath)
        if self.isCollection():
#            assert not os.path.exists(fpDest)
            if not os.path.exists(fpDest):
                os.mkdir(fpDest)
            try:
                # may raise: [Error 5] Zugriff verweigert: u'C:\\temp\\litmus\\ccdest'
                shutil.copystat(self._filePath, fpDest)
            except Exception, e:
                _logger.debug("Could not copy folder stats: %s" % e)
        else:
            shutil.copy2(self._filePath, fpDest)
        # (Live properties are copied by copy2 or copystat)
        # Copy dead properties
        if self.provider.propManager:
            destRes = self.provider.getResourceInst(destPath)
            self.provider.propManager.copyProperties(self.getRefUrl(), destRes.getRefUrl())
               

    def move(self, destPath):
        """See DAVResource.move() """
#        raise DAVError(HTTP_FORBIDDEN)
        fpDest = self.provider._locToFilePath(destPath)
        assert not util.isEqualOrChildUri(self.path, destPath)
        assert not os.path.exists(fpDest)
        _logger.debug("move(%s, %s)" % (self._filePath, fpDest))
        print("move(%s, %s)" % (self._filePath, fpDest))
        shutil.move(self._filePath, fpDest)
               


    
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
        return "%s for path '%s'" % (self.__class__.__name__, self.rootFolderPath)


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

    
    def getResourceInst(self, path):
        """Return info dictionary for path.

        See DAVProvider.getResourceInst()
        """
        self._count_getResourceInst += 1
        fp = self._locToFilePath(path)
        if not os.path.exists(fp):
            return None
        return FileResource(self, path, os.path.isdir(fp), fp)

    


#===============================================================================
# FilesystemProvider
#===============================================================================

#class FilesystemProvider(ReadOnlyFilesystemProvider):
#    
#    def __init__(self, rootFolderPath):
#        super(FilesystemProvider, self).__init__(rootFolderPath)


#    def createEmptyResource(self, path):
#        fp = self._locToFilePath(path)
#        f = open(fp, "w")
#        f.close()

    
#    def createCollection(self, path):
#        fp = self._locToFilePath(path)
#        os.mkdir(fp)

    
#    def deleteCollection(self, path):
#        fp = self._locToFilePath(path)
#        os.rmdir(fp)


#    def openResourceForWrite(self, path, contentType=None):
#        fp = self._locToFilePath(path)
#        mode = "wb"
#        if contenttype and contenttype.startswith("text"):
#            mode = "w"
#        _logger.debug("openResourceForWrite: %s, %s" % (fp, mode))
#        return file(fp, mode, BUFFER_SIZE)

    
#    def deleteResource(self, path):
#        fp = self._locToFilePath(path)
#        os.unlink(fp)

    
#    def copyResource(self, path, destrespath):
#        fpSrc = self._locToFilePath(path)
#        fpDest = self._locToFilePath(destrespath)
#        shutil.copy2(fpSrc, fpDest)

    
#    def setLivePropertyValue(self, path, name, value, dryRun=False):
#        # {DAV:} live properties are mostly read-only.
#        # Especially supportedlock and lockdiscovery MUST NOT be set here
#        # TODO: RFC 3253 states that {DAV:}displayname 'SHOULD NOT be protected' 
#        # so we could implement {DAV:}displayname as RW, if propMan is available
#        # Maybe in a 'create-on-write' way
#        raise DAVError(HTTP_FORBIDDEN,  # TODO: Chun used HTTP_CONFLICT 
#                       preconditionCode=PRECONDITION_CODE_ProtectedProperty)  
