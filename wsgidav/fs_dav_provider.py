# (c) 2009-2024 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Implementation of a DAV provider that serves resource from a file system.

:class:`~wsgidav.fs_dav_provider.FilesystemProvider` implements a DAV resource
provider that publishes a file system.

If ``readonly=True`` is passed, write attempts will raise HTTP_FORBIDDEN.

This provider creates instances of :class:`~wsgidav.fs_dav_provider.FileResource`
and :class:`~wsgidav.fs_dav_provider.FolderResource` to represent files and
directories respectively.
"""

import os
import shutil
import stat
import sys
from typing import List

from wsgidav import util
from wsgidav.dav_error import HTTP_FORBIDDEN, DAVError
from wsgidav.dav_provider import DAVCollection, DAVNonCollection, DAVProvider

__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)

BUFFER_SIZE = 8192


# ========================================================================
# FileResource
# ========================================================================
class FileResource(DAVNonCollection):
    """Represents a single existing DAV resource instance.

    See also _DAVResource, DAVNonCollection, and FilesystemProvider.
    """

    def __init__(self, path: str, environ: dict, file_path: str):
        super().__init__(path, environ)
        self._file_path: str = file_path
        self.file_stat: os.stat_result = os.stat(self._file_path)
        # Setting the name from the file path should fix the case on Windows
        self.name: str = os.path.basename(self._file_path)
        self.name = util.to_str(self.name)

    # Getter methods for standard live properties
    def get_content_length(self):
        return self.file_stat[stat.ST_SIZE]

    def get_content_type(self):
        return util.guess_mime_type(self.path)

    def get_creation_date(self):
        return self.file_stat[stat.ST_CTIME]

    def get_display_name(self):
        return self.name

    def get_etag(self):
        return util.get_file_etag(self._file_path)

    def get_last_modified(self):
        return self.file_stat[stat.ST_MTIME]

    def is_link(self):
        return os.path.islink(self._file_path)

    def support_etag(self):
        return True

    def support_ranges(self):
        return True

    def get_content(self):
        """Open content as a stream for reading.

        See DAVResource.get_content()
        """
        assert not self.is_collection
        # GC issue 28, 57: if we open in text mode, \r\n is converted to one byte.
        # So the file size reported by Windows differs from len(..), thus
        # content-length will be wrong.
        return open(self._file_path, "rb", BUFFER_SIZE)

    def begin_write(self, *, content_type=None):
        """Open content as a stream for writing.

        See DAVResource.begin_write()
        """
        assert not self.is_collection
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)
        # _logger.debug("begin_write: {}, {}".format(self._file_path, "wb"))
        # GC issue 57: always store as binary
        return open(self._file_path, "wb", BUFFER_SIZE)

    def delete(self):
        """Remove this resource or collection (recursive).

        See DAVResource.delete()
        """
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)
        os.unlink(self._file_path)
        self.remove_all_properties(recursive=True)
        self.remove_all_locks(recursive=True)

    def copy_move_single(self, dest_path, *, is_move):
        """See DAVResource.copy_move_single()"""
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)
        fpDest = self.provider._loc_to_file_path(dest_path, self.environ)
        assert not util.is_equal_or_child_uri(self.path, dest_path)
        # Copy file (overwrite, if exists)
        shutil.copy2(self._file_path, fpDest)
        # (Live properties are copied by copy2 or copystat)
        # Copy dead properties
        propMan = self.provider.prop_manager
        if propMan:
            destRes = self.provider.get_resource_inst(dest_path, self.environ)
            if is_move:
                propMan.move_properties(
                    self.get_ref_url(),
                    destRes.get_ref_url(),
                    with_children=False,
                    environ=self.environ,
                )
            else:
                propMan.copy_properties(
                    self.get_ref_url(), destRes.get_ref_url(), self.environ
                )

    def support_recursive_move(self, dest_path):
        """Return True, if move_recursive() is available (see comments there)."""
        return True

    def move_recursive(self, dest_path):
        """See DAVResource.move_recursive()"""
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)
        fpDest = self.provider._loc_to_file_path(dest_path, self.environ)
        assert not util.is_equal_or_child_uri(self.path, dest_path)
        assert not os.path.exists(fpDest)
        _logger.debug(f"move_recursive({self._file_path}, {fpDest})")
        shutil.move(self._file_path, fpDest)
        # (Live properties are copied by copy2 or copystat)
        # Move dead properties
        if self.provider.prop_manager:
            destRes = self.provider.get_resource_inst(dest_path, self.environ)
            self.provider.prop_manager.move_properties(
                self.get_ref_url(),
                destRes.get_ref_url(),
                with_children=True,
                environ=self.environ,
            )

    def set_last_modified(self, dest_path, time_stamp, *, dry_run):
        """Set last modified time for destPath to timeStamp on epoch-format"""
        # Translate time from RFC 1123 to seconds since epoch format
        secs = util.parse_time_string(time_stamp)
        if not dry_run:
            os.utime(self._file_path, (secs, secs))
        return True


# ========================================================================
# FolderResource
# ========================================================================
class FolderResource(DAVCollection):
    """Represents a single existing file system folder DAV resource.

    See also _DAVResource, DAVCollection, and FilesystemProvider.
    """

    def __init__(self, path: str, environ: dict, file_path):
        super().__init__(path, environ)
        self._file_path: str = file_path
        self.file_stat: os.stat_result = os.stat(self._file_path)
        self.fs_opts = self.provider
        # Setting the name from the file path should fix the case on Windows
        self.name = os.path.basename(self._file_path)
        self.name = util.to_str(self.name)  # .encode("utf8")

    # Getter methods for standard live properties
    def get_creation_date(self):
        return self.file_stat[stat.ST_CTIME]

    def get_display_name(self):
        return self.name

    def get_directory_info(self):
        return None

    def get_etag(self):
        return None

    def get_used_bytes(self):
        return shutil.disk_usage(self._file_path).used

    def get_available_bytes(self):
        return shutil.disk_usage(self._file_path).free

    def get_last_modified(self):
        return self.file_stat[stat.ST_MTIME]

    def is_link(self):
        return os.path.islink(self._file_path)

    def get_member_names(self) -> List[str]:
        """Return list of direct collection member names (utf-8 encoded).

        See DAVCollection.get_member_names()
        """
        # On Windows NT/2k/XP and Unix, if path is a Unicode object, the result
        # will be a list of Unicode objects.
        # Undecodable filenames will still be returned as string objects
        # If we don't request unicode, for example Vista may return a '?'
        # instead of a special character. The name would then be unusable to
        # build a distinct URL that references this resource.

        nameList = []
        # self._file_path is unicode, so os.listdir returns unicode as well
        assert util.is_str(self._file_path)
        # if "temp" in self._file_path:
        #     raise RuntimeError("Oops")
        for name in os.listdir(self._file_path):
            if not util.is_str(name):
                name = name.decode(sys.getfilesystemencoding())
            assert util.is_str(name)
            # Skip non files (links and mount points)
            fp = os.path.join(self._file_path, name)
            # if not self.provider.fs_opts.get("follow_symlinks") and os.path.islink(fp):
            #     _logger.info(f"Skipping symlink {fp!r}")
            #     continue
            if not os.path.isdir(fp) and not os.path.isfile(fp):
                _logger.info(f"Skipping non-file {fp!r}")
                continue
            # name = name.encode("utf8")
            name = util.to_str(name)
            nameList.append(name)
        return nameList

    def get_member(self, name: str) -> FileResource:
        """Return direct collection member (DAVResource or derived).

        See DAVCollection.get_member()
        """
        assert util.is_str(name), f"{name!r}"
        fp = os.path.join(self._file_path, util.to_str(name))
        # name = name.encode("utf8")
        path = util.join_uri(self.path, name)
        res = None
        # if not self.provider.fs_opts.get("follow_symlinks") and os.path.islink(fp):
        #     _logger.info(f"Skipping symlink {path}")
        # elif
        if os.path.isdir(fp):
            res = FolderResource(path, self.environ, fp)
        elif os.path.isfile(fp):
            res = FileResource(path, self.environ, fp)
        else:
            _logger.debug(f"Skipping non-file {path}")
        return res

    # --- Read / write -------------------------------------------------------

    def create_empty_resource(self, name):
        """Create an empty (length-0) resource.

        See DAVResource.create_empty_resource()
        """
        assert "/" not in name
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)
        path = util.join_uri(self.path, name)
        fp = self.provider._loc_to_file_path(path, self.environ)
        f = open(fp, "wb")
        f.close()
        return self.provider.get_resource_inst(path, self.environ)

    def create_collection(self, name):
        """Create a new collection as member of self.

        See DAVResource.create_collection()
        """
        assert "/" not in name
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)
        path = util.join_uri(self.path, name)
        fp = self.provider._loc_to_file_path(path, self.environ)
        os.mkdir(fp)

    def delete(self):
        """Remove this resource or collection (recursive).

        See DAVResource.delete()
        """
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)
        shutil.rmtree(self._file_path, ignore_errors=False)
        self.remove_all_properties(recursive=True)
        self.remove_all_locks(recursive=True)

    def copy_move_single(self, dest_path, *, is_move):
        """See DAVResource.copy_move_single()"""
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)
        fpDest = self.provider._loc_to_file_path(dest_path, self.environ)
        assert not util.is_equal_or_child_uri(self.path, dest_path)
        # Create destination collection, if not exists
        if not os.path.exists(fpDest):
            os.mkdir(fpDest)
        try:
            # may raise: [Error 5] Permission denied:
            # u'C:\\temp\\litmus\\ccdest'
            shutil.copystat(self._file_path, fpDest)
        except Exception:
            _logger.exception(f"Could not copy folder stats: {self._file_path}")
        # (Live properties are copied by copy2 or copystat)
        # Copy dead properties
        propMan = self.provider.prop_manager
        if propMan:
            destRes = self.provider.get_resource_inst(dest_path, self.environ)
            if is_move:
                propMan.move_properties(
                    self.get_ref_url(),
                    destRes.get_ref_url(),
                    with_children=False,
                    environ=self.environ,
                )
            else:
                propMan.copy_properties(
                    self.get_ref_url(), destRes.get_ref_url(), self.environ
                )

    def support_recursive_move(self, dest_path):
        """Return True, if move_recursive() is available (see comments there)."""
        return True

    def move_recursive(self, dest_path):
        """See DAVResource.move_recursive()"""
        if self.provider.readonly:
            raise DAVError(HTTP_FORBIDDEN)
        fpDest = self.provider._loc_to_file_path(dest_path, self.environ)
        assert not util.is_equal_or_child_uri(self.path, dest_path)
        assert not os.path.exists(fpDest)
        _logger.debug(f"move_recursive({self._file_path}, {fpDest})")
        shutil.move(self._file_path, fpDest)
        # (Live properties are copied by copy2 or copystat)
        # Move dead properties
        if self.provider.prop_manager:
            destRes = self.provider.get_resource_inst(dest_path, self.environ)
            self.provider.prop_manager.move_properties(
                self.get_ref_url(),
                destRes.get_ref_url(),
                with_children=True,
                environ=self.environ,
            )

    def set_last_modified(self, dest_path, time_stamp, *, dry_run):
        """Set last modified time for destPath to timeStamp on epoch-format"""
        # Translate time from RFC 1123 to seconds since epoch format
        secs = util.parse_time_string(time_stamp)
        if not dry_run:
            os.utime(self._file_path, (secs, secs))
        return True


# ========================================================================
# FilesystemProvider
# ========================================================================
class FilesystemProvider(DAVProvider):
    """Default implementation of a filesystem DAVProvider.

    Args:
        root_folder (str)
        readonly (bool)
        fs_opts (dict | None): defaults to `config.fs_dav_provider`
        shadow (dict):  @deprecated (Use option `fs_provider.shadow_map` instead)
    """

    def __init__(self, root_folder, *, readonly=False, fs_opts=None):
        # root_folder is typically already resolved relative to config file
        # and has user ~ expanded
        root_folder = os.path.abspath(root_folder)
        if not root_folder or not os.path.exists(root_folder):
            raise ValueError(f"Invalid root path: {root_folder}")

        super().__init__()

        self.root_folder_path = root_folder
        self.readonly = readonly
        if fs_opts is None:
            _logger.warning(f"{self}: no `fs_opts` parameter passed to constructor.")
            fs_opts = {}
        self.fs_opts = fs_opts
        # Get shadow map and convert keys to lower case
        self.shadow_map = self.fs_opts.get("shadow_map") or {}
        if self.shadow_map:
            self.shadow_map = {k.lower(): v for k, v in self.shadow_map.items()}

    def __repr__(self):
        rw = "Read-Only" if self.readonly else "Read-Write"
        return f"{self.__class__.__name__} for path {self.root_folder_path!r} ({rw})"

    def _resolve_shadow_path(self, path: str, environ: dict, file_path):
        """File not found: See if there is a shadow configured."""
        shadow = self.shadow_map.get(path.lower())
        # _logger.info(f"Shadow {path} -> {shadow} {self.shadow}")
        if not shadow:
            return False, file_path

        err = None
        method = environ["REQUEST_METHOD"].upper()
        if method not in ("GET", "HEAD", "OPTIONS"):
            err = f"Shadow {path} -> {shadow}: ignored for method {method!r}."
        elif os.path.exists(file_path):
            err = f"Shadow {path} -> {shadow}: ignored for existing resource {file_path!r}."
        elif not os.path.exists(shadow):
            err = f"Shadow {path} -> {shadow}: does not exist."

        if err:
            _logger.warning(err)
            return False, file_path
        _logger.info(f"Shadow {path} -> {shadow}")
        return True, shadow

    def _loc_to_file_path(self, path: str, environ: dict = None):
        """Convert resource path to a unicode absolute file path.
        Optional environ argument may be useful e.g. in relation to per-user
        sub-folder chrooting inside root_folder_path.
        """
        root_path = self.root_folder_path
        assert root_path is not None
        assert util.is_str(root_path)
        assert util.is_str(path)

        path_parts = path.strip("/").split("/")
        file_path = os.path.abspath(os.path.join(root_path, *path_parts))

        # Try alternative URL if not found (or even override target):
        is_shadow, file_path = self._resolve_shadow_path(path, environ, file_path)

        if not file_path.startswith(root_path) and not is_shadow:
            raise RuntimeError(
                f"Security exception: tried to access file outside root: {file_path}"
            )

        # Convert to unicode
        file_path = util.to_unicode_safe(file_path)
        return file_path

    def get_resource_inst(self, path: str, environ: dict) -> FileResource:
        """Return info dictionary for path.

        See DAVProvider.get_resource_inst()
        """
        self._count_get_resource_inst += 1
        fp = self._loc_to_file_path(path, environ)

        if not os.path.exists(fp):
            return None
        if not self.fs_opts.get("follow_symlinks") and os.path.islink(fp):
            raise DAVError(HTTP_FORBIDDEN, f"Symlink support is disabled: {fp!r}")
        if os.path.isdir(fp):
            return FolderResource(path, environ, fp)
        return FileResource(path, environ, fp)
