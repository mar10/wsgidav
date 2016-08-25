# (c) 2009-2016 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Implementation of a DAV provider that serves resource from a file system.

ReadOnlyFilesystemProvider implements a DAV resource provider that publishes
a file system for read-only access.
Write attempts will raise HTTP_FORBIDDEN.

FilesystemProvider inherits from ReadOnlyFilesystemProvider and implements the
missing write access functionality.

See `Developers info`_ for more information about the WsgiDAV architecture.

.. _`Developers info`: http://wsgidav.readthedocs.org/en/latest/develop.html
"""
from __future__ import print_function

import os
import shutil
import stat
import sys

from wsgidav import compat
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN
from wsgidav.dav_provider import DAVProvider, DAVCollection, DAVNonCollection
from wsgidav import util


__docformat__ = "reStructuredText"

_logger = util.getModuleLogger(__name__)

BUFFER_SIZE = 8192


#===============================================================================
# FileResource
#===============================================================================
class FileResource(DAVNonCollection):
    """Represents a single existing DAV resource instance.

    See also _DAVResource, DAVNonCollection, and FilesystemProvider.
    """
    def __init__(self, path, environ, filePath):
        super(FileResource, self).__init__(path, environ)
        self._filePath = filePath
        self.filestat = os.stat(self._filePath)
        # Setting the name from the file path should fix the case on Windows
        self.name = os.path.basename(self._filePath)
        self.name = compat.to_native(self.name)

    # Getter methods for standard live properties
    def getContentLength(self):
        return self.filestat[stat.ST_SIZE]
    def getContentType(self):
#        (mimetype, _mimeencoding) = mimetypes.guess_type(self.path)
#        print "mimetype(%s): %r, %r" % (self.path, mimetype, _mimeencoding)
#        if not mimetype:
#            mimetype = "application/octet-stream"
#        print "mimetype(%s): return %r" % (self.path, mimetype)
#        return mimetype
        return util.guessMimeType(self.path)
    def getCreationDate(self):
        return self.filestat[stat.ST_CTIME]
    def getDisplayName(self):
        return self.name
    def getEtag(self):
        return util.getETag(self._filePath)
    def getLastModified(self):
        return self.filestat[stat.ST_MTIME]
    def supportEtag(self):
        return True
    def supportRanges(self):
        return True

    def getContent(self):
        """Open content as a stream for reading.

        See DAVResource.getContent()
        """
        assert not self.isCollection
        # GC issue 28, 57: if we open in text mode, \r\n is converted to one byte.
        # So the file size reported by Windows differs from len(..), thus
        # content-length will be wrong.
        return open(self._filePath, "rb", BUFFER_SIZE)


    def beginWrite(self, contentType=None):
        """Open content as a stream for writing.

        See DAVResource.beginWrite()
        """
        assert not self.isCollection
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)
        _logger.debug("beginWrite: %s, %s" % (self._filePath, "wb"))
        # GC issue 57: always store as binary
        return open(self._filePath, "wb", BUFFER_SIZE)


    def delete(self):
        """Remove this resource or collection (recursive).

        See DAVResource.delete()
        """
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)
        os.unlink(self._filePath)
        self.removeAllProperties(True)
        self.removeAllLocks(True)


    def copyMoveSingle(self, destPath, isMove):
        """See DAVResource.copyMoveSingle() """
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)
        fpDest = self.provider._locToFilePath(destPath, self.environ)
        assert not util.isEqualOrChildUri(self.path, destPath)
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
        fpDest = self.provider._locToFilePath(destPath, self.environ)
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


    def setLastModified(self, destPath, timeStamp, dryRun):
        """Set last modified time for destPath to timeStamp on epoch-format"""
        # Translate time from RFC 1123 to seconds since epoch format
        secs = util.parseTimeString(timeStamp)
        if not dryRun:
            os.utime(self._filePath, (secs, secs))
        return True


#===============================================================================
# FolderResource
#===============================================================================
class FolderResource(DAVCollection):
    """Represents a single existing file system folder DAV resource.

    See also _DAVResource, DAVCollection, and FilesystemProvider.
    """
    def __init__(self, path, environ, filePath):
        super(FolderResource, self).__init__(path, environ)
        self._filePath = filePath
#        self._dict = None
        self.filestat = os.stat(self._filePath)
        # Setting the name from the file path should fix the case on Windows
        self.name = os.path.basename(self._filePath)
        self.name = compat.to_native(self.name)  #.encode("utf8")


    # Getter methods for standard live properties
    def getCreationDate(self):
        return self.filestat[stat.ST_CTIME]
    def getDisplayName(self):
        return self.name
    def getDirectoryInfo(self):
        return None
    def getEtag(self):
        return None
    def getLastModified(self):
        return self.filestat[stat.ST_MTIME]

    def getMemberNames(self):
        """Return list of direct collection member names (utf-8 encoded).

        See DAVCollection.getMemberNames()
        """
        # On Windows NT/2k/XP and Unix, if path is a Unicode object, the result
        # will be a list of Unicode objects.
        # Undecodable filenames will still be returned as string objects
        # If we don't request unicode, for example Vista may return a '?'
        # instead of a special character. The name would then be unusable to
        # build a distinct URL that references this resource.

        nameList = []
        # self._filePath is unicode, so os.listdir returns unicode as well
        assert compat.is_unicode(self._filePath)
        for name in os.listdir(self._filePath):
            if not compat.is_unicode(name):
                name = name.decode(sys.getfilesystemencoding())
            assert compat.is_unicode(name)
            # Skip non files (links and mount points)
            fp = os.path.join(self._filePath, name)
            if not os.path.isdir(fp) and not os.path.isfile(fp):
                _logger.debug("Skipping non-file %r" % fp)
                continue
            # name = name.encode("utf8")
            name = compat.to_native(name)
            nameList.append(name)
        return nameList

    def getMember(self, name):
        """Return direct collection member (DAVResource or derived).

        See DAVCollection.getMember()
        """
        assert compat.is_native(name), "%r" % name
        fp = os.path.join(self._filePath, compat.to_unicode(name))
#        name = name.encode("utf8")
        path = util.joinUri(self.path, name)
        if os.path.isdir(fp):
            res = FolderResource(path, self.environ, fp)
        elif os.path.isfile(fp):
            res = FileResource(path, self.environ, fp)
        else:
            _logger.debug("Skipping non-file %s" % fp)
            res = None
        return res

    # --- Read / write ---------------------------------------------------------

    def createEmptyResource(self, name):
        """Create an empty (length-0) resource.

        See DAVResource.createEmptyResource()
        """
        assert not "/" in name
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)
        path = util.joinUri(self.path, name)
        fp = self.provider._locToFilePath(path, self.environ)
        f = open(fp, "wb")
        f.close()
        return self.provider.getResourceInst(path, self.environ)


    def createCollection(self, name):
        """Create a new collection as member of self.

        See DAVResource.createCollection()
        """
        assert not "/" in name
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)
        path = util.joinUri(self.path, name)
        fp = self.provider._locToFilePath(path, self.environ)
        os.mkdir(fp)


    def delete(self):
        """Remove this resource or collection (recursive).

        See DAVResource.delete()
        """
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)
        shutil.rmtree(self._filePath, ignore_errors=False)
        self.removeAllProperties(True)
        self.removeAllLocks(True)


    def copyMoveSingle(self, destPath, isMove):
        """See DAVResource.copyMoveSingle() """
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)
        fpDest = self.provider._locToFilePath(destPath, self.environ)
        assert not util.isEqualOrChildUri(self.path, destPath)
        # Create destination collection, if not exists
        if not os.path.exists(fpDest):
            os.mkdir(fpDest)
        try:
            # may raise: [Error 5] Permission denied: u'C:\\temp\\litmus\\ccdest'
            shutil.copystat(self._filePath, fpDest)
        except Exception as e:
            _logger.debug("Could not copy folder stats: %s" % e)
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
        fpDest = self.provider._locToFilePath(destPath, self.environ)
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


    def setLastModified(self, destPath, timeStamp, dryRun):
        """Set last modified time for destPath to timeStamp on epoch-format"""
        # Translate time from RFC 1123 to seconds since epoch format
        secs = util.parseTimeString(timeStamp)
        if not dryRun:
            os.utime(self._filePath, (secs, secs))
        return True


#===============================================================================
# FilesystemProvider
#===============================================================================
class FilesystemProvider(DAVProvider):

    def __init__(self, rootFolderPath, readonly=False):
        # Expand leading '~' as user home dir; expand %VAR%, $Var, ..
        rootFolderPath = os.path.expandvars(os.path.expanduser(rootFolderPath))
        rootFolderPath = os.path.abspath(rootFolderPath)
        if not rootFolderPath or not os.path.exists(rootFolderPath):
            raise ValueError("Invalid root path: %s" % rootFolderPath)

        super(FilesystemProvider, self).__init__()

        self.rootFolderPath = rootFolderPath
        self.readonly = readonly


    def __repr__(self):
        rw = "Read-Write"
        if self.readonly:
            rw = "Read-Only"
        return "%s for path '%s' (%s)" % (self.__class__.__name__,
                                          self.rootFolderPath, rw)


    def _locToFilePath(self, path, environ=None):
        """Convert resource path to a unicode absolute file path.
        Optional environ argument may be useful e.g. in relation to per-user
        sub-folder chrooting inside rootFolderPath.
        """
        assert self.rootFolderPath is not None
        assert compat.is_native(path)
        pathInfoParts = path.strip("/").split("/")

        r = os.path.abspath(os.path.join(self.rootFolderPath, *pathInfoParts))
        if not r.startswith(self.rootFolderPath):
            raise RuntimeError("Security exception: tried to access file outside root.")
        r = util.toUnicode(r)
#        print "_locToFilePath(%s, %s): %s" % (path, environ, r)
        return r


    def isReadOnly(self):
        return self.readonly

    def getResourceInst(self, path, environ):
        """Return info dictionary for path.

        See DAVProvider.getResourceInst()
        """
        self._count_getResourceInst += 1
        fp = self._locToFilePath(path, environ)
        if not os.path.exists(fp):
            return None

        if os.path.isdir(fp):
            return FolderResource(path, environ, fp)
        return FileResource(path, environ, fp)
