# -*- coding: iso-8859-1 -*-

"""
lock_manager
============

:Author: Ho Chun Wei, fuzzybr80(at)gmail.com (author of original PyFileServer)
:Author: Martin Wendt, moogle(at)wwwendt.de 
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

A low performance lock manager implementation using shelve.

This module consists of a number of miscellaneous functions for the locks
features of WebDAV.

It also includes an implementation of a LockManager for
storage of locks. This implementation use
shelve for file storage. See request_server.py for details.

LockManagers must provide the methods as described in 
lockmanagerinterface_

See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
.. _lockmanagerinterface : interfaces/lockmanagerinterface.py
"""
from pprint import pprint
from dav_error import DAVError, \
    HTTP_LOCKED, PRECONDITION_CODE_LockConflict, HTTP_FORBIDDEN,\
    HTTP_PRECONDITION_FAILED
import sys
import util
import shelve
import threading
import random
import re
import time

__docformat__ = 'reStructuredText'

# TODO: comment's from Ian Bicking (2005)
#@@: Use of shelve means this is only really useful in a threaded environment.
#    And if you have just a single-process threaded environment, you could get
#    nearly the same effect with a dictionary of threading.Lock() objects.  Of course,
#    it would be better to move off shelve anyway, probably to a system with
#    a directory of per-file locks, using the file locking primitives (which,
#    sadly, are not quite portable).
# @@: It would probably be easy to store the properties as pickle objects
# in a parallel directory structure to the files you are describing.
# Pickle is expedient, but later you could use something more readable
# (pickles aren't particularly readable)


class LockManager(object):
    """
    A low performance lock manager implementation using shelve.
    """
    LOCK_TIME_OUT_DEFAULT = 604800 # 1 week, in seconds

    # any numofsecs above the following limit is regarded as infinite
    MAX_FINITE_TIMEOUT_LIMIT = 10*365*24*60*60  #approx 10 years

    def __init__(self, persiststore):
        self._loaded = False      
        self._dict = None
        self._init_lock = threading.RLock()
        self._write_lock = threading.RLock()
        self._persiststorepath = persiststore
        self._verbose = 2


    def _performInitialization(self):
        self._init_lock.acquire(True)
        try:
            if self._loaded:       # test again within the critical section
#                self._lock.release()
                return True
            self._dict = shelve.open(self._persiststorepath)
            self._loaded = True
            self._cleanup()
            if self._verbose >= 2:
                self._dump("After shelve.open()")
        finally:
            self._init_lock.release()         


    def __repr__(self):
        return repr(self._dict)


    def __del__(self):
        if self._loaded:
            self._dict.close()   


    def _cleanup(self):
        """TODO: Purge expired locks."""
        pass

    
    def _log(self, msg):
        if self._verbose >= 2:
            util.log(msg)


    def _dump(self, msg="", out=None):
        if not self._loaded:
            self._performInitialization()
            if not out and self._verbose >= 2:
                return # Already dumped on init
        if out is None:
            out = sys.stdout

        urlDict = {} # { <url>: [<tokenlist>] }
#        urlMapDict = {} # { <url>: [<tokenlist>] }
        ownerDict = {} # { <LOCKOWNER>: [<tokenlist>] }
        userDict = {} # { <LOCKUSER>: [<tokenlist>] }
        tokenDict = {} # { <token>: <LOCKURLS> } 
        def _splitToken(key):
            return key.split(":", 1)[1]
        
        print >>out, "LockManager(%s): %s" % (self._persiststorepath, msg)
        
        for k, v in self._dict.items():
            if k.startswith("URL2TOKEN:"):
                print >>out, "    ", k, v

        for k, v in self._dict.items():
            tok = _splitToken(k)
            if k.startswith("URL2TOKEN:"):
                continue
            v = v.copy()
            if v["timeout"] < 0:
                v["timeout"] = "Infinite (%s)" % (v["timeout"])
            else:
                v["timeout"] = "%s (%s)" % (util.getRfc1123Time(v["timeout"]), v["timeout"])
            tokenDict[k] = v
            
            userDict.setdefault(v["principal"], []).append(tok)
            ownerDict.setdefault(v["owner"], []).append(tok)
            urlDict.setdefault(v["root"], []).append(tok)
            
            assert ("URL2TOKEN:" + v["root"]) in self._dict, "Inconsistency: missing URL2TOKEN:%s" % v["root"]
            assert v["token"] in self._dict["URL2TOKEN:" + v["root"]], "Inconsistency: missing token %s in URL2TOKEN:%s" % (v["token"], v["root"])
                
        print >>out, "Locks:" 
        pprint(tokenDict, indent=0, width=255)
        if tokenDict:
            print >>out, "Locks by URL:" 
            pprint(urlDict, indent=4, width=255, stream=out)
            print >>out, "Locks by principal:" 
            pprint(userDict, indent=4, width=255, stream=out)
            print >>out, "Locks by owner:" 
            pprint(ownerDict, indent=4, width=255, stream=out)


    def generateLock(self, username, locktype, lockscope, lockdepth, lockowner, lockroot, timeout):
        """Acquire lock and return lockDict.
        
        This function does NOT check, if the new lock creates a conflict!
        """
#        self._log("generateLock(%s, %s, %s, %s, %s, %s, %s)" % (username, lockscope, lockdepth, lockowner, lockroot, timeout))
        assert locktype == "write"
        assert lockscope in ("shared", "exclusive")
        assert lockdepth in ("0", "infinity")

        if timeout is None:
            timeout = LockManager.LOCK_TIME_OUT_DEFAULT
        elif timeout < 0:
            timeout = -1      
        else:
            timeout = time.time() + timeout
        
        randtoken = "opaquelocktoken:" + str(hex(random.getrandbits(256)))
        while randtoken in self._dict:
            randtoken = "opaquelocktoken:" + str(hex(random.getrandbits(256)))

        lockDict = {"root": lockroot,
                    "type": locktype,
                    "scope": lockscope,
                    "depth": lockdepth,
                    "owner": lockowner,
                    "timeout": timeout,
                    "principal": username, 
                    "token": randtoken,
                    }
        self._log("generateLock %s" % _lockString(lockDict))

        self._write_lock.acquire(True)
        try:
            if not self._loaded:
                self._performInitialization()
            #     
            self._dict[randtoken] = lockDict
            
            key = "URL2TOKEN:%s" % lockroot
            if not key in self._dict:
                self._dict[key] = [ randtoken ]
            else:
                # Note: shelve dictionary returns copies, so we must reassign values: 
                tokList = self._dict[key] 
                tokList.append(randtoken)
                self._dict[key] = tokList

            self._dict.sync()
#            if self._verbose:
#                self._dump("After generateLock(%s)" % lockroot)
            return lockDict
        finally:
            self._write_lock.release()


    def getCheckedLock(self, resourceAL, 
                       lockroot, locktype, lockscope, lockdepth, lockowner, timeout, 
                       user, tokenList):
        """Check for permissions and acquire a lock.
        
        On success, return length-1 list: [ {newLockDict, None} ]
        On error return a list of conflicts (@see self.checkLockPermission)
        """
        self._write_lock.acquire(True)
        try:
            if not self._loaded:
                self._performInitialization()
            conflictList = self.checkLockPermission(resourceAL, lockroot, locktype, lockscope, lockdepth, tokenList, user)
            if len(conflictList) > 0:
                return conflictList
            lockDict = self.generateLock(user, locktype, lockscope, lockdepth, lockowner, lockroot, timeout)
            return [ (lockDict, None) ]
        finally:
            self._write_lock.release()
        

    def refreshLock(self, locktoken, timeout=None):
        """Set new timeout for lock, if existing and valid."""
        if timeout is None:
            timeout = LockManager.LOCK_TIME_OUT_DEFAULT  
        self._write_lock.acquire(True)
        try:
            lock = self.getLock(locktoken)
            self._log("refreshLock %s" % _lockString(lock))
            if lock:
                lock["timeout"] = time.time() + timeout
                self._dict[locktoken] = lock 
                self._dict.sync()
            return lock
        finally:
            self._write_lock.release()


    def getLock(self, locktoken, key=None):
        """Return lockDict, or None, if not found or invalid. 
        
        @param key: name of lock attribute that will be returned instead of a dictionary. 
        Side effect: if lock is expired, it will be purged and None is returned.
        """
        assert key in (None, "type", "scope", "depth", "owner", "root", "timeout", "principal", "token")
        if not self._loaded:
            self._performInitialization()
        lock = self._dict.get(locktoken)
        if lock is None: # Lock not found: purge dangling URL2TOKEN entries
            self.deleteLock(locktoken)      
            return None
        timeout = lock["timeout"]
        if timeout >= 0 and timeout < time.time():
            self.deleteLock(locktoken)   
            return None
        if key is None:
            return lock
        else:
            return lock[key]


    def deleteLock(self, locktoken):
        """Delete lock and url2token mapping."""
        self._write_lock.acquire(True)      
        try:
            if not self._loaded:
                self._performInitialization()
            lock = self._dict.get(locktoken)
            self._log("deleteLock %s" % _lockString(lock))
            if lock is None:
                return False
            # Remove url to lock mapping
            key = "URL2TOKEN:%s" % lock.get("root")
            if key in self._dict:
#                self._log("    delete token %s from url %s" % (locktoken, lock.get("root")))
                tokList = self._dict[key]
                if len(tokList) > 1:
                    # Note: shelve dictionary returns copies, so we must reassign values: 
                    tokList.remove(locktoken)
                    self._dict[key] = tokList
                else:
                    del self._dict[key]     
            # Remove the lock
            del self._dict[locktoken]       

#            if self._verbose:
#                self._dump("After deleteLock(%s)" % locktoken)
            self._dict.sync()
        finally:
            self._write_lock.release()


    def isTokenLockedByUser(self, token, username):
        """Return True, if <token> exists, is valid, and bound to <username>."""   
        return self.getLock(token, "principal") == username


    def getUrlLockList(self, url, username=None):
        """Return list of lockDict, if <url> is protected by at least one direct, valid lock.
        
        Side effect: expired locks for this url are purged.
        """   
        if not self._loaded:
            self._performInitialization()
        key = "URL2TOKEN:%s" % url
        lockList = []
        for tok in self._dict.get(key, []):
            lock = self.getLock(tok)
            if lock and (username is None or username == lock["principal"]):
                lockList.append(lock)
        return lockList


    def getIndirectUrlLockList(self, url, username=None):
        """Return a list of valid lockDicts, that protect <url> directly or indirectly.
        
        If a username is given, only locks owned by this principal are returned.
        Side effect: expired locks for this url and all parents are purged.
        """   
        lockList = []
        u = url 
        while u:
            # TODO: check, if expired
            ll = self.getUrlLockList(u)
            for l in ll:
                if u != url and l["depth"] != "infinity":
                    continue  # We only consider parents with Depth: inifinity
                # TODO: handle shared locks in some way?
#                if l["scope"] == "shared" and lockscope == "shared" and username != l["principal"]:
#                    continue  # Only compatible with shared locks by other users 
                if username == l["principal"]:
                    lockList.append(l)
            u = util.getUriParent(u)
#        self._log("getIndirectUrlLockList(%s, %s): %s" % (url, username, lockList))
        return lockList


    def isUrlLocked(self, url):
        """Return True, if url is directly locked."""
        lockList = self.getUrlLockList(url)
        return len(lockList) > 0

        
    def getUrlLockScope(self, url):
        lockList = self.getUrlLockList(url)
        # either one exclusive lock, or many shared locks - first lock will give lock scope
        if len(lockList) > 0:
            return lockList[0].get("scope")
        return None 


    def isUrlLockedByToken(self, url, locktoken):
        """Check, if url is directly or indirectly locked by locktoken."""
        lockUrl = self.getLock(locktoken, "root")
        # FIXME: make sure '/a/b' doesn't match '/a/bb'
        return ( lockUrl and url.startswith(lockUrl) )


    def removeAllLocksFromUrl(self, url):
        self._write_lock.acquire(True)
        try:
            lockList = self.getUrlLockList(url)
            for lock in lockList:
                self.deleteLock(lock["token"])
        finally:
            self._write_lock.release()               


    def checkLockPermission(self, resourceAL, lockroot, locktype, lockscope, lockdepth, tokenList, user):
        """Check, if <user> can lock <lockroot>, otherwise return a list of conflicting locks.
        
        An empty list is returned, if the lock would be granted.
        Otherwise a list of 2-tuples (lockDict, DAVError) is returned.

        If <lockroot> is already locked directly or indirectly (i.e. by a 
        locked parent), this lock is returned together with HTTP_LOCKED.
        
        Otherwise (and if depth=infinity) we check all children for conflicting 
        locks, and return them togeher with HTTP_PRECONDITION_FAILED. 

        @see http://www.webdav.org/specs/rfc4918.html#lock-model

        TODO: verify assumptions:
        - Parent locks WILL NOT be conflicting, if they are depth-0.
        - Exclusive depth-infinity parent locks WILL be conflicting, even if they 
          are owned by <user>.
        - Exclusive child locks WILL be conflicting, even if they are owned by <user>. (7.7)
        - It is not enough to check whether a lock is owned by <user>, but also 
          the token must be passed with the request. (Because <user> may run two 
          different applications on his client.)
        - TODO: Can <user> lock-exclusive, if she holds a parent shared-lock?
          (currently NO; it would only make sense, if he was the only shared-lock holder)
        - TODO: litmus tries to acquire a shared lock one resource twice (locks: 27 'double_sharedlock')
          and fails, when we return HTTP_LOCKED. So we allow multi shared locks 
          on a resource even for the same principal

        
        @param lockroot: URL that shall be locked
        @param locktype: "write"
        @param lockscope: "shared"|"exclusive"
        @param lockdepth: "0"|"infinity"
        @param tokenList: list of lock tokens, that the user submitted in If: header
        @param user: name of the principal requesting a lock 

        @return: [] or a list of 2-tuples (lockDict, DAVError)
        """

        # TODO: this should be resourceAL.checkLockPermission(lockroot, locktype, lockscope, lockdepth, user)
         
        assert locktype == "write"
        assert lockscope in ("shared", "exclusive")
        assert lockdepth in ("0", "infinity")

        self._log("checkLockPermission(%s, %s, %s, %s)" % (lockroot, lockscope, lockdepth, user))

        conflictLockList = []

        # Check lockroot and all parents for conflicting locks
        u = lockroot 
        while u:
            # TODO: check, if expired
            ll = self.getUrlLockList(u)
            for l in ll:
                self._log("    check parent %s, %s" % (u, l))
                if u != lockroot and l["depth"] != "infinity":
                    continue  # We only consider parents with Depth: infinity
                elif l["scope"] == "shared" and lockscope == "shared": # and user != l["principal"]:
                    continue  # Only compatible with shared locks (even by same principal) 
                # Return first lock as a list (in a sane system there can be max. one anyway)
                self._log(" -> DENIED due to locked parent %s" % _lockString(l))
                return [ (l, DAVError(HTTP_LOCKED)) ]
            # TODO: this also will check the realm level itself
            u = util.getUriParent(u)

        if lockdepth == "0":
            return conflictLockList
        
        # TODO: we could exit also, if lockroot is not a collection or assert that depth=0 in this case
        
        # Check child urls for conflicting locks
        prefix = "URL2TOKEN:" + lockroot   
        if not prefix.endswith("/"):
            prefix += "/"  

        for u, ll in self._dict.items():
            if not u.startswith(prefix): 
                continue  # Not a child
            # TODO: check, if expired
            
            for l in ll:
                lockDict = self.getLock(l)
#                self._log("    check child %s, %s" % (u, l))
                # TODO: no-conflicting-lock can pass a list of href elements too:
                conflictLockList.append((lockDict, 
                                         DAVError(HTTP_PRECONDITION_FAILED,
                                                  preconditionCode=PRECONDITION_CODE_LockConflict)
                                         ))
                self._log(" -> DENIED due to locked child %s" % _lockString(lockDict))
        return conflictLockList


    def checkAccessPermission(self, resourceAL, url, tokenList, accesstype, accessdepth, user):
        """Check, if <user> can modify <url>, otherwise return a list of conflicting locks.
        
        If an empty list is returned, the write access is allowed (concerning locks).

        <url> may be modified by <user>, if it is not currently locked
        directly or indirectly (i.e. by a locked parent).
        For accessdepth-infinity operations, <url> also must not have locked children. 

        It is not enough to check whether a lock is owned by <user>, but also the 
        token must be passed with the request. Because <user> may run two 
        different applications.  

        @see http://www.webdav.org/specs/rfc4918.html#lock-model

        TODO: verify assumptions:
        - Parent locks WILL NOT be conflicting, if they are depth-0.
        - Exclusive child locks WILL be conflicting, even if they are owned by <user>.
        - TODO: Can <user> lock-exclusive, if she holds a parent shared-lock?
        
        @param url: URL that shall be modified, created, moved, or deleted
        @param accesstype: "write"
        @param accessdepth: "0"|"infinity"
        @param tokenList: list of lock tokens, that the user submitted in If: header
        @param user: name of the principal requesting a lock 

        @return: [] or a list of 2-tuples (lockDict, DAVError)
        """
        # TODO: this should be resourceAL.checkWritePermission(url, locktype, lockscope, lockdepth, username)
         
        assert accesstype == "write"
        assert accessdepth in ("0", "infinity")
        conflictLockList = []
        self._log("checkAccessPermission(%s, %s, %s, %s)" % (url, tokenList, accessdepth, user))

        # Check url and all parents for conflicting locks
        u = url 
        while u:
            # TODO: check, if expired
            ll = self.getUrlLockList(u)
#            self._log("  checking %s" % u)
            for l in ll:
                self._log("     l=%s" % l)
                if u != url and l["depth"] != "infinity":
                    continue  # We only consider parents with Depth: inifinity
                elif user == l["principal"] and l["token"] in tokenList:
                    continue  # User owns this lock 
                elif l["token"] in tokenList:
                    # Token is owned by another user
                    conflictLockList.append((l, DAVError(HTTP_FORBIDDEN)))
                    self._log(" -> DENIED due to locked parent %s" % _lockString(l))
                else:
                    # Token is owned by user, but not passed with lock list
                    # TODO: no-conflicting-lock can pass a list of href elements too:
                    conflictLockList.append((l, DAVError(HTTP_LOCKED,
                                                         preconditionCode=PRECONDITION_CODE_LockConflict)))
                    self._log(" -> DENIED due to locked parent %s" % _lockString(l))
            u = util.getUriParent(u)

        if accessdepth == "0":
            # We only request flat access, so no need to check for child locks 
            return conflictLockList
        
        # TODO: we could exit also, if <url> is not a collection
        
        # Check child urls for conflicting locks
        prefix = "URL2TOKEN:" + url   
        if not prefix.endswith("/"):
            prefix += "/"  

        for u, ll in self._dict.items():
            if not u.startswith(prefix): 
                continue  # Not a child
            # TODO: check, if expired
            
            for tok in ll:
                l = self.getLock(tok)
                # TODO: no-conflicting-lock can pass a list of href elements too:
                conflictLockList.append((l,
                                         DAVError(HTTP_LOCKED,
                                                  preconditionCode=PRECONDITION_CODE_LockConflict)
                                         ))
                self._log(" -> DENIED due to locked child %s" % _lockString(l))
         
        return conflictLockList



reSecondsReader = re.compile(r'second\-([0-9]+)', re.I)

def readTimeoutValueHeader(timeoutvalue):
    """Return -1 if infinite, else return numofsecs."""
    timeoutsecs = 0
    timeoutvaluelist = timeoutvalue.split(',')   
    for timeoutspec in timeoutvaluelist:
        timeoutspec = timeoutspec.strip()
        if timeoutspec.lower() == 'infinite':
            return -1
        else:
            listSR = reSecondsReader.findall(timeoutspec)
            for secs in listSR:
                timeoutsecs = long(secs)
                if timeoutsecs > LockManager.MAX_FINITE_TIMEOUT_LIMIT:
                    return -1          
                if timeoutsecs != 0:
                    return timeoutsecs
    return None


def _lockString(lockDict):
    """Return readable rep."""
    if not lockDict:
        lockDict = {}
    return "Lock(<%s..>, '%s', %s, %s: '%s'" % (
        lockDict.get("token","?"*30)[18:22], # first 4 significant token characters
        lockDict.get("principal"),
        lockDict.get("scope"),
        lockDict.get("depth"),
        lockDict.get("root"),
        )


def test():
    l = LockManager("wsgidav-locks.shelve")
    l._performInitialization()
    l._dump()
#    l.generateLock("martin", "", lockscope, lockdepth, lockowner, lockroot, timeout)


if __name__ == "__main__":
    test()
