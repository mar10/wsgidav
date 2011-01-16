# -*- coding: iso-8859-1 -*-
# (c) 2009-2011 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""

"""
import stat
import os
import mimetypes
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO #@UnusedImport
from wsgidav.dav_provider import DAVCollection, DAVNonCollection
from wsgidav import util

__docformat__ = "reStructuredText en"

_logger = util.getModuleLogger(__name__)

#===============================================================================
# VirtualCollection
#===============================================================================

class VirtualCollection(DAVCollection):
    """Abstract base class for collections that contain a list of static members.
    
    Member names are passed to the constructor.
    getMember() is implemented by calling self.provider.getResourceInst()
    """
    def __init__(self, path, environ, displayInfo, memberNameList):
        DAVCollection.__init__(self, path, environ)
        if isinstance(displayInfo, basestring):
            displayInfo = { "type": displayInfo }
        assert type(displayInfo) is dict
        assert type(memberNameList) is list
        self.displayInfo = displayInfo
        self.memberNameList = memberNameList
        
    def getDisplayInfo(self):
        return self.displayInfo
    
    def getMemberNames(self):
        return self.memberNameList
    
    def preventLocking(self):
        """Return True, since we don't want to lock virtual collections."""
        return True
    
    def getMember(self, name):
#        raise NotImplementedError()
        return self.provider.getResourceInst(util.joinUri(self.path, name), 
                                             self.environ)



#===============================================================================
# _VirtualNonCollection classes
#===============================================================================
class _VirtualNonCollection(DAVNonCollection):
    """Abstract base class for all non-collection resources."""
    def __init__(self, path, environ):
        DAVNonCollection.__init__(self, path, False, environ)
    def getContentLength(self):
        return None
    def getContentType(self):
        return None
    def getCreationDate(self):
        return None
    def getDisplayName(self):
        return self.name
    def getDisplayInfo(self):
        raise NotImplementedError()
    def getEtag(self):
        return None
    def getLastModified(self):
        return None
    def supportRanges(self):
        return False
#    def handleDelete(self):
#        raise DAVError(HTTP_FORBIDDEN)
#    def handleMove(self, destPath):
#        raise DAVError(HTTP_FORBIDDEN)
#    def handleCopy(self, destPath, depthInfinity):
#        raise DAVError(HTTP_FORBIDDEN)


#===============================================================================
# VirtualTextResource
#===============================================================================
class VirtualTextResource(_VirtualNonCollection):
    """A virtual file, containing a string."""
    def __init__(self, path, environ, content, 
                 displayName=None, displayType=None):
        _VirtualNonCollection.__init__(self, path, environ)
        self.content = content
        self.displayName = displayName
        self.displayType = displayType
    def getContentLength(self):
        return len(self.getContent().read())
    def getContentType(self):
        if self.name.endswith(".txt"):
            return "text/plain"
        return "text/html"
    def getDisplayName(self):
        return self.displayName or self.name
    def getDisplayInfo(self):
        return {"type": "Virtual info file"}
    def preventLocking(self):
        return True
#    def getRefUrl(self):
#        refPath = "/by_key/%s/%s" % (self._data["key"], self.name)
#        return urllib.quote(self.provider.sharePath + refPath)
    def getContent(self):
        return StringIO(self.content)


#===============================================================================
# FileResource
#===============================================================================
class FileResource(_VirtualNonCollection):
    """Represents an existing file."""
    BUFFER_SIZE = 8192
    def __init__(self, path, environ, filePath):
        if not os.path.exists(filePath):
            util.warn("FileResource(%r) does not exist." % filePath)
        _VirtualNonCollection.__init__(self, path, environ)
        self.filePath = filePath
    def getContentLength(self):
        statresults = os.stat(self.filePath)
        return statresults[stat.ST_SIZE]      
    def getContentType(self):
        if not os.path.isfile(self.filePath):
            return "text/html"
        (mimetype, _mimeencoding) = mimetypes.guess_type(self.filePath) 
        if not mimetype:
            mimetype = "application/octet-stream" 
        return mimetype
    def getCreationDate(self):
        statresults = os.stat(self.filePath)
        return statresults[stat.ST_CTIME]      
    def getDisplayInfo(self):
        return {"type": "File"}
    def getLastModified(self):
        statresults = os.stat(self.filePath)
        return statresults[stat.ST_MTIME]      
#    def getRefUrl(self):
#        refPath = "/by_key/%s/%s" % (self._data["key"], os.path.basename(self.filePath))
#        return urllib.quote(self.provider.sharePath + refPath)
    def getContent(self):
        mime = self.getContentType()
        if mime.startswith("text"):
            return file(self.filePath, "r", FileResource.BUFFER_SIZE)
        return file(self.filePath, "rb", FileResource.BUFFER_SIZE)
        
         
#===============================================================================
# Resolvers
#===============================================================================
class DAVResolver(object):
    """Return a DAVResource object for a path (None, if not found)."""
    def __init__(self, parentResolver, name):
        self.parentResolver = parentResolver
        self.name = name
    def resolve(self, scriptName, pathInfo, environ):
        raise NotImplementedError
