# (c) 2009-2011 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Implements the `LockManager` object that provides the locking functionality.

The LockManager requires a LockStorage object to implement persistence.  
Two alternative lock storage classes are defined in the lock_storage module:

- wsgidav.lock_storage.LockStorageDict
- wsgidav.lock_storage.LockStorageShelve


The lock data model is a dictionary with these fields:

    root:
        Resource URL.
    principal:
        Name of the authenticated user that created the lock.
    type:
        Must be 'write'.
    scope:
        Must be 'shared' or 'exclusive'.
    depth:
        Must be '0' or 'infinity'.
    owner:
        String identifying the owner.
    timeout:
        Seconds remaining until lock expiration.
        This value is passed to create() and refresh()
    expire:
        Converted timeout for persistence: expire = time() + timeout.
    token:
        Automatically generated unique token.

See `Developers info`_ for more information about the WsgiDAV architecture.

.. _`Developers info`: http://docs.wsgidav.googlecode.com/hg/html/develop.html  
"""
from pprint import pprint
from dav_error import DAVError, HTTP_LOCKED, PRECONDITION_CODE_LockConflict
from wsgidav.dav_error import DAVErrorCondition
import sys
import util
import random
import time
from rw_lock import ReadWriteLock

__docformat__ = "reStructuredText"

_logger = util.getModuleLogger(__name__)


#===============================================================================
# Tool functions
#===============================================================================

def generateLockToken():
    return "opaquelocktoken:" + str(hex(random.getrandbits(256)))


def normalizeLockRoot(path):
    # Normalize root: /foo/bar
    assert path
    if type(path) is unicode:
        path = path.encode("utf-8") 
    path = "/" + path.strip("/")
    return path


def isLockExpired(lock):
    expire = float(lock["expire"])
    return expire >= 0 and expire < time.time()


def lockString(lockDict):
    """Return readable rep."""
    if not lockDict:
        return "Lock: None"

    if lockDict["expire"] < 0:
        expire = "Infinite (%s)" % (lockDict["expire"])
    else:
        expire = "%s (in %s seconds)" % (util.getLogTime(lockDict["expire"]), 
                                          lockDict["expire"] - time.time())

    return "Lock(<%s..>, '%s', %s, %s, depth-%s, until %s" % (
        lockDict.get("token","?"*30)[18:22], # first 4 significant token characters
        lockDict.get("root"),
        lockDict.get("principal"),
        lockDict.get("scope"),
        lockDict.get("depth"),
        expire,
        )


def validateLock(lock):
    assert type(lock["root"]) is str
    assert lock["root"].startswith("/")
    assert lock["type"] == "write"
    assert lock["scope"] in ("shared", "exclusive")
    assert lock["depth"] in ("0", "infinity")
    assert type(lock["owner"]) is str
    # raises TypeError:
    timeout = float(lock["timeout"])
    assert timeout > 0 or timeout == -1, "timeout must be positive or -1"
    assert type(lock["principal"]) is str
    if "token" in lock:
        assert type(lock["token"]) is str

    
#===============================================================================
# LockManager
#===============================================================================
class LockManager(object):
    """
    Implements locking functionality using a custom storage layer.
    
    """
    LOCK_TIME_OUT_DEFAULT = 604800 # 1 week, in seconds

    def __init__(self, storage):
        """
        storage:
            LockManagerStorage object
        """
        assert hasattr(storage, "getLockList")
        self._lock = ReadWriteLock()
        self.storage = storage
        self.storage.open()


    def __del__(self):
        self.storage.close()


    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.storage)
    
    
    def _dump(self, msg="", out=None):
        if out is None:
            out = sys.stdout

        urlDict = {} # { <url>: [<tokenlist>] }
        ownerDict = {} # { <LOCKOWNER>: [<tokenlist>] }
        userDict = {} # { <LOCKUSER>: [<tokenlist>] }
        tokenDict = {} # { <token>: <LOCKURLS> } 
        
        print >>out, "%s: %s" % (self, msg)
        
        for lock in self.storage.getLockList("/", includeRoot=True, 
                                             includeChildren=True, 
                                             tokenOnly=False):
            tok = lock["token"]
            tokenDict[tok] = lockString(lock)
            userDict.setdefault(lock["principal"], []).append(tok)
            ownerDict.setdefault(lock["owner"], []).append(tok)
            urlDict.setdefault(lock["root"], []).append(tok)
            
#            assert ("URL2TOKEN:" + v["root"]) in self._dict, "Inconsistency: missing URL2TOKEN:%s" % v["root"]
#            assert v["token"] in self._dict["URL2TOKEN:" + v["root"]], "Inconsistency: missing token %s in URL2TOKEN:%s" % (v["token"], v["root"])
                
        print >>out, "Locks:" 
        pprint(tokenDict, indent=0, width=255)
        if tokenDict:
            print >>out, "Locks by URL:" 
            pprint(urlDict, indent=4, width=255, stream=out)
            print >>out, "Locks by principal:" 
            pprint(userDict, indent=4, width=255, stream=out)
            print >>out, "Locks by owner:" 
            pprint(ownerDict, indent=4, width=255, stream=out)


    def _generateLock(self, principal, 
                      locktype, lockscope, lockdepth, lockowner, path, timeout):
        """Acquire lock and return lockDict.

        principal
            Name of the principal.
        locktype
            Must be 'write'.
        lockscope
            Must be 'shared' or 'exclusive'.
        lockdepth
            Must be '0' or 'infinity'.
        lockowner
            String identifying the owner.
        path
            Resource URL.
        timeout
            Seconds to live
            
        This function does NOT check, if the new lock creates a conflict!
        """
        if timeout is None:
            timeout = LockManager.LOCK_TIME_OUT_DEFAULT
        elif timeout < 0:
            timeout = -1      
        
        lockDict = {"root": path,
                    "type": locktype,
                    "scope": lockscope,
                    "depth": lockdepth,
                    "owner": lockowner,
                    "timeout": timeout,
                    "principal": principal, 
                    }
        #
        self.storage.create(path, lockDict)
        return lockDict


    def acquire(self, url, locktype, lockscope, lockdepth, lockowner, timeout, 
                principal, tokenList):
        """Check for permissions and acquire a lock.
        
        On success return new lock dictionary.
        On error raise a DAVError with an embedded DAVErrorCondition.
        """
        url = normalizeLockRoot(url)
        self._lock.acquireWrite()
        try:
            # Raises DAVError on conflict:
            self._checkLockPermission(url, locktype, lockscope, lockdepth, tokenList, principal)
            return self._generateLock(principal, locktype, lockscope, lockdepth, lockowner, url, timeout)
        finally:
            self._lock.release()
        

    def refresh(self, token, timeout=None):
        """Set new timeout for lock, if existing and valid."""
        if timeout is None:
            timeout = LockManager.LOCK_TIME_OUT_DEFAULT
        return self.storage.refresh(token, timeout)


    def getLock(self, token, key=None):
        """Return lockDict, or None, if not found or invalid. 
        
        Side effect: if lock is expired, it will be purged and None is returned.

        key: 
            name of lock attribute that will be returned instead of a dictionary. 
        """
        assert key in (None, "type", "scope", "depth", "owner", "root", 
                       "timeout", "principal", "token")
        lock = self.storage.get(token)
        if key is None or lock is None:
            return lock
        return lock[key]


    def release(self, token):
        """Delete lock."""
        self.storage.delete(token)


    def isTokenLockedByUser(self, token, principal):
        """Return True, if <token> exists, is valid, and bound to <principal>."""   
        return self.getLock(token, "principal") == principal


#    def getUrlLockList(self, url, principal=None):
    def getUrlLockList(self, url):
        """Return list of lockDict, if <url> is protected by at least one direct, valid lock.
        
        Side effect: expired locks for this url are purged.
        """
        url = normalizeLockRoot(url)
        lockList = self.storage.getLockList(url, includeRoot=True, 
                                            includeChildren=False, 
                                            tokenOnly=False)
        return lockList


    def getIndirectUrlLockList(self, url, principal=None):
        """Return a list of valid lockDicts, that protect <path> directly or indirectly.
        
        If a principal is given, only locks owned by this principal are returned.
        Side effect: expired locks for this path and all parents are purged.
        """   
        url = normalizeLockRoot(url)
        lockList = []
        u = url 
        while u:
            ll = self.storage.getLockList(u, includeRoot=True, 
                                          includeChildren=False, 
                                          tokenOnly=False)
            for l in ll:
                if u != url and l["depth"] != "infinity":
                    continue  # We only consider parents with Depth: infinity
                # TODO: handle shared locks in some way?
#                if l["scope"] == "shared" and lockscope == "shared" and principal != l["principal"]:
#                    continue  # Only compatible with shared locks by other users 
                if principal is None or principal == l["principal"]:
                    lockList.append(l)
            u = util.getUriParent(u)
        return lockList


    def isUrlLocked(self, url):
        """Return True, if url is directly locked."""
        lockList = self.getUrlLockList(url)
        return len(lockList) > 0

        
    def isUrlLockedByToken(self, url, locktoken):
        """Check, if url (or any of it's parents) is locked by locktoken."""
        lockUrl = self.getLock(locktoken, "root")
        return lockUrl and util.isEqualOrChildUri(lockUrl, url) 


    def removeAllLocksFromUrl(self, url):
        self._lock.acquireWrite()
        try:
            lockList = self.getUrlLockList(url)
            for lock in lockList:
                self.release(lock["token"])
        finally:
            self._lock.release()               


    def _checkLockPermission(self, url, locktype, lockscope, lockdepth, 
                             tokenList, principal):
        """Check, if <principal> can lock <url>, otherwise raise an error.
        
        If locking <url> would create a conflict, DAVError(HTTP_LOCKED) is 
        raised. An embedded DAVErrorCondition contains the conflicting resource. 

        @see http://www.webdav.org/specs/rfc4918.html#lock-model

        - Parent locks WILL NOT be conflicting, if they are depth-0.
        - Exclusive depth-infinity parent locks WILL be conflicting, even if 
          they are owned by <principal>.
        - Child locks WILL NOT be conflicting, if we request a depth-0 lock.
        - Exclusive child locks WILL be conflicting, even if they are owned by 
          <principal>. (7.7)
        - It is not enough to check whether a lock is owned by <principal>, but 
          also the token must be passed with the request. (Because <principal> 
          may run two different applications on his client.)
        - <principal> cannot lock-exclusive, if he holds a parent shared-lock.
          (This would only make sense, if he was the only shared-lock holder.)
        - TODO: litmus tries to acquire a shared lock on one resource twice 
          (locks: 27 'double_sharedlock') and fails, when we return HTTP_LOCKED. 
          So we allow multi shared locks on a resource even for the same 
          principal.
        
        @param url: URL that shall be locked
        @param locktype: "write"
        @param lockscope: "shared"|"exclusive"
        @param lockdepth: "0"|"infinity"
        @param tokenList: list of lock tokens, that the user submitted in If: header
        @param principal: name of the principal requesting a lock 

        @return: None (or raise)
        """
        assert locktype == "write"
        assert lockscope in ("shared", "exclusive")
        assert lockdepth in ("0", "infinity")

        _logger.debug("checkLockPermission(%s, %s, %s, %s)" % (url, lockscope, lockdepth, principal))

        # Error precondition to collect conflicting URLs
        errcond = DAVErrorCondition(PRECONDITION_CODE_LockConflict)
        
        self._lock.acquireRead()
        try:
            # Check url and all parents for conflicting locks
            u = url 
            while u:
                ll = self.getUrlLockList(u)
                for l in ll:
                    _logger.debug("    check parent %s, %s" % (u, lockString(l)))
                    if u != url and l["depth"] != "infinity":
                        # We only consider parents with Depth: infinity
                        continue
                    elif l["scope"] == "shared" and lockscope == "shared":
                        # Only compatible with shared locks (even by same principal)
                        continue   
                    # Lock conflict
                    _logger.debug(" -> DENIED due to locked parent %s" % lockString(l))
                    errcond.add_href(l["root"])
                u = util.getUriParent(u)
    
            if lockdepth == "infinity":
                # Check child URLs for conflicting locks
                childLocks = self.storage.getLockList(url, 
                                                      includeRoot=False, 
                                                      includeChildren=True, 
                                                      tokenOnly=False)

                for l in childLocks:
                    assert util.isChildUri(url, l["root"])
#                    if util.isChildUri(url, l["root"]): 
                    _logger.debug(" -> DENIED due to locked child %s" % lockString(l))
                    errcond.add_href(l["root"])
        finally:
            self._lock.release()

        # If there were conflicts, raise HTTP_LOCKED for <url>, and pass
        # conflicting resource with 'no-conflicting-lock' precondition 
        if len(errcond.hrefs) > 0:              
            raise DAVError(HTTP_LOCKED, errcondition=errcond)
        return


    def checkWritePermission(self, url, depth, tokenList, principal):
        """Check, if <principal> can modify <url>, otherwise raise HTTP_LOCKED.
        
        If modifying <url> is prevented by a lock, DAVError(HTTP_LOCKED) is 
        raised. An embedded DAVErrorCondition contains the conflicting locks. 

        <url> may be modified by <principal>, if it is not currently locked
        directly or indirectly (i.e. by a locked parent).
        For depth-infinity operations, <url> also must not have locked children. 

        It is not enough to check whether a lock is owned by <principal>, but 
        also the token must be passed with the request. Because <principal> may 
        run two different applications.  

        See http://www.webdav.org/specs/rfc4918.html#lock-model
            http://www.webdav.org/specs/rfc4918.html#rfc.section.7.4

        TODO: verify assumptions:
        - Parent locks WILL NOT be conflicting, if they are depth-0.
        - Exclusive child locks WILL be conflicting, even if they are owned by <principal>.
        
        @param url: URL that shall be modified, created, moved, or deleted
        @param depth: "0"|"infinity"
        @param tokenList: list of lock tokens, that the principal submitted in If: header
        @param principal: name of the principal requesting a lock 

        @return: None or raise error
        """
        assert depth in ("0", "infinity")
        _logger.debug("checkWritePermission(%s, %s, %s, %s)" % (url, depth, tokenList, principal))

        # Error precondition to collect conflicting URLs
        errcond = DAVErrorCondition(PRECONDITION_CODE_LockConflict)

        self._lock.acquireRead()
        try:
            # Check url and all parents for conflicting locks
            u = url 
            while u:
                ll = self.getUrlLockList(u)
                _logger.debug("  checking %s" % u)
                for l in ll:
                    _logger.debug("     l=%s" % lockString(l))
                    if u != url and l["depth"] != "infinity":
                        # We only consider parents with Depth: inifinity
                        continue  
                    elif principal == l["principal"] and l["token"] in tokenList:
                        # User owns this lock 
                        continue  
                    else:
                        # Token is owned by principal, but not passed with lock list
                        _logger.debug(" -> DENIED due to locked parent %s" % lockString(l))
                        errcond.add_href(l["root"])
                u = util.getUriParent(u)
    
            if depth == "infinity":
                # Check child URLs for conflicting locks
                childLocks = self.storage.getLockList(url, 
                                                      includeRoot=False, 
                                                      includeChildren=True, 
                                                      tokenOnly=False)

                for l in childLocks:
                    assert util.isChildUri(url, l["root"])
#                    if util.isChildUri(url, l["root"]): 
                    _logger.debug(" -> DENIED due to locked child %s" % lockString(l))
                    errcond.add_href(l["root"])
        finally:
            self._lock.release()               

        # If there were conflicts, raise HTTP_LOCKED for <url>, and pass
        # conflicting resource with 'no-conflicting-lock' precondition 
        if len(errcond.hrefs) > 0:              
            raise DAVError(HTTP_LOCKED, errcondition=errcond)
        return


#===============================================================================
# test
#===============================================================================
def test():
#    l = ShelveLockManager("wsgidav-locks.shelve")
#    l._lazyOpen()
#    l._dump()
#    l.generateLock("martin", "", lockscope, lockdepth, lockowner, lockroot, timeout)
    pass

if __name__ == "__main__":
    test()
