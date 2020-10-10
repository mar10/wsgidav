# -*- coding: utf-8 -*-
# (c) 2009-2020 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
DAV provider that publishes a Mercurial repository.

Note: This is **not** production code!

The repository is rendered as three top level collections.

edit:
    Contains the working directory, i.e. all files. This includes uncommitted
    changes and untracked new files.
    This folder is writable.
released:
    Contains the latest committed files, also known as 'tip'.
    This folder is read-only.
archive:
    Contains the last 10 revisions as sub-folders.
    This folder is read-only.

Sample layout::

    /<share>/
        edit/
            server/
                ext_server.py
            README.txt
        released/
        archive/
            19/
            18/
            ...

Supported features:

#. Copying or moving files from ``/edit/..`` to the ``/edit/..`` folder will
   result in a ``hg copy`` or ``hg rename``.
#. Deleting resources from ``/edit/..`` will result in a ``hg remove``.
#. Copying or moving files from ``/edit/..`` to the ``/released`` folder will
   result in a ``hg commit``.
   Note that the destination path is ignored, instead the source path is used.
   So a user can drag a file or folder from somewhere under the ``edit/..``
   directory and drop it directly on the ``released`` directory to commit
   changes.
#. To commit all changes, simply drag'n'drop the ``/edit`` folder on the
   ``/released`` folder.
#. Creating new collections results in creation of a file called ``.directory``,
   which is then ``hg add`` ed since Mercurial doesn't track directories.
#. Some attributes are published as live properties, such as ``{hg:}date``.


Known limitations:

#. This 'commit by drag-and-drop' only works, if the WebDAV clients produces
   MOVE or COPY requests. Alas, some clients will send PUT, MKCOL, ... sequences
   instead.
#. Adding and then removing a file without committing after the 'add' will
   leave this file on disk (untracked)
   This happens for example whit lock files that Open Office Write and other
   applications will create.
#. Dragging the 'edit' folder onto 'released' with Windows File Explorer will
   remove the folder in the explorer view, although WsgiDAV did not delete it.
   This seems to be done by the client.


See:
    http://mercurial.selenic.com/wiki/MercurialApi
Requirements:
    ``easy_install mercurial`` or install the API as non-standalone version
    from here: http://mercurial.berkwood.com/
    http://mercurial.berkwood.com/binaries/mercurial-1.4.win32-py2.6.exe
"""
from __future__ import print_function
from hashlib import md5
from pprint import pprint
from wsgidav import compat, util
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN
from wsgidav.dav_provider import _DAVResource, DAVProvider
from wsgidav.samples.dav_provider_tools import VirtualCollection

import os
import sys
import time


try:
    import mercurial.ui
    from mercurial.__version__ import version as hgversion
    from mercurial import commands, hg

    # from mercurial import util as hgutil
except ImportError:
    print(
        "Could not import Mercurial API. Try 'easy_install -U mercurial'.",
        file=sys.stderr,
    )
    raise

__docformat__ = "reStructuredText en"

_logger = util.get_module_logger(__name__)

BUFFER_SIZE = 8192


# ============================================================================
# HgResource
# ============================================================================
class HgResource(_DAVResource):
    """Abstract base class for all resources."""

    def __init__(self, path, is_collection, environ, rev, localHgPath):
        super(HgResource, self).__init__(path, is_collection, environ)
        self.rev = rev
        self.localHgPath = localHgPath
        self.absFilePath = self._getFilePath()
        assert "\\" not in self.localHgPath
        assert "/" not in self.absFilePath

        if is_collection:
            self.fctx = None
        else:
            # Change Context for the requested revision:
            # rev=None: current working dir
            # rev="tip": TIP
            # rev=<int>: Revision ID
            wdctx = self.provider.repo[self.rev]
            self.fctx = wdctx[self.localHgPath]

    #        util.status("HgResource: path=%s, rev=%s, localHgPath=%s, fctx=%s" % (
    #            self.path, self.rev, self.localHgPath, self.fctx))
    #        util.status("HgResource: name=%s, dn=%s, abspath=%s" % (
    #            self.name, self.get_display_name(), self.absFilePath))

    def _getFilePath(self, *addParts):
        parts = self.localHgPath.split("/")
        if addParts:
            parts.extend(addParts)
        return os.path.join(self.provider.repo.root, *parts)

    def _commit(self, message):
        user = self.environ.get("wsgidav.auth.user_name") or "Anonymous"
        commands.commit(
            self.provider.ui,
            self.provider.repo,
            self.localHgPath,
            addremove=True,
            user=user,
            message=message,
        )

    def _check_write_access(self):
        """Raise HTTP_FORBIDDEN, if resource is unwritable."""
        if self.rev is not None:
            # Only working directory may be edited
            raise DAVError(HTTP_FORBIDDEN)

    def get_content_length(self):
        if self.is_collection:
            return None
        return self.fctx.size()

    def get_content_type(self):
        if self.is_collection:
            return None
        #        (mimetype, _mimeencoding) = mimetypes.guess_type(self.path)
        #        if not mimetype:
        #            return "application/octet-stream"
        #        return mimetype
        return util.guess_mime_type(self.path)

    def get_creation_date(self):
        # statresults = os.stat(self._file_path)
        # return statresults[stat.ST_CTIME]
        return None  # TODO

    def get_display_name(self):
        if self.is_collection or self.fctx.filerev() is None:
            return self.name
        return "%s@%s" % (self.name, self.fctx.filerev())

    def get_etag(self):
        return (
            md5(self.path).hexdigest()
            + "-"
            + compat.to_native(self.get_last_modified())
            + "-"
            + str(self.get_content_length())
        )

    def get_last_modified(self):
        if self.is_collection:
            return None
        # (secs, tz-ofs)
        return self.fctx.date()[0]

    def support_ranges(self):
        return False

    def get_member_names(self):
        assert self.is_collection
        cache = self.environ["wsgidav.hg.cache"][compat.to_native(self.rev)]
        dirinfos = cache["dirinfos"]
        if self.localHgPath not in dirinfos:
            return []
        return dirinfos[self.localHgPath][0] + dirinfos[self.localHgPath][1]

    #        return self.provider._listMembers(self.path)

    def get_member(self, name):
        # Rely on provider to get member oinstances
        assert self.is_collection
        return self.provider.get_resource_inst(
            util.join_uri(self.path, name), self.environ
        )

    def get_display_info(self):
        if self.is_collection:
            return {"type": "Directory"}
        return {"type": "File"}

    def get_property_names(self, is_allprop):
        """Return list of supported property names in Clark Notation.

        See DAVResource.get_property_names()
        """
        # Let base class implementation add supported live and dead properties
        propNameList = super(HgResource, self).get_property_names(is_allprop)
        # Add custom live properties (report on 'allprop' and 'propnames')
        if self.fctx:
            propNameList.extend(
                [
                    "{hg:}branch",
                    "{hg:}date",
                    "{hg:}description",
                    "{hg:}filerev",
                    "{hg:}rev",
                    "{hg:}user",
                ]
            )
        return propNameList

    def get_property_value(self, name):
        """Return the value of a property.

        See get_property_value()
        """
        # Supported custom live properties
        if name == "{hg:}branch":
            return self.fctx.branch()
        elif name == "{hg:}date":
            # (secs, tz-ofs)
            return compat.to_native(self.fctx.date()[0])
        elif name == "{hg:}description":
            return self.fctx.description()
        elif name == "{hg:}filerev":
            return compat.to_native(self.fctx.filerev())
        elif name == "{hg:}rev":
            return compat.to_native(self.fctx.rev())
        elif name == "{hg:}user":
            return compat.to_native(self.fctx.user())

        # Let base class implementation report live and dead properties
        return super(HgResource, self).get_property_value(name)

    def set_property_value(self, name, value, dry_run=False):
        """Set or remove property value.

        See DAVResource.set_property_value()
        """
        raise DAVError(HTTP_FORBIDDEN)

    def prevent_locking(self):
        """Return True, to prevent locking.

        See prevent_locking()
        """
        if self.rev is not None:
            # Only working directory may be locked
            return True
        return False

    def create_empty_resource(self, name):
        """Create and return an empty (length-0) resource as member of self.

        See DAVResource.create_empty_resource()
        """
        assert self.is_collection
        self._check_write_access()
        filepath = self._getFilePath(name)
        f = open(filepath, "w")
        f.close()
        commands.add(self.provider.ui, self.provider.repo, filepath)
        # get_resource_inst() won't work, because the cached manifest is outdated
        #        return self.provider.get_resource_inst(self.path.rstrip("/")+"/"+name, self.environ)
        return HgResource(
            self.path.rstrip("/") + "/" + name,
            False,
            self.environ,
            self.rev,
            self.localHgPath + "/" + name,
        )

    def create_collection(self, name):
        """Create a new collection as member of self.

        A dummy member is created, because Mercurial doesn't handle folders.
        """
        assert self.is_collection
        self._check_write_access()
        collpath = self._getFilePath(name)
        os.mkdir(collpath)
        filepath = self._getFilePath(name, ".directory")
        f = open(filepath, "w")
        f.write("Created by WsgiDAV.")
        f.close()
        commands.add(self.provider.ui, self.provider.repo, filepath)

    def get_content(self):
        """Open content as a stream for reading.

        See DAVResource.get_content()
        """
        assert not self.is_collection
        d = self.fctx.data()
        return compat.StringIO(d)

    def begin_write(self, content_type=None):
        """Open content as a stream for writing.

        See DAVResource.begin_write()
        """
        assert not self.is_collection
        self._check_write_access()
        mode = "wb"
        # GC issue 57: always store as binary
        #        if contentType and contentType.startswith("text"):
        #            mode = "w"
        return open(self.absFilePath, mode, BUFFER_SIZE)

    def end_write(self, with_errors):
        """Called when PUT has finished writing.

        See DAVResource.end_write()
        """
        if not with_errors:
            commands.add(self.provider.ui, self.provider.repo, self.localHgPath)

    #    def handle_delete(self):
    #        """Handle a DELETE request natively.
    #
    #        """
    #        self._check_write_access()
    #        return False

    def support_recursive_delete(self):
        """Return True, if delete() may be called on non-empty collections
        (see comments there)."""
        return True

    def delete(self):
        """Remove this resource (recursive)."""
        self._check_write_access()
        filepath = self._getFilePath()
        commands.remove(self.provider.ui, self.provider.repo, filepath, force=True)

    def handle_copy(self, dest_path, depth_infinity):
        """Handle a COPY request natively."""
        destType, destHgPath = util.pop_path(dest_path)
        destHgPath = destHgPath.strip("/")
        ui = self.provider.ui
        repo = self.provider.repo
        _logger.info("handle_copy %s -> %s" % (self.localHgPath, destHgPath))
        if self.rev is None and destType == "edit":
            # COPY /edit/a/b to /edit/c/d: turn into 'hg copy -f a/b c/d'
            commands.copy(ui, repo, self.localHgPath, destHgPath, force=True)
        elif self.rev is None and destType == "released":
            # COPY /edit/a/b to /released/c/d
            # This is interpreted as 'hg commit a/b' (ignoring the dest. path)
            self._commit("WsgiDAV commit (COPY %s -> %s)" % (self.path, dest_path))
        else:
            raise DAVError(HTTP_FORBIDDEN)
        # Return True: request was handled
        return True

    def handle_move(self, dest_path):
        """Handle a MOVE request natively."""
        destType, destHgPath = util.pop_path(dest_path)
        destHgPath = destHgPath.strip("/")
        ui = self.provider.ui
        repo = self.provider.repo
        _logger.info("handle_copy %s -> %s" % (self.localHgPath, destHgPath))
        if self.rev is None and destType == "edit":
            # MOVE /edit/a/b to /edit/c/d: turn into 'hg rename -f a/b c/d'
            commands.rename(ui, repo, self.localHgPath, destHgPath, force=True)
        elif self.rev is None and destType == "released":
            # MOVE /edit/a/b to /released/c/d
            # This is interpreted as 'hg commit a/b' (ignoring the dest. path)
            self._commit("WsgiDAV commit (MOVE %s -> %s)" % (self.path, dest_path))
        else:
            raise DAVError(HTTP_FORBIDDEN)
        # Return True: request was handled
        return True


# ============================================================================
# HgResourceProvider
# ============================================================================


class HgResourceProvider(DAVProvider):
    """
    DAV provider that serves a VirtualResource derived structure.
    """

    def __init__(self, repoRoot):
        super(HgResourceProvider, self).__init__()
        self.repoRoot = repoRoot
        print("Mercurial version %s" % hgversion)
        self.ui = mercurial.ui.ui()
        self.repo = hg.repository(self.ui, repoRoot)
        self.ui.status("Connected to repository %s\n" % self.repo.root)
        self.repoRoot = self.repo.root

        # Some commands (remove) seem to expect cwd set to the repo
        # TODO: try to go along without this, because it prevents serving
        #       multiple repos. Instead pass absolute paths to the commands.
        #        print(os.getcwd())
        os.chdir(self.repo.root)

        # Verify integrity of the repository
        _logger.warning("Verify repository '%s' tree..." % self.repo.root)
        commands.verify(self.ui, self.repo)

        #        self.ui.status("Changelog: %s\n" % self.repo.changelog)
        print("Status:")
        pprint(self.repo.status())
        self.repo.ui.status(
            "the default user_name to be used in commits: %s\n"
            % self.repo.ui.user_name()
        )
        #        self.repo.ui.status("a short form of user name USER %s\n" % self.repo.ui.shortuser(user))
        self.ui.status("Expandpath: %s\n" % self.repo.ui.expandpath(repoRoot))

        print("Working directory state summary:")
        self.ui.pushbuffer()
        commands.summary(self.ui, self.repo, remote=False)
        res = self.ui.popbuffer().strip()
        reslines = [tuple(line.split(":", 1)) for line in res.split("\n")]
        pprint(reslines)

        print("Repository state summary:")
        self.ui.pushbuffer()
        commands.identify(self.ui, self.repo, num=True, id=True, branch=True, tags=True)
        res = self.ui.popbuffer().strip()
        reslines = [tuple(line.split(":", 1)) for line in res.split("\n")]
        pprint(reslines)

        self._get_log()

    def _get_log(self, limit=None):
        """Read log entries into a list of dictionaries."""
        self.ui.pushbuffer()
        commands.log(self.ui, self.repo, limit=limit, date=None, rev=None, user=None)
        res = self.ui.popbuffer().strip()

        logList = []
        for logentry in res.split("\n\n"):
            log = {}
            logList.append(log)
            for line in logentry.split("\n"):
                k, v = line.split(":", 1)
                assert k in ("changeset", "tag", "user", "date", "summary")
                log[k.strip()] = v.strip()
            log["parsed_date"] = util.parse_time_string(log["date"])
            local_id, unid = log["changeset"].split(":")
            log["local_id"] = int(local_id)
            log["unid"] = unid
        #        pprint(logList)
        return logList

    def _get_repo_info(self, environ, rev, reload=False):
        """Return a dictionary containing all files under source control.

        dirinfos:
            Dictionary containing direct members for every collection.
            {folderpath: (collectionlist, filelist), ...}
        files:
            Sorted list of all file paths in the manifest.
        filedict:
            Dictionary containing all files under source control.

        ::

            {'dirinfos': {'': (['wsgidav',
                                'tools',
                                'WsgiDAV.egg-info',
                                'tests'],
                               ['index.rst',
                                'wsgidav MAKE_DAILY_BUILD.launch',
                                'wsgidav run_server.py DEBUG.launch',
                                'wsgidav-paste.conf',
                                ...
                                'setup.py']),
                          'wsgidav': (['addons', 'samples', 'server', 'interfaces'],
                                      ['__init__.pyc',
                                       'dav_error.pyc',
                                       'dav_provider.pyc',
                                       ...
                                       'wsgidav_app.py']),
                           },
             'files': ['.hgignore',
                       'ADDONS.txt',
                       'wsgidav/samples/mysql_dav_provider.py',
                       ...
                       ],
             'filedict': {'.hgignore': True,
                           'README.txt': True,
                           'WsgiDAV.egg-info/PKG-INFO': True,
                           }
                           }
        """
        caches = environ.setdefault("wsgidav.hg.cache", {})
        if caches.get(compat.to_native(rev)) is not None:
            _logger.debug("_get_repo_info(%s): cache hit." % rev)
            return caches[compat.to_native(rev)]

        start_time = time.time()
        self.ui.pushbuffer()
        commands.manifest(self.ui, self.repo, rev)
        res = self.ui.popbuffer()
        files = []
        dirinfos = {}
        filedict = {}
        for file in res.split("\n"):
            if file.strip() == "":
                continue
            file = file.replace("\\", "/")
            # add all parent directories to 'dirinfos'
            parents = file.split("/")
            if len(parents) >= 1:
                p1 = ""
                for i in range(0, len(parents) - 1):
                    p2 = parents[i]
                    dir = dirinfos.setdefault(p1, ([], []))
                    if p2 not in dir[0]:
                        dir[0].append(p2)
                    if p1 == "":
                        p1 = p2
                    else:
                        p1 = "%s/%s" % (p1, p2)
                dirinfos.setdefault(p1, ([], []))[1].append(parents[-1])
            filedict[file] = True
        files.sort()

        cache = {"files": files, "dirinfos": dirinfos, "filedict": filedict}
        caches[compat.to_native(rev)] = cache
        _logger.info("_getRepoInfo(%s) took %.3f" % (rev, time.time() - start_time))
        return cache

    #    def _listMembers(self, path, rev=None):
    #        """Return a list of all non-collection members"""
    #        # Pattern for direct members:
    #        glob = "glob:" + os.path.join(path, "*").lstrip("/")
    #        print(glob)
    #        self.ui.pushbuffer()
    #        commands.status(self.ui, self.repo,
    #                        glob,
    #                        all=True)
    #        lines = self.ui.popbuffer().strip().split("\n")
    #        pprint(lines)
    #        return dict

    def get_resource_inst(self, path, environ):
        """Return HgResource object for path.

        See DAVProvider.get_resource_inst()
        """
        self._count_get_resource_inst += 1

        # HG expects the resource paths without leading '/'
        localHgPath = path.strip("/")
        rev = None
        cmd, rest = util.pop_path(path)

        if cmd == "":
            return VirtualCollection(
                path, environ, "root", ["edit", "released", "archive"]
            )
        elif cmd == "edit":
            localHgPath = rest.strip("/")
            rev = None
        elif cmd == "released":
            localHgPath = rest.strip("/")
            rev = "tip"
        elif cmd == "archive":
            if rest == "/":
                # Browse /archive: return a list of revision folders:
                loglist = self._get_log(limit=10)
                members = [compat.to_native(m["local_id"]) for m in loglist]
                return VirtualCollection(path, environ, "Revisions", members)
            revid, rest = util.pop_path(rest)
            try:
                int(revid)
            except Exception:
                # Tried to access /archive/anyname
                return None
            # Access /archive/19
            rev = revid
            localHgPath = rest.strip("/")
        else:
            return None

        # read mercurial repo into request cache
        cache = self._get_repo_info(environ, rev)

        if localHgPath in cache["filedict"]:
            # It is a version controlled file
            return HgResource(path, False, environ, rev, localHgPath)

        if localHgPath in cache["dirinfos"] or localHgPath == "":
            # It is an existing folder
            return HgResource(path, True, environ, rev, localHgPath)
        return None
