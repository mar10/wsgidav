# -*- coding: iso-8859-1 -*-
"""
:Author: Martin Wendt
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

Sample implementation of a DAV provider that publishes a Mercurial repository.

See:
    http://mercurial.selenic.com/wiki/MercurialApi
Requirements:
    ``easy_install mercurial`` or install the API as non-standalone version
    from here: http://mercurial.berkwood.com/
    http://mercurial.berkwood.com/binaries/mercurial-1.4.win32-py2.6.exe

Sample layout::
    
    /<share>/
        edit/
            server/
                ext_server.py
            README.txt
        released/
        archive/
            rev1/
            rev2/
        tags/
            release1/
            

"""
from pprint import pprint
from wsgidav.dav_error import DAVError, HTTP_FORBIDDEN
import os
try:
    from hashlib import md5
except ImportError:
    from md5 import md5
import time
import sys
import mimetypes
import stat

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO #@UnusedImport
from wsgidav.dav_provider import DAVProvider, DAVResource
from wsgidav import util

try:
    import mercurial.ui
#    import mercurial.error
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
# VirtualCollection
#===============================================================================
class VirtualCollection(DAVResource):
    """Collection resource, that contains a list of member names."""
    def __init__(self, provider, path, environ, memberNames):
        DAVResource.__init__(self, provider, path, True, environ)
        self._memberNames = memberNames
    def displayType(self):
        return "Virtual Collection"
    def getMemberNames(self):
        return self._memberNames




#===============================================================================
# HgResource
#===============================================================================
class HgResource(DAVResource):
    """Abstract base class for all resources."""
    def __init__(self, provider, path, isCollection, environ, rev, repoPath):
        super(HgResource, self).__init__(provider, path, isCollection, environ)
        self.rev = rev
        self.repoPath = repoPath 

        if isCollection:
#            self.fctx = self.provider.repo.filectx(repoFilePath, fileid="tip")
            self.fctx = None
        else:
            # Change Context for the working directory:
            # rev=None: current working dir
            # rev="tip": TIP
            wdctx = self.provider.repo[self.rev]
            self.fctx = wdctx[self.repoPath]
        util.write("HgResourcdec: path=%s, rev=%s, repoPath=%s, fctx=%s" % 
                   (self.path, self.rev, self.repoPath, self.fctx))

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
        if self.isCollection:
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
    def displayType(self):
        if self.isCollection:
            return "Directory"
        return "File"
        
    def getMemberNames(self):
        assert self.isCollection
        cache = self.environ["wsgidav.hg.cache"][str(self.rev)]
        dirinfos = cache["dirinfos"] 
        return dirinfos[self.repoPath][0] + dirinfos[self.repoPath][1] 
#        return self.provider._listMembers(self.path)

    def getPropertyNames(self, isAllProp):
        """Return list of supported property names in Clark Notation.
        
        See DAVResource.getPropertyNames() 
        """
        # Let base class implementation add supported live and dead properties
        propNameList = super(HgResource, self).getPropertyNames(isAllProp)
        # Add custom live properties (report on 'allprop' and 'propnames')
        if self.fctx:
            propNameList.extend(["{hg:}status",
                                 "{hg:}branch",
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
        cache = self.environ["wsgidav.hg.cache"][str(self.rev)]
        if propname == "{hg:}status":
            return cache["filestats"][self.repoPath]
        elif propname == "{hg:}branch":
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


    def _checkWriteAccess(self):
        """Raise HTTP_FORBIDDEN, if resource is unwritable."""
        if self.rev is not None:
            # Only working directory may be edited 
            raise DAVError(HTTP_FORBIDDEN)

    
    def preventLocking(self):
        """Return True, to prevent locking.
        
        See preventLocking()
        """
        if self.rev is not None:
            # Only working directory may be edited 
            return True
        return False               

    
    def createEmptyResource(self, name):
        """Create and return an empty (length-0) resource as member of self.
        
        See DAVResource.createEmptyResource()
        """
        assert self.isCollection
        self._checkWriteAccess()               
    

    def createCollection(self, name):
        """Create a new collection as member of self.
        
        """
        assert self.isCollection
        self._checkWriteAccess()               


    def getContent(self):
        """Open content as a stream for reading.
         
        See DAVResource.getContent()
        """
        assert not self.isCollection
        d = self.fctx.data()
        return StringIO(d)
    

    def openResourceForWrite(self, contentType=None):
        """Open content as a stream for writing.
         
        """
        assert not self.isCollection
        self._checkWriteAccess()               

    
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
        ui = self.provider.ui  
        repo = self.provider.repo
        ui.pushbuffer()
        commands.remove(ui, repo, self.repoPath, cwd=self.provider.repoRoot)
        res = ui.popbuffer().strip()
        print res                     

    
    def handleCopy(self, destPath, depthInfinity):
        """Handle a COPY request natively.
        
        """
        return False               

    
    def copyMoveSingle(self, destPath, isMove):
        """Copy or move this resource to destPath (non-recursive).
        
        """
        self._checkWriteAccess()               



    def handleMove(self, destPath):
        """Handle a MOVE request natively.
        
        """
        return False               

    
    def supportRecursiveMove(self, destPath):
        """Return True, if moveRecursive() is available (see comments there)."""
        return True

    
    def moveRecursive(self, destPath):
        """Move this resource and members to destPath.
        
        """
        self._checkWriteAccess()               

         
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
        
        # Some commands (remove) seem to exect cwd set to the repo
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
        

    def _readTree(self, rev):
        """Return a dictionary containing all files under source control.

        files: 
            sorted list of all file paths under source control
        filestats:
            {filepath: status, ...}
        dirinfos: 
            {folderpath: (collectionlist, filelist), ...}
        
        ::
        
            {'dirinfos': {'': (['wsgidav',
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
             'filestats': {'.hgignore': 'C',
                           'README.txt': 'C',
                           'WsgiDAV.egg-info/PKG-INFO': 'I',
                           }
                           }
        """
        start_time = time.time()
        self.ui.pushbuffer()
        commands.status(self.ui, self.repo, 
                        modified=True, added=True, clean=True,
#                        all=True,
                        revision=rev)
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
            file = file 
            files.append(file)
            filestats[file] = stat
        files.sort()

        cache = {"files": files,
                 "dirinfos": dirinfos,
                 "filestats": filestats,
                 }
        util.status("_readTree(%s) took %s" % (rev, time.time() - start_time)
                    , var=cache
                    )
        return cache

        
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
        """Return _VirtualResource object for path.
        
        See DAVProvider.getResourceInst()
        """
        self._count_getResourceInst += 1

        # HG expects the resource paths without leading '/'
        repoPath = path.strip("/")
        rev = None
        cmd, rest = util.popPath(path)
        
        if cmd == "":
            return VirtualCollection(self, path, environ, 
                                     ["edit",
                                      "released", 
                                      "archive",
#                                      "tags", 
                                      ])
        elif cmd == "edit":
            repoPath = rest.strip("/")
            rev = None 
        elif cmd == "released":
            repoPath = rest.strip("/")
            rev = "tip"
        elif cmd == "archive":
            if rest == "/":
                loglist = self._getLog()
                members = [ str(l["local_id"])  for l in loglist ] 
                return VirtualCollection(self, path, environ, members)
            unid, rest = util.popPath(rest)
            rev = unid
            repoPath = rest.strip("/")
#        elif cmd == "tags":
#            if  rest == "/":
#                return VirtualCollection(self, path, environ, ["a", "b", "c"])
#            else:
#                raise
        else:
            return None
        
        # read mercurial repo into request cache
        caches = environ.setdefault("wsgidav.hg.cache", {})
        if caches.get(str(rev)) is None:
            cache = caches[str(rev)] = self._readTree(rev)
        else:
            cache = caches[str(rev)]
        
        if repoPath in cache["filestats"]:
            # It is a version controlled file
            return HgResource(self, path, False, environ, rev, repoPath)
        
        if repoPath in cache["dirinfos"]:
            # It is an existing folder
            return HgResource(self, path, True, environ, rev, repoPath)
        return None
