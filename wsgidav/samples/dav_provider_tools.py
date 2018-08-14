# -*- coding: utf-8 -*-
# (c) 2009-2018 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Tools that make it easier to implement custom WsgiDAV providers.
"""
import os
import stat

from wsgidav import compat, util
from wsgidav.dav_provider import DAVCollection, DAVNonCollection

__docformat__ = "reStructuredText en"

_logger = util.get_module_logger(__name__)

# ============================================================================
# VirtualCollection
# ============================================================================


class VirtualCollection(DAVCollection):
    """Abstract base class for collections that contain a list of static members.

    Member names are passed to the constructor.
    get_member() is implemented by calling self.provider.get_resource_inst()
    """

    def __init__(self, path, environ, displayInfo, memberNameList):
        DAVCollection.__init__(self, path, environ)
        if compat.is_basestring(displayInfo):
            displayInfo = {"type": displayInfo}
        assert type(displayInfo) is dict
        assert type(memberNameList) is list
        self.displayInfo = displayInfo
        self.memberNameList = memberNameList

    def get_display_info(self):
        return self.displayInfo

    def get_member_names(self):
        return self.memberNameList

    def prevent_locking(self):
        """Return True, since we don't want to lock virtual collections."""
        return True

    def get_member(self, name):
        # raise NotImplementedError
        return self.provider.get_resource_inst(
            util.join_uri(self.path, name), self.environ
        )


# ============================================================================
# _VirtualNonCollection classes
# ============================================================================
class _VirtualNonCollection(DAVNonCollection):
    """Abstract base class for all non-collection resources."""

    def __init__(self, path, environ):
        DAVNonCollection.__init__(self, path, False, environ)

    def get_content_length(self):
        return None

    def get_content_type(self):
        return None

    def get_creation_date(self):
        return None

    def get_display_name(self):
        return self.name

    def get_display_info(self):
        raise NotImplementedError

    def get_etag(self):
        return None

    def get_last_modified(self):
        return None

    def support_ranges(self):
        return False


#    def handle_delete(self):
#        raise DAVError(HTTP_FORBIDDEN)
#    def handle_move(self, destPath):
#        raise DAVError(HTTP_FORBIDDEN)
#    def handle_copy(self, destPath, depthInfinity):
#        raise DAVError(HTTP_FORBIDDEN)


# ============================================================================
# VirtualTextResource
# ============================================================================
class VirtualTextResource(_VirtualNonCollection):
    """A virtual file, containing a string."""

    def __init__(self, path, environ, content, displayName=None, displayType=None):
        _VirtualNonCollection.__init__(self, path, environ)
        self.content = content
        self.displayName = displayName
        self.displayType = displayType

    def get_content_length(self):
        return len(self.get_content().read())

    def get_content_type(self):
        if self.name.endswith(".txt"):
            return "text/plain"
        return "text/html"

    def get_display_name(self):
        return self.displayName or self.name

    def get_display_info(self):
        return {"type": "Virtual info file"}

    def prevent_locking(self):
        return True

    #    def get_ref_url(self):
    #        refPath = "/by_key/%s/%s" % (self._data["key"], self.name)
    #        return compat.quote(self.provider.sharePath + refPath)

    def get_content(self):
        return compat.StringIO(self.content)


# ============================================================================
# FileResource
# ============================================================================
class FileResource(_VirtualNonCollection):
    """Represents an existing file."""

    BUFFER_SIZE = 8192

    def __init__(self, path, environ, filePath):
        if not os.path.exists(filePath):
            _logger.error("FileResource({!r}) does not exist.".format(filePath))
        _VirtualNonCollection.__init__(self, path, environ)
        self.filePath = filePath

    def get_content_length(self):
        statresults = os.stat(self.filePath)
        return statresults[stat.ST_SIZE]

    def get_content_type(self):
        if not os.path.isfile(self.filePath):
            return "text/html"
        #        (mimetype, _mimeencoding) = mimetypes.guess_type(self.filePath)
        #        if not mimetype:
        #            mimetype = "application/octet-stream"
        #        return mimetype
        return util.guess_mime_type(self.filePath)

    def get_creation_date(self):
        statresults = os.stat(self.filePath)
        return statresults[stat.ST_CTIME]

    def get_display_info(self):
        return {"type": "File"}

    def get_last_modified(self):
        statresults = os.stat(self.filePath)
        return statresults[stat.ST_MTIME]

    #    def get_ref_url(self):
    #        refPath = "/by_key/%s/%s" % (self._data["key"], os.path.basename(self.filePath))
    #        return compat.quote(self.provider.sharePath + refPath)

    def get_content(self):
        # mime = self.get_content_type()
        # GC issue 57: always store as binary
        # if mime.startswith("text"):
        #     return open(self.filePath, "r", FileResource.BUFFER_SIZE)
        return open(self.filePath, "rb", FileResource.BUFFER_SIZE)


# ============================================================================
# Resolvers
# ============================================================================
class DAVResolver(object):
    """Return a DAVResource object for a path (None, if not found)."""

    def __init__(self, parentResolver, name):
        self.parentResolver = parentResolver
        self.name = name

    def resolve(self, scriptName, pathInfo, environ):
        raise NotImplementedError
