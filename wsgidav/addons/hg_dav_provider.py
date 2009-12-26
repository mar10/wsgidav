# -*- coding: iso-8859-1 -*-
"""
:Author: Martin Wendt
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

Sample implementation of a DAV provider that pulishes a mercurial reposity.

See:
    http://mercurial.berkwood.com/binaries/mercurial-1.4.win32-py2.6.exe

Sample layout::
    
    /<share>/
        tip/
            server/
                ext_server.py
            README.txt
        archive/
            rev1/
            rev2/
        tags/
            release1/
            

"""
from pprint import pprint
import sys
import mimetypes
import stat

import os
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO #@UnusedImport
from wsgidav.dav_provider import DAVProvider, DAVResource
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN, HTTP_INTERNAL_ERROR,\
    PRECONDITION_CODE_ProtectedProperty
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
# _VirtualResource classes
#===============================================================================
class HgResource(DAVResource):
    """Abstract base class for all resources."""
    def __init__(self, provider, path, isCollection):
        super(HgResource, self).__init__(provider, path, isCollection)
        self._filePath = os.path.join(self.provider.repoPath, *path.split("/"))
#        print path, self._filePath

    def getContentLength(self):
        statresults = os.stat(self._filePath)
        return statresults[stat.ST_SIZE]
    def getContentType(self):
        (mimetype, _mimeencoding) = mimetypes.guess_type(self.path)  
        if not mimetype:
            return "application/octet-stream" 
        return mimetype
    def getCreationDate(self):
        statresults = os.stat(self._filePath)
        return statresults[stat.ST_CTIME]
    def getDisplayName(self):
        return self.name
    def getEtag(self):
        return util.getETag(self._filePath)
    def getLastModified(self):
        statresults = os.stat(self._filePath)
        return statresults[stat.ST_MTIME]
    def supportRanges(self):
        return False
    def displayType(self):
        if self.isCollection:
            return "Directory"
        return "File"
        
    def getMemberNames(self):
        assert self.isCollection
        dirinfos = self.provider.tree["dirinfos"] 
        return dirinfos[self.path][0] + dirinfos[self.path][1] 
#        return self.provider._listMembers(self.path)
        # TODO: this is not efficient!

#        childlist = []
#        l = len(self.path)
#        for f in self.provider.files:
#            if f.startswith(self.path):
#                p = f[l:]
##                print f, p
#                if "/" in p:
#                    # This is a member container, so we only append it once
#                    p = p.split("/")[0]
#                if len(childlist) == 0 or childlist[-1] != p:
#                    childlist.append(p) 
#            else:
#                if len(childlist) > 0:
#                    # we reached the end of the matching sequence
#                    break
        return childlist

    def getContent(self):
        """Open content as a stream for reading.
         
        See DAVResource.getContent()
        """
        assert not self.isCollection
        mime = self.getContentType()
        if mime.startswith("text"):
            return file(self._filePath, "r", BUFFER_SIZE)
        return file(self._filePath, "rb", BUFFER_SIZE)
        
         
#===============================================================================
# HgResourceProvider
#===============================================================================


class HgResourceProvider(DAVProvider):
    """
    DAV provider that serves a VirtualResource derived structure.
    """
    def __init__(self, repoPath):
        super(HgResourceProvider, self).__init__()
        self.repoPath = repoPath
        print "Mercurial version %s" % hgversion
        self.ui = mercurial.ui.ui()
        self.repo = hg.repository(self.ui, repoPath)
        self.ui.status("Connected to repository %s\n" % self.repo.root)
        self.repoPath = self.repo.root

        # Verify integrity of the repository
        print "Verify repository '%s' tree..." % self.repo.root
        commands.verify(self.ui, self.repo)
        
        print "Reading tree..."
        self.tree = self._readTree()
        pprint(self.tree)
        
#        self.ui.status("Changelog: %s\n" % self.repo.changelog)
        print "Status:"
        pprint(self.repo.status())
#        self.repo.ui.status("Status: %s\n" % ", ".join(self.repo.status()))
#        self.repo.ui.status("preferred editor: %s\n" % self.repo.ui.editor())
        self.repo.ui.status("the default username to be used in commits: %s\n" % self.repo.ui.username())
#        self.repo.ui.status("a short form of user name USER %s\n" % self.repo.ui.shortuser(user))
        self.ui.status("Expandpath: %s\n" % self.repo.ui.expandpath(repoPath))
        
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


#        print "Status:"
#        # files: sorted list of all file paths under source control
#        # statusdict: {filepath: status, ...}
#        # folders: {folderpath: (collectionlist, filelist), ...}
#        self.ui.pushbuffer()
#        commands.status(self.ui, self.repo, all=True)
#        res = self.ui.popbuffer()
#        self.files = []
#        self.statusdict = {} 
#        for line in res.split("\n"):
#            if line.strip():
#                stat, file = line.split(" ", 1)
#                file = "/" + file.replace("\\", "/")
#                self.files.append(file)
#                self.statusdict[file] = stat
##                for parent in file.strip("/").split("/"):
#                    
#        self.files.sort()
#        pprint(self.statusdict)
#        pprint(self.files)

#        print "Log:"
#        self.ui.pushbuffer()
#        commands.log(self.ui, self.repo, limit=3)
#        res = self.ui.popbuffer().strip()
#        statuslist = [ tuple(line.split(":", 1)) for line in res.split("\n")]
#        pprint(statuslist)

        
        # 'cat': get file content for a given revision:
#        self.ui.pushbuffer()
#        commands.cat(self.ui, self.repo, filename)
#        res = self.ui.popbuffer()
        # heads
        # manifest: list all versioned files
        # parents
        # paths
        # showconfig
        
        print "Tip:"
        self.ui.pushbuffer()
        commands.tip(self.ui, self.repo)
        res = self.ui.popbuffer().strip()
        statuslist = [ tuple(line.split(":", 1)) for line in res.split("\n")]
        pprint(statuslist)
#        raise
#        self.repo.ui.status(self.repo.)
        

    def _readTree(self, rev=None):
        """Return a dictionary containing all files under source control.

        files: sorted list of all file paths under source control
        filestats: {filepath: status, ...}
        dirinfos: {folderpath: (collectionlist, filelist), ...}
        
        {'dirinfos': {'/': (['wsgidav',
                             'tools',
                             '.settings',
                             'WsgiDAV.egg-info',
                             'tests'],
                            ['index.rst',
                             'wsgidav MAKE_DAILY_BUILD.launch',
                             'wsgidav run_server.py DEBUG.launch',
                             'wsgidav run_server.py RELEASE.launch',
                             'wsgidav test_all.py.launch',
                             'wsgidav-paste.conf',
                             ...
                             'setup.py']),
                      '/wsgidav': (['addons', 'samples', 'server', 'interfaces'],
                                   ['__init__.pyc',
                                    'dav_error.pyc',
                                    'dav_provider.pyc',
                                    ...
                                    'wsgidav_app.py']),
                        },
         'files': ['/.hgignore',
                   '/ADDONS.txt',
                   '/wsgidav/addons/mysql_dav_provider.py',
                   ...
                   ],
         'filestats': {'/.hgignore': 'C',
                       '/README.txt': 'C',
                       '/WsgiDAV.egg-info/PKG-INFO': 'I',
                       }
                       }
        """
        self.ui.pushbuffer()
#        commands.status(self.ui, self.repo, all=True)
        commands.status(self.ui, self.repo, modified=True, added=True, clean=True)
        res = self.ui.popbuffer()
        files = []
        dirinfos = {}
        filestats = {} 
        for line in res.split("\n"):
            if len(line) < 3:
                continue
            stat, file = line.split(" ", 1)
            file = file.replace("\\", "/")
            # add all parent directories to 'dirinfos'
            parents = file.split("/")
            if len(parents) >= 1:
                p1 = "/"
                for i in range(0, len(parents)-1):
                    p2 = parents[i]
                    dir = dirinfos.setdefault(p1, ([], []))
                    if not p2 in dir[0]:
                        dir[0].append(p2)
                    p1 = "%s/%s" % (p1.rstrip("/"), p2)
                dirinfos.setdefault(p1, ([], []))[1].append(parents[-1])
            file = "/" + file 
            files.append(file)
            filestats[file] = stat
        files.sort()
        return {"files": files,
                "dirinfos": dirinfos,
                "filestats": filestats,
                }

        
#    def _identify(self, path, rev=None):
#        self.ui.pushbuffer()
#        commands.identify(self.ui, self.repo, 
#                          num=True, id=True, branch=True, tags=True)
#        res = self.ui.popbuffer().strip().split(" ")
#        hasChanges = res[0].endswith("+")
#        dict = {"id": res[0].strip("+"),
#                "num": res[1].strip("+"),
#                "branch": res[2],
#                "tag": res[3], 
#                "hasChanges": hasChanges,
#                "path": path,
#                }
#        pprint(dict)
#        return dict
        
    def _listMembers(self, path, rev=None):
        """Return a list of all non-collection members"""
        # Pattern gor direct members:
        glob = "glob:" + os.path.join(path, "*").lstrip("/")
#        print glob
        self.ui.pushbuffer()
        commands.status(self.ui, self.repo,
                        glob, 
                        all=True)
        lines = self.ui.popbuffer().strip().split("\n")
        pprint(lines)
        return dict
        
    def getResourceInst(self, path):
        """Return _VirtualResource object for path.
        
        path is expected to be 
            categoryType/category/name/artifact
        for example:
            'by_tag/cool/My doc 2/info.html'

        See DAVProvider.getResourceInst()
        """
        self._count_getResourceInst += 1
        
#        catType, cat, resName, artifactName = util.saveSplit(path.strip("/"), "/", 3)
        #info = self._identify(path)
        p = "/" + path.strip("/")
        if p in self.tree["filestats"]:
            # It is a version controlled file
            return HgResource(self, path, False)
        
        if p in self.tree["dirinfos"]:
            # It is an existing folder
            return HgResource(self, p, True)
        return None
        
