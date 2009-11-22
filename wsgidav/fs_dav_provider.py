"""
fs_dav_provider
===============

:Author: Ho Chun Wei, fuzzybr80(at)gmail.com (author of original PyFileServer)
:Author: Martin Wendt, moogle(at)wwwendt.de 
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

__docformat__ = "reStructuredText"


import util
import os
import mimetypes
import shutil
import stat

from dav_error import DAVError, HTTP_FORBIDDEN
from dav_provider import DAVProvider, DAVResource


_logger = util.getModuleLogger(__name__)

BUFFER_SIZE = 8192

    
#===============================================================================
# FileResource
#===============================================================================
class FileResource(DAVResource):
    """Represents a single existing DAV resource instance.


    See also DAVResource and ReadOnlyFilesystemProvider.
    """
    def __init__(self, provider, path, typeList):
        assert path=="" or path.startswith("/")
        self.provider = provider
        self.path = path
        self.typeList = typeList
        
        self._filePath = self._locToFilePath(path)

        # TODO: recalc self.path from <self._filePath>, to fix correct file system case
        #       On windows this would lead to correct URLs
        
        if not os.path.exists(self._filePath):
            raise RuntimeError("Path must exist: %s" % path)
        
        statresults = os.stat(self._filePath)
        isCollection = os.path.isdir(self._filePath)
        # The file system may have non-files (e.g. links)
        isFile = os.path.isfile(self._filePath)
#        name = util.getUriName(self.getPreferredPath(path))
#        name = util.getUriName(path)
        name = os.path.basename(self._filePath)
        
#       TODO: this line in: browser doesn't work, but DAVEx does
#        name = name.decode("utf8")
#        util.log("getInfoDict(%s): name='%s'" % (path, name))

        displayType = "File"
        if isCollection:
            displayType = "Directory"
        elif not isFile:
            displayType = "Unknown"
        
        self._dict = {
            "contentLength": None,
            "contentType": "text/html", # TODO: should be None?
            "name": name,
            "displayName": name,
            "displayType": displayType,
            "modified": statresults[stat.ST_MTIME],
            "created": statresults[stat.ST_CTIME],
            "etag": util.getETag(self._filePath), # TODO: should be resource-only?
            "isCollection": isCollection, 
            }
        # Some resource-only infos: 
        if isFile:
            # Guess MIME type (if requested)
            if typeList is None or "contentType" in typeList:
                (mimetype, _mimeencoding) = mimetypes.guess_type(path) # TODO: use strict=False?  
                if not mimetype:
                    mimetype = "application/octet-stream" 
                dict["contentType"] = mimetype

            dict["contentLength"] = statresults[stat.ST_SIZE]
        return

    
    def __repr__(self):
        return "%s(%s): %s" % (self.__class__.__name__, self.path, self._dict)

    def contentLength(self):
        return self._dict.get("contentLength")
    def contentType(self):
        return self._dict.get("contentType")
    def created(self):
        return self._dict.get("created")
    def displayName(self):
        return self._dict.get("displayName")
    def displayType(self):
        return self._dict.get("displayType")
    def etag(self):
        return self._dict.get("etag")
    def isCollection(self):
        return self._dict["isCollection"]
    def modified(self):
        return self._dict.get("modified")
    def name(self):
        return self._dict.get("name")
    def supportRanges(self):
        return True
    
    
    def getMemberNames(self):
        """Return list of (direct) collection member names (UTF-8 byte strings).
        
        Every provider must override this method.
        """
        # TODO: iso_8859_1 doesn't know EURO sign
        # On Windows NT/2k/XP and Unix, if path is a Unicode object, the result 
        # will be a list of Unicode objects. 
        # Undecodable filenames will still be returned as string objects
        
        # If we don't request unicode, for example Vista may return a '?' 
        # instead of a special character. The name would then be unusable to
        # build a URL that references this resource.
        
#        fp = unicode(fp)
        nameList = []
        # Note: self._filePath is unicode, so listdir returns unicode also
        for name in os.listdir(self._filePath):
#            print "%r" % name
            assert isinstance(name, unicode)
            name = name.encode("utf8")
#            print "-> %r" % name
            nameList.append(name)
        return nameList


    # --- Properties -----------------------------------------------------------
     
    # --- Read / write ---------------------------------------------------------
    
    def createEmptyResource(self, name):
        """Create an empty (length-0) resource.
        
        This default implementation simply raises HTTP_FORBIDDEN.
        
        The caller must make sure that <path> does not yet exist, and the parent
        is not locked.
        This method MUST be implemented by all providers that support locking
        and write access."""
        assert self.isCollection()
        raise DAVError(HTTP_FORBIDDEN)               
    

    def createCollection(self, name):
        """Create a new collection as member of self.
        
        This default implementation raises HTTP_FORBIDDEN.
        
        The caller must make sure that <path> does not yet exist, and the parent
        is not locked.
        This method MUST be implemented by all providers that support write 
        access."""
        assert self.isCollection()
        raise DAVError(HTTP_FORBIDDEN)               


    def openResourceForRead(self):
        """Open content as a stream for reading.
         
        This method MUST be implemented by all providers."""
        assert self.isResource()
        fp = self._dict["filePath"]
        mime = self._dict.get("contentType")

        if mime.startswith("text"):
            return file(fp, "r", BUFFER_SIZE)
        else:
            return file(fp, "rb", BUFFER_SIZE)
    

    

    def openResourceForWrite(self, contenttype=None):
        """Open content as a stream for writing.
         
        This method MUST be implemented by all providers that support write 
        access."""
        assert self.isResource()
        raise DAVError(HTTP_FORBIDDEN)               

    
    def delete(self):
        """Remove this resource or collection (non-recursive).
        
        The caller is responsible for checking locking and permissions.
        If this is a collection, he must make sure, all children have already 
        been deleted. 
        Afterwards, he must take care of removing locks and properties.
         
        This method MUST be implemented by all providers that support write 
        access."""
        raise DAVError(HTTP_FORBIDDEN)               

    
#    def remove(self):
#        """Remove the resource and associated locks and properties.
#        
#        This default implementation calls self.deleteResource(path), followed by 
#        .removeAllProperties(path) and .removeAllLocks(path).
#        Errors are raised on failure. 
#
#        This function should NOT be implemented in a recursive way.
#        Instead, the caller is responsible to call remove() for all child 
#        resources before.
#        The caller is also responsible for checking of locks and permissions. 
#        """
#        self.deleteResource()
#        self.removeAllProperties()
#        self.removeAllLocks()
#
#
#    def copy(self, destPath):
#        raise DAVError(HTTP_FORBIDDEN)               



#===============================================================================
# ReadOnlyFilesystemProvider
#===============================================================================
class ReadOnlyFilesystemProvider(DAVProvider):

    def __init__(self, rootFolderPath):
        if not rootFolderPath or not os.path.exists(rootFolderPath):
            raise ValueError("Invalid root path: %s" % rootFolderPath)
        super(ReadOnlyFilesystemProvider, self).__init__()
        self.rootFolderPath = os.path.abspath(rootFolderPath)

        
    def __repr__(self):
        return "%s for path '%s'" % (self.__class__.__name__, self.rootFolderPath)


    def _locToFilePath(self, path):
        """Convert resource path to a unicode absolute file path."""
        # TODO: cache results
#        print "_locToFilePath(%s)..." % (path)
        assert self.rootFolderPath is not None
        pathInfoParts = path.strip("/").split("/")
        
        r = os.path.abspath(os.path.join(self.rootFolderPath, *pathInfoParts))
        if not r.startswith(self.rootFolderPath):
            raise RuntimeError("Security exception: tried to access file outside root.")
#        if not isinstance(r, unicode):
#            util.log("_locToFilePath(%s): %r" % (path, r))
#            r = r.decode("utf8")
        r = util.toUnicode(r)
#        print "_locToFilePath(%s): %s" % (path, r)
        return r  

    
    def getResourceInst(self, path, typeList=None):
        """Return info dictionary for path.

        See DAVProvider.getResourceInst()
        """
        fp = self._locToFilePath(path)
        if not os.path.exists(fp):
            return None
        return FileResource(self, path, typeList)

    
    def exists(self, path):
        fp = self._locToFilePath(path)
        return os.path.exists(fp)
    

    def isCollection(self, path):
        fp = self._locToFilePath(path)
        return os.path.isdir(fp)

    


#===============================================================================
# FilesystemProvider
#===============================================================================

class FilesystemProvider(ReadOnlyFilesystemProvider):
    
    def __init__(self, rootFolderPath):
        super(FilesystemProvider, self).__init__(rootFolderPath)


    def createEmptyResource(self, path):
        fp = self._locToFilePath(path)
        f = open(fp, "w")
        f.close()

    
    def createCollection(self, path):
        fp = self._locToFilePath(path)
        os.mkdir(fp)

    
    def deleteCollection(self, path):
        fp = self._locToFilePath(path)
        os.rmdir(fp)


    def openResourceForWrite(self, path, contenttype=None):
        fp = self._locToFilePath(path)
        mode = "wb"
        if contenttype and contenttype.startswith("text"):
            mode = "w"
        _logger.debug("openResourceForWrite: %s, %s" % (fp, mode))
        return file(fp, mode, BUFFER_SIZE)

    
    def deleteResource(self, path):
        fp = self._locToFilePath(path)
        os.unlink(fp)

    
    def copyResource(self, path, destrespath):
        fpSrc = self._locToFilePath(path)
        fpDest = self._locToFilePath(destrespath)
        shutil.copy2(fpSrc, fpDest)

    
#    def setLivePropertyValue(self, path, name, value, dryRun=False):
#        # {DAV:} live properties are mostly read-only.
#        # Especially supportedlock and lockdiscovery MUST NOT be set here
#        # TODO: RFC 3253 states that {DAV:}displayname 'SHOULD NOT be protected' 
#        # so we could implement {DAV:}displayname as RW, if propMan is available
#        # Maybe in a 'create-on-write' way
#        raise DAVError(HTTP_FORBIDDEN,  # TODO: Chun used HTTP_CONFLICT 
#                       preconditionCode=PRECONDITION_CODE_ProtectedProperty)  
