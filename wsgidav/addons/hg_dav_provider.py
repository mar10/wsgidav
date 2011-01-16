# -*- coding: iso-8859-1 -*-
# (c) 2009-2011 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
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
from pprint import pprint
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN
import os
from wsgidav.samples.dav_provider_tools import VirtualCollection
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import time
import sys
import mimetypes

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO #@UnusedImport
from wsgidav.dav_provider import DAVProvider, _DAVResource
from wsgidav import util

try:
    import mercurial.ui
    from mercurial.__version__ import version as hgversion
    from mercurial import commands, hg
    #from mercurial import util as hgutil 
except ImportError:
    print >>sys.stderr, "Could not import Mercurial API. Try 'easy_install -U mercurial'."
    raise

__docformat__ = "reStructuredText en"

_logger = util.getModuleLogger(__name__)

BUFFER_SIZE = 8192


#===============================================================================
# HgResource
#===============================================================================
class HgResource(_DAVResource):
    """Abstract base class for all resources."""
    def __init__(self, path, isCollection, environ, rev, localHgPath):
        super(HgResource, self).__init__(path, isCollection, environ)
        self.rev = rev
        self.localHgPath = localHgPath 
        self.absFilePath = self._getFilePath() 
        assert not "\\" in self.localHgPath
        assert not "/" in self.absFilePath
        
        if isCollection:
            self.fctx = None
        else:
            # Change Context for the requested revision:
            # rev=None: current working dir
            # rev="tip": TIP
            # rev=<int>: Revision ID
            wdctx = self.provider.repo[self.rev]
            self.fctx = wdctx[self.localHgPath]
#        util.status("HgResource: path=%s, rev=%s, localHgPath=%s, fctx=%s" % (self.path, self.rev, self.localHgPath, self.fctx))
#        util.status("HgResource: name=%s, dn=%s, abspath=%s" % (self.name, self.getDisplayName(), self.absFilePath))

    def _getFilePath(self, *addParts):
        parts = self.localHgPath.split("/")
        if addParts:
            parts.extend(addParts)
        return os.path.join(self.provider.repo.root, *parts)

    def _commit(self, message):
        user = self.environ.get("http_authenticator.username") or "Anonymous"
        commands.commit(self.provider.ui, self.provider.repo, 
                        self.localHgPath, 
                        addremove=True,
                        user=user,
                        message=message)

    def _checkWriteAccess(self):
        """Raise HTTP_FORBIDDEN, if resource is unwritable."""
        if self.rev is not None:
            # Only working directory may be edited 
            raise DAVError(HTTP_FORBIDDEN)

    def getContentLength(self):
        if self.isCollection:
            return None
        return self.fctx.size()

    def getContentType(self):
        if self.isCollection:
            return None
        (mimetype, _mimeencoding) = mimetypes.guess_type(self.path)  
        if not mimetype:
            return "application/octet-stream" 
        return mimetype
    
    def getCreationDate(self):
#        statresults = os.stat(self._filePath)
#        return statresults[stat.ST_CTIME]
        return None # TODO
    
    def getDisplayName(self):
        if self.isCollection or self.fctx.filerev() is None:
            return self.name
        return "%s@%s" % (self.name, self.fctx.filerev())
    
    def getEtag(self):
        return md5(self.path).hexdigest() + "-" + str(self.getLastModified()) + "-" + str(self.getContentLength())
    
    def getLastModified(self):
        if self.isCollection:
            return None
        # (secs, tz-ofs)
        return self.fctx.date()[0]
    
    def supportRanges(self):
        return False
    
    def getMemberNames(self):
        assert self.isCollection
        cache = self.environ["wsgidav.hg.cache"][str(self.rev)]
        dirinfos = cache["dirinfos"] 
        if not dirinfos.has_key(self.localHgPath):
            return []
        return dirinfos[self.localHgPath][0] + dirinfos[self.localHgPath][1] 
#        return self.provider._listMembers(self.path)

    def getMember(self, name):
        # Rely on provider to get member oinstances
        assert self.isCollection
        return self.provider.getResourceInst(util.joinUri(self.path, name), 
                                             self.environ)
    def getDisplayInfo(self):
        if self.isCollection:
            return {"type": "Directory"}
        return {"type": "File"}

    def getPropertyNames(self, isAllProp):
        """Return list of supported property names in Clark Notation.
        
        See DAVResource.getPropertyNames() 
        """
        # Let base class implementation add supported live and dead properties
        propNameList = super(HgResource, self).getPropertyNames(isAllProp)
        # Add custom live properties (report on 'allprop' and 'propnames')
        if self.fctx:
            propNameList.extend(["{hg:}branch",
                                 "{hg:}date",
                                 "{hg:}description",
                                 "{hg:}filerev",
                                 "{hg:}rev",
                                 "{hg:}user",
                                 ])
        return propNameList
    
    def getPropertyValue(self, propname):
        """Return the value of a property.
        
        See getPropertyValue()
        """
        # Supported custom live properties
        if propname == "{hg:}branch":
            return self.fctx.branch()
        elif propname == "{hg:}date":
            # (secs, tz-ofs)
            return str(self.fctx.date()[0])
        elif propname == "{hg:}description":
            return self.fctx.description()
        elif propname == "{hg:}filerev":
            return str(self.fctx.filerev())
        elif propname == "{hg:}rev":
            return str(self.fctx.rev())
        elif propname == "{hg:}user":
            return str(self.fctx.user())
        
        # Let base class implementation report live and dead properties
        return super(HgResource, self).getPropertyValue(propname)
    
    def setPropertyValue(self, propname, value, dryRun=False):
        """Set or remove property value.
        
        See DAVResource.setPropertyValue()
        """
        raise DAVError(HTTP_FORBIDDEN)

    def preventLocking(self):
        """Return True, to prevent locking.
        
        See preventLocking()
        """
        if self.rev is not None:
            # Only working directory may be locked 
            return True
        return False               

    def createEmptyResource(self, name):
        """Create and return an empty (length-0) resource as member of self.
        
        See DAVResource.createEmptyResource()
        """
        assert self.isCollection
        self._checkWriteAccess()    
        filepath = self._getFilePath(name)
        f = open(filepath, "w")
        f.close()
        commands.add(self.provider.ui, self.provider.repo, filepath)
        # getResourceInst() won't work, because the cached manifest is outdated 
#        return self.provider.getResourceInst(self.path.rstrip("/")+"/"+name, self.environ)
        return HgResource(self.path.rstrip("/")+"/"+name, False, 
                          self.environ, self.rev, self.localHgPath+"/"+name)
    
    def createCollection(self, name):
        """Create a new collection as member of self.
        
        A dummy member is created, because Mercurial doesn't handle folders.
        """
        assert self.isCollection
        self._checkWriteAccess()
        collpath = self._getFilePath(name)
        os.mkdir(collpath)
        filepath = self._getFilePath(name, ".directory") 
        f = open(filepath, "w")
        f.write("Created by WsgiDAV.")
        f.close()
        commands.add(self.provider.ui, self.provider.repo, filepath)

    def getContent(self):
        """Open content as a stream for reading.
         
        See DAVResource.getContent()
        """
        assert not self.isCollection
        d = self.fctx.data()
        return StringIO(d)
    
    def beginWrite(self, contentType=None):
        """Open content as a stream for writing.
         
        See DAVResource.beginWrite()
        """
        assert not self.isCollection
        self._checkWriteAccess()
        mode = "wb"
        if contentType and contentType.startswith("text"):
            mode = "w"
        return file(self.absFilePath, mode, BUFFER_SIZE)

    def endWrite(self, withErrors):
        """Called when PUT has finished writing.

        See DAVResource.endWrite()
        """
        if not withErrors:           
            commands.add(self.provider.ui, self.provider.repo, self.localHgPath)

#    def handleDelete(self):
#        """Handle a DELETE request natively.
#        
#        """
#        self._checkWriteAccess()               
#        return False               

    
    def supportRecursiveDelete(self):
        """Return True, if delete() may be called on non-empty collections 
        (see comments there)."""
        return True

    
    def delete(self):
        """Remove this resource (recursive)."""
        self._checkWriteAccess()
        filepath = self._getFilePath()
        commands.remove(self.provider.ui, self.provider.repo,
                        filepath,
                        force=True)

        
    def handleCopy(self, destPath, depthInfinity):
        """Handle a COPY request natively.
        
        """
        destType, destHgPath = util.popPath(destPath)
        destHgPath = destHgPath.strip("/")
        ui = self.provider.ui  
        repo = self.provider.repo
        util.write("handleCopy %s -> %s" % (self.localHgPath, destHgPath))
        if self.rev is None and destType == "edit":
            # COPY /edit/a/b to /edit/c/d: turn into 'hg copy -f a/b c/d'
            commands.copy(ui, repo, 
                          self.localHgPath, 
                          destHgPath,
                          force=True)
        elif self.rev is None and destType == "released":
            # COPY /edit/a/b to /released/c/d
            # This is interpreted as 'hg commit a/b' (ignoring the dest. path)
            self._commit("WsgiDAV commit (COPY %s -> %s)" % (self.path, destPath))
        else:
            raise DAVError(HTTP_FORBIDDEN)
        # Return True: request was handled
        return True               


    def handleMove(self, destPath):
        """Handle a MOVE request natively.
        
        """
        destType, destHgPath = util.popPath(destPath)
        destHgPath = destHgPath.strip("/")
        ui = self.provider.ui  
        repo = self.provider.repo
        util.write("handleCopy %s -> %s" % (self.localHgPath, destHgPath))
        if self.rev is None and destType == "edit":
            # MOVE /edit/a/b to /edit/c/d: turn into 'hg rename -f a/b c/d'
            commands.rename(ui, repo, self.localHgPath, destHgPath,
                            force=True)
        elif self.rev is None and destType == "released":
            # MOVE /edit/a/b to /released/c/d
            # This is interpreted as 'hg commit a/b' (ignoring the dest. path)
            self._commit("WsgiDAV commit (MOVE %s -> %s)" % (self.path, destPath))
        else:
            raise DAVError(HTTP_FORBIDDEN)
        # Return True: request was handled
        return True               

    
#===============================================================================
# HgResourceProvider
#===============================================================================

class HgResourceProvider(DAVProvider):
    """
    DAV provider that serves a VirtualResource derived structure.
    """
    def __init__(self, repoRoot):
        super(HgResourceProvider, self).__init__()
        self.repoRoot = repoRoot
        print "Mercurial version %s" % hgversion
        self.ui = mercurial.ui.ui()
        self.repo = hg.repository(self.ui, repoRoot)
        self.ui.status("Connected to repository %s\n" % self.repo.root)
        self.repoRoot = self.repo.root
        
        # Some commands (remove) seem to expect cwd set to the repo
        # TODO: try to go along without this, because it prevents serving
        #       multiple repos. Instead pass absolute paths to the commands. 
#        print os.getcwd()
        os.chdir(self.repo.root)

        # Verify integrity of the repository
        util.status("Verify repository '%s' tree..." % self.repo.root)
        commands.verify(self.ui, self.repo)
        
#        self.ui.status("Changelog: %s\n" % self.repo.changelog)
        print "Status:"
        pprint(self.repo.status())
        self.repo.ui.status("the default username to be used in commits: %s\n" % self.repo.ui.username())
#        self.repo.ui.status("a short form of user name USER %s\n" % self.repo.ui.shortuser(user))
        self.ui.status("Expandpath: %s\n" % self.repo.ui.expandpath(repoRoot))
        
        print "Working directory state summary:"
        self.ui.pushbuffer()
        commands.summary(self.ui, self.repo, remote=False)
        res = self.ui.popbuffer().strip()
        reslines = [ tuple(line.split(":", 1)) for line in res.split("\n")]
        pprint(reslines)

        print "Repository state summary:"
        self.ui.pushbuffer()
        commands.identify(self.ui, self.repo, 
                          num=True, id=True, branch=True, tags=True)
        res = self.ui.popbuffer().strip()
        reslines = [ tuple(line.split(":", 1)) for line in res.split("\n")]
        pprint(reslines)

        self._getLog()
                

    def _getLog(self, limit=None):
        """Read log entries into a list of dictionaries."""
        self.ui.pushbuffer()
        commands.log(self.ui, self.repo, limit=limit, 
                     date=None, rev=None, user=None)
        res = self.ui.popbuffer().strip()

        logList = []
        for logentry in res.split("\n\n"):
            log = {}
            logList.append(log)
            for line in logentry.split("\n"):
                k, v = line.split(":", 1)
                assert k in ("changeset", "tag", "user", "date", "summary")
                log[k.strip()] = v.strip()
            log["parsed_date"] = util.parseTimeString(log["date"])
            local_id, unid = log["changeset"].split(":")
            log["local_id"] = int(local_id)
            log["unid"] = unid
#        pprint(logList)
        return logList
        

    def _getRepoInfo(self, environ, rev, reload=False):
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
                       'wsgidav/addons/mysql_dav_provider.py',
                       ...
                       ],
             'filedict': {'.hgignore': True,
                           'README.txt': True,
                           'WsgiDAV.egg-info/PKG-INFO': True,
                           }
                           }
        """
        caches = environ.setdefault("wsgidav.hg.cache", {})
        if caches.get(str(rev)) is not None:
            util.debug("_getRepoInfo(%s): cache hit." % rev)
            return caches[str(rev)]

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
                for i in range(0, len(parents)-1):
                    p2 = parents[i]
                    dir = dirinfos.setdefault(p1, ([], []))
                    if not p2 in dir[0]:
                        dir[0].append(p2)
                    if p1 == "":
                        p1 = p2
                    else:
                        p1 = "%s/%s" % (p1, p2)
                dirinfos.setdefault(p1, ([], []))[1].append(parents[-1])
            filedict[file] = True
        files.sort()

        cache = {"files": files,
                 "dirinfos": dirinfos,
                 "filedict": filedict,
                 }
        caches[str(rev)] = cache
        util.note("_getRepoInfo(%s) took %.3f" % (rev, time.time() - start_time)
#                  , var=cache
                  )
        return cache


#    def _listMembers(self, path, rev=None):
#        """Return a list of all non-collection members"""
#        # Pattern for direct members:
#        glob = "glob:" + os.path.join(path, "*").lstrip("/")
##        print glob
#        self.ui.pushbuffer()
#        commands.status(self.ui, self.repo,
#                        glob, 
#                        all=True)
#        lines = self.ui.popbuffer().strip().split("\n")
#        pprint(lines)
#        return dict


    def getResourceInst(self, path, environ):
        """Return HgResource object for path.
        
        See DAVProvider.getResourceInst()
        """
        self._count_getResourceInst += 1

        # HG expects the resource paths without leading '/'
        localHgPath = path.strip("/")
        rev = None
        cmd, rest = util.popPath(path)
        
        if cmd == "":
            return VirtualCollection(path, environ, 
                                     "root",
                                     ["edit", "released", "archive"])
        elif cmd == "edit":
            localHgPath = rest.strip("/")
            rev = None 
        elif cmd == "released":
            localHgPath = rest.strip("/")
            rev = "tip"
        elif cmd == "archive":
            if rest == "/":
                # Browse /archive: return a list of revision folders:
                loglist = self._getLog(limit=10)
                members = [ str(l["local_id"])  for l in loglist ] 
                return VirtualCollection(path, environ, "Revisions", members)
            revid, rest = util.popPath(rest)
            try:
                int(revid)
            except:
                # Tried to access /archive/anyname
                return None
            # Access /archive/19
            rev = revid
            localHgPath = rest.strip("/")
        else:
            return None
        
        # read mercurial repo into request cache
        cache = self._getRepoInfo(environ, rev)
        
        if localHgPath in cache["filedict"]:
            # It is a version controlled file
            return HgResource(path, False, environ, rev, localHgPath)
        
        if localHgPath in cache["dirinfos"] or localHgPath == "":
            # It is an existing folder
            return HgResource(path, True, environ, rev, localHgPath)
        return None
