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

from dav_provider import DAVProvider

import util
import os
import mimetypes
import shutil
import stat

from dav_error import DAVError, HTTP_FORBIDDEN


_logger = util.getModuleLogger(__name__)

BUFFER_SIZE = 8192

    
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

    
    def getMemberNames(self, path):
        """Return list of (direct) collection member names (UTF-8 byte strings)."""
        fp = self._locToFilePath(path)

        # TODO: iso_8859_1 doesn't know EURO sign
        # On Windows NT/2k/XP and Unix, if path is a Unicode object, the result 
        # will be a list of Unicode objects. 
        # Undecodable filenames will still be returned as string objects
        
        # If we don't request unicode, for example Vista may return a '?' 
        # instead of a special character. The name would then be unusable to
        # build a URL that references this resource.
#        fp = unicode(fp)
        nameList = []
        for name in os.listdir(fp):
#            print "%r" % name
            assert isinstance(name, unicode)
            name = name.encode("utf8")
#            print "-> %r" % name
            nameList.append(name)
        return nameList
        

    def getInfoDict(self, path, typeList=None):
        """Return info dictionary for path.

        See DAVProvider.getInfoDict()
        """
        fp = self._locToFilePath(path)
#        print >>sys.stderr, "getInfoDict(%s)" % (path, )
        
        if not os.path.exists(fp):
            return None
        # Early out,if typeList is [] (i.e. test for resource existence only)
        if not (typeList or typeList is None):
            return {} 
        statresults = os.stat(fp)
        isCollection = os.path.isdir(fp)
        # The file system may have non-files (e.g. links)
        isFile = os.path.isfile(fp)
        name = util.getUriName(self.getPreferredPath(path))
        
#       TODO: this line in: browser doesn't work, but DAVEx does
#        name = name.decode("utf8")
#        util.log("getInfoDict(%s): name='%s'" % (path, name))

        displayType = "File"
        if isCollection:
            displayType = "Directory"
        elif not isFile:
            displayType = "Unknown"
        
        dict = {"contentLength": None,
                "contentType": "text/html", # TODO: should be None?
                "name": name,
                "displayName": name,
                "displayType": displayType,
                "modified": statresults[stat.ST_MTIME],
                "created": statresults[stat.ST_CTIME],
                "etag": util.getETag(fp), # TODO: should be resource-only?
                "supportRanges": False,
                "isCollection": isCollection, 
                }
        # Some resource-only infos: 
        if not isCollection:
            # Guess MIME type (if requested)
            if (typeList is None or "contentType" in typeList) and isFile:
                (mimetype, _mimeencoding) = mimetypes.guess_type(path) # TODO: use strict=False?  
                if not mimetype:
                    mimetype = "application/octet-stream" 
                dict["contentType"] = mimetype
                 
            if isFile:
                dict["contentLength"] = statresults[stat.ST_SIZE]
                dict["supportRanges"] = True

        return dict

    
    def exists(self, path):
        fp = self._locToFilePath(path)
        return os.path.exists(fp)
    

    def isCollection(self, path):
        fp = self._locToFilePath(path)
        return os.path.isdir(fp)


    def isResource(self, path):
        # TODO: does it make sense to treat non-files/non-collections as
        #       existing, but neither isCollection nor isResource?
        #       Maybe we should define existing as 'isCollection or isResource'
        fp = self._locToFilePath(path)
        return os.path.isfile(fp)


    def createEmptyResource(self, path):
        raise DAVError(HTTP_FORBIDDEN)               
    

    def createCollection(self, path):
        raise DAVError(HTTP_FORBIDDEN)               

    
    def deleteCollection(self, path):
        raise DAVError(HTTP_FORBIDDEN)               


    def openResourceForRead(self, path, davres=None):
        fp = self._locToFilePath(path)
        if davres: 
            mime = davres.contentType()
        else:
            mime = self.getInfoDict(path, ["contentType"]).get("contentType")

        if mime.startswith("text"):
            return file(fp, "r", BUFFER_SIZE)
        else:
            return file(fp, "rb", BUFFER_SIZE)
    

    def openResourceForWrite(self, path, contenttype=None):
        raise DAVError(HTTP_FORBIDDEN)               

    
    def deleteResource(self, path):
        raise DAVError(HTTP_FORBIDDEN)               

    
    def copyResource(self, path, destrespath):
        raise DAVError(HTTP_FORBIDDEN)               

    


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
#        if contenttype is None:
#            istext = False
#        else:
#            istext = contenttype.startswith("text")
#        if istext:
#            return file(fp, "w", BUFFER_SIZE)
#        else:
#            return file(fp, "wb", BUFFER_SIZE)
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
