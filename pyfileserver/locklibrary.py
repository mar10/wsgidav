"""
locklibrary
===========

:Module: pyfileserver.locklibrary
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com
:Project: PyFileServer, http://pyfilesync.berlios.de/
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

This module consists of a number of miscellaneous functions for the locks
features of webDAV.

It also includes an implementation of a LockManager for
storage of locks. This implementation use
shelve for file storage. See extrequestserver.py for details.

LockManagers must provide the methods as described in 
lockmanagerinterface_

.. _lockmanagerinterface : interfaces/lockmanagerinterface.py


Classes::
   
   class LockManager(object)

Misc methods::

   checkLocksToAdd(lm, displaypath)
   readTimeoutValueHeader(timeoutvalue)

Interface methods::

   generateLock(lm, username, locktype='write', lockscope='exclusive', lockdepth='infinite', lockowner='', lockheadurl='', timeout=None)
   deleteLock(lm, locktoken)
   refreshLock(lm, locktoken, timeout=None)
   addUrlToLock(lm, url, locktoken)
   getLockProperty(lm, locktoken, lockproperty)
   removeAllLocksFromUrl(lm, url)
   isTokenLockedByUser(lm, locktoken, username)
   isUrlLocked(lm, url)
   getUrlLockScope(lm, url)
   isUrlLockedByToken(lm, url, locktoken)
   getTokenListForUrl(lm, url)
   getTokenListForUrlByUser(lm, url, username)

*author note*: More documentation here required

This module is specific to the PyFileServer application.

"""

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


__docformat__ = 'reStructuredText'

import os
import shelve
import threading
import stat
import mimetypes
import random
import re
import time

import httpdatehelper
import websupportfuncs
from processrequesterrorhandler import HTTPRequestException
import processrequesterrorhandler

"""
A low performance lock library using shelve
"""

class LockManager(object):
    def __init__(self, persiststore):
        self.LOCK_TIME_OUT_DEFAULT = 604800 # 1 week, in seconds
        self._loaded = False      
        self._dict = None
        self._init_lock = threading.RLock()
        self._write_lock = threading.RLock()
        self._persiststorepath = persiststore

    def _performInitialization(self):
        self._init_lock.acquire(True)
        try:
            if self._loaded:       # test again within the critical section
                self._lock.release()
                return True
            self._dict = shelve.open(self._persiststorepath)
        finally:
            self._init_lock.release()         

    def __repr__(self):
        return repr(self._dict)

    def __del__(self):
        if self._loaded:
            self._dict.close()   

    def generateLock(self, username, locktype, lockscope, lockdepth, lockowner, lockheadurl, timeout):
        if timeout is None:
            timeout = self.LOCK_TIME_OUT_DEFAULT
        self._write_lock.acquire(True)
        try:
            if not self._loaded:
                self._performInitialization()
            randtoken = "opaquelocktoken:" + str(hex(random.getrandbits(256)))
            while ('LOCKTIME:'+ randtoken) in self._dict:
                randtoken = "opaquelocktoken:" + str(hex(random.getrandbits(256)))
            if timeout < 0:
                self._dict['LOCKTIME:'+ randtoken] = -1      
            else:
                self._dict['LOCKTIME:'+ randtoken] = time.time() + timeout
            self._dict['LOCKUSER:'+ randtoken] = username
            self._dict['LOCKTYPE:'+ randtoken] = locktype
            self._dict['LOCKSCOPE:'+ randtoken] = lockscope
            self._dict['LOCKDEPTH:'+ randtoken] = lockdepth
            self._dict['LOCKOWNER:'+randtoken] = lockowner
            self._dict['LOCKHEADURL:'+randtoken] = lockheadurl
            return randtoken
        finally:
            self._dict.sync()
            self._write_lock.release()

    def _validateLock(self, locktoken):
        if not self._loaded:
            self._performInitialization()
        if ('LOCKTIME:'+ locktoken) in self._dict:
            if self._dict['LOCKTIME:'+ locktoken] > 0 and self._dict['LOCKTIME:'+ locktoken] < time.time():
                self.deleteLock(locktoken)   
                return False
        else:
            self.deleteLock(locktoken)      
            return False
        return True

    def deleteLock(self, locktoken):
        self._write_lock.acquire(True)      
        try:
            if not self._loaded:
                self._performInitialization()
            if ('LOCKTIME:'+ locktoken) in self._dict:
                del self._dict['LOCKTIME:'+ locktoken]       
            if ('LOCKUSER:'+ locktoken) in self._dict:
                del self._dict['LOCKUSER:'+ locktoken]       
            if ('LOCKTYPE:'+ locktoken) in self._dict:
                del self._dict['LOCKTYPE:'+ locktoken]
            if ('LOCKSCOPE:'+ locktoken) in self._dict:
                del self._dict['LOCKSCOPE:'+ locktoken]
            if ('LOCKDEPTH:'+ locktoken) in self._dict:
                del self._dict['LOCKDEPTH:'+ locktoken]
            if ('LOCKOWNER:'+ locktoken) in self._dict:
                del self._dict['LOCKOWNER:'+ locktoken]
            if ('LOCKHEADURL:'+ locktoken) in self._dict:
                del self._dict['LOCKHEADURL:'+ locktoken]
            if ('LOCKURLS:'+locktoken) in self._dict:       
                for urllocked in self._dict['LOCKURLS:'+locktoken]:
                    if ('URLLOCK:' + urllocked) in self._dict:
                        urllockdict = self._dict['URLLOCK:' + urllocked]
                        if locktoken in urllockdict:
                            del urllockdict[locktoken]
                        if len(urllockdict) == 0:
                            del self._dict['URLLOCK:' + urllocked]
                        else:
                            self._dict['URLLOCK:' + urllocked] = urllockdict 
                del self._dict['LOCKURLS:'+locktoken]  
        finally:
            self._dict.sync()
            self._write_lock.release()

    def isTokenLockedByUser(self, locktoken, username):
        if not self._loaded:
            self._performInitialization()
        if self._validateLock(locktoken):
            return ('LOCKUSER:'+locktoken) in self._dict      
        else:
            return False


    def isUrlLocked(self, url):   
        if not self._loaded:
            self._performInitialization()
        if ('URLLOCK:' + url) in self._dict:
            urllockdictcopy = self._dict['URLLOCK:' + url].copy()  # use read-only copy here, since validation can delete the dictionary
            for urllocktoken in urllockdictcopy:
                if self._validateLock(urllocktoken):
                    return True
            return False
        else:
            return False

    def getUrlLockScope(self, url):
        if not self._loaded:
            self._performInitialization()
        if ('URLLOCK:' + url) in self._dict:
            urllockdictcopy = self._dict['URLLOCK:' + url].copy()  # use read-only copy here, since validation can delete the dictionary
            for urllocktoken in urllockdictcopy:
                if self._validateLock(urllocktoken):
                    if ('LOCKSCOPE:'+ urllocktoken) in self._dict: # either one exclusive lock, or many shared locks - first lock will give lock scope
                        return self._dict['LOCKSCOPE:'+ urllocktoken]
                    return "unknown" # not usually reached
            return None
        else:
            return None

    # lockproperty one of 'LOCKSCOPE', 'LOCKUSER', 'LOCKTYPE', 'LOCKDEPTH', 'LOCKTIME', 'LOCKOWNER' note case
    def getLockProperty(self, locktoken, lockproperty):
        if (lockproperty + ":" + locktoken) in self._dict: 
            lockpropvalue = self._dict[lockproperty + ":" + locktoken]         
            if lockproperty == 'LOCKTIME':
                if lockpropvalue < 0:
                    return 'Infinite'
                else:
                    return 'Second-' + str(long(lockpropvalue - time.time())) 
            return lockpropvalue
        else:
            return ''

    def isUrlLockedByToken(self, url, locktoken):   
        if not self._loaded:
            self._performInitialization()
        if ('URLLOCK:' + url) in self._dict:
            urllockdictcopy = self._dict['URLLOCK:' + url].copy()  # use read-only copy here, since validation can delete the dictionary
            for urllocktoken in urllockdictcopy:
                if self._validateLock(urllocktoken) and urllocktoken == locktoken:
                    return True
            return False
        else:
            return False

    def getTokenListForUrl(self, url):
        listReturn = []
        if not self._loaded:
            self._performInitialization()
        if ('URLLOCK:' + url) in self._dict:
            urllockdictcopy = self._dict['URLLOCK:' + url].copy()  # use read-only copy here, since validation can delete the dictionary
            for urllocktoken in urllockdictcopy:
                if self._validateLock(urllocktoken):
                    listReturn.append(urllocktoken)
        return listReturn

    def getTokenListForUrlByUser(self, url, username):
        listReturn = []
        if not self._loaded:
            self._performInitialization()
        if ('URLLOCK:' + url) in self._dict:
            urllockdictcopy = self._dict['URLLOCK:' + url].copy()  # use read-only copy here, since validation can delete the dictionary
            for urllocktoken in urllockdictcopy:
                if self.isTokenLockedByUser(urllocktoken, username):
                    listReturn.append(urllocktoken)
        return listReturn


    def addUrlToLock(self, url, locktoken):
        self._write_lock.acquire(True)
        try:
            if not self._loaded:
                self._performInitialization()
            if self._validateLock(locktoken):            
                if ('URLLOCK:' + url) in self._dict:
                    urllockdict = self._dict['URLLOCK:' + url]      
                    urllockdict[locktoken] = locktoken
                    self._dict['URLLOCK:' + url] = urllockdict
                else:
                    self._dict['URLLOCK:' + url] = dict([(locktoken ,locktoken )])

                if ('LOCKURLS:'+locktoken) in self._dict:  
                    urllockdict = self._dict['LOCKURLS:'+locktoken]
                    urllockdict[url] = url
                    self._dict['LOCKURLS:'+locktoken] = urllockdict
                else:
                    self._dict['LOCKURLS:'+locktoken] = dict([(url, url)])
                return True
            else:
                return False
        finally:
            self._dict.sync()
            self._write_lock.release()               

    def removeAllLocksFromUrl(self, url):
        self._write_lock.acquire(True)
        try:
            if not self._loaded:
                self._performInitialization()
            if ('URLLOCK:' + url) in self._dict:
                urllockdictcopy = self._dict['URLLOCK:' + url].copy()  # use read-only copy here, since validation can delete the dictionary
                for locktoken in urllockdictcopy:
                    if self._validateLock(locktoken):
                        if ('LOCKURLS:'+locktoken) in self._dict:       
                            urllockdict = self._dict['LOCKURLS:'+locktoken]
                            if url in urllockdict:
                                del urllockdict[url]
                                if len(urllockdict) == 0:
                                    self.deleteLock(locktoken)
                                else:                
                                    self._dict['LOCKURLS:'+locktoken] = urllockdict
                if ('URLLOCK:' + url) in self._dict:  # check again, deleteLock might have removed it
                    del self._dict['URLLOCK:' + url]      
        finally:
            self._dict.sync()
            self._write_lock.release()               

    def refreshLock(self, locktoken, timeout):
        if timeout is None:
            timeout = self.LOCK_TIME_OUT_DEFAULT      
        self._write_lock.acquire(True)
        try:
            if not self._loaded:
                self._performInitialization()
            if ('LOCK:'+ locktoken) in self._dict:
                self._dict['LOCK:'+ locktoken] = time.time() + timeout
                return True
            return False
        finally:
            self._dict.sync()
            self._write_lock.release()


def checkLocksToAdd(lm, displaypath):
    parentdisplaypath = websupportfuncs.getLevelUpURL(displaypath)
    if lm.isUrlLocked(parentdisplaypath) != None:
        locklist = lm.getTokenListForUrl(parentdisplaypath)
        for locklisttoken in locklist:
            if lm.getLockProperty(locklisttoken, 'LOCKDEPTH') == 'infinity':
                if not lm.isUrlLockedByToken(displaypath, locklisttoken):
                    lm.addUrlToLock(displaypath, locklisttoken)

# returns -1 if infinite, else return numofsecs
# any numofsecs above the following limit is regarded as infinite
MAX_FINITE_TIMEOUT_LIMIT = 10*365*24*60*60  #approx 10 years

reSecondsReader = re.compile(r'second\-([0-9]+)', re.I)

def readTimeoutValueHeader(timeoutvalue):
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
                if timeoutsecs > MAX_FINITE_TIMEOUT_LIMIT:
                    return -1          
                if timeoutsecs != 0:
                    return timeoutsecs
    return None



def generateLock(lm, username, locktype='write', lockscope='exclusive', lockdepth='infinite', lockowner='', lockheadurl='', timeout=None):
    return lm.generateLock(username, locktype, lockscope, lockdepth, lockowner, lockheadurl, timeout)

def deleteLock(lm, locktoken):
    return lm.deleteLock(locktoken)
    
def refreshLock(lm, locktoken, timeout=None):
    return lm.refreshLock(locktoken, timeout)

def addUrlToLock(lm, url, locktoken):
    return lm.addUrlToLock(url, locktoken)

def getLockProperty(lm, locktoken, lockproperty):
    return lm.getLockProperty(locktoken, lockproperty)

def removeAllLocksFromUrl(lm, url):
    return lm.removeAllLocksFromUrl(url)
        
def isTokenLockedByUser(lm, locktoken, username):
    return lm.isTokenLockedByUser(locktoken, username)

def isUrlLocked(lm, url):
    return lm.isUrlLocked(url)

def getUrlLockScope(lm, url):
    return lm.getUrlLockScope(url)

def isUrlLockedByToken(lm, url, locktoken):
    return lm.isUrlLockedByToken(url, locktoken)

def getTokenListForUrl(lm, url):
    return lm.getTokenListForUrl(url)

def getTokenListForUrlByUser(lm, url, username):
    return lm.getTokenListForUrlByUser(url, username)
