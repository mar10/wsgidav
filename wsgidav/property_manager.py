"""
property_manager
================

:Author: Ho Chun Wei, fuzzybr80(at)gmail.com (author of original PyFileServer)
:Author: Martin Wendt, moogle(at)wwwendt.de 
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

A low performance property manager implementation using shelve.

This module consists of a number of miscellaneous functions for the dead 
properties features of WebDAV.

It also includes an implementation of a PropertyManager for
storage of dead properties. This implementation use
shelve for file storage.  See request_server.py for details.

PropertyManagers must provide the methods as described in 
propertymanagerinterface_

See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
.. _propertymanagerinterface : interfaces/propertymanagerinterface.py



Properties and WsgiDAV
----------------------
Properties of a resource refers to the attributes of the resource. A property
is referenced by the property name and the property namespace. We usually
refer to the property as ``{property namespace}property name`` 

Properties of resources as defined in WebDAV falls under three categories:

Live properties
   These properties are attributes actively maintained by the server, such as 
   file size, or read permissions. if you are sharing a database record as a 
   resource, for example, the attributes of the record could become the live 
   properties of the resource.

   The webdav specification defines the following properties that could be
   live properties (refer to webdav specification for details):
   {DAV:}creationdate
   {DAV:}displayname
   {DAV:}getcontentlanguage
   {DAV:}getcontentlength
   {DAV:}getcontenttype
   {DAV:}getetag
   {DAV:}getlastmodified
   {DAV:}resourcetype
   {DAV:}source

   These properties are implemented by the abstraction layer.

Locking properties 
   They refer to the two webdav-defined properties 
   {DAV:}supportedlock and {DAV:}lockdiscovery
    
   These properties are implemented by the locking library in
   ``wsgidav.lock_manager``.
      
Dead properties
   They refer to arbitrarily assigned properties not actively maintained. 

   These properties are implemented by the dead properties library in
   ``wsgidav.property_manager``.
"""
from wsgidav import util
import traceback

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
import sys

__docformat__ = 'reStructuredText'

import shelve
import threading


    
class PropertyManager(object):
    """
    A low performance property manager implementation using shelve
    """
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
                return True
            self._dict = shelve.open(self._persiststorepath)
            self._loaded = True
            if self._verbose >= 2:
                self._dump("After shelve.open()")
        finally:
            self._init_lock.release()         


    def _check(self, msg=""):
        try:
            if not self._loaded:
                return True
#            for k in self._dict.keys():
#                print "%s" % k
#                print "  -> %s" % self._dict[k]
            for k, v in self._dict.items():
                _ = "%s, %s" % (k, v)
            self._log("PropertyManager checks ok " + msg)
            return True
        except Exception:
            traceback.print_exc()
#            raise
#            sys.exit(-1)
            return False

    def _log(self, msg):
        if self._verbose >= 2:
            util.log(msg)


    def _dump(self, msg="", out=None):
        if out is None:
            out = sys.stdout
        print >>out, "PropertyManager(%s): %s" % (self._persiststorepath, msg)
        if not self._loaded:
            self._performInitialization()
            if self._verbose >= 2:
                return # Already dumped in _performInitialization
        try:
            for k, v in self._dict.items():
                print >>out, "    ", k
                for k2, v2 in v.items():
                    try:
                        print >>out, "        %s: '%s'" % (k2, v2)
                    except Exception, e:
                        print >>out, "        %s: ERROR %s" % (k2, e)
        except Exception, e:
            print >>sys.stderr, "PropertyManager._dump()  ERROR: %s" % e
            


    def getProperties(self, normurl):
        if not self._loaded:
            self._performInitialization()        
        returnlist = []
        if normurl in self._dict:
            for propdata in self._dict[normurl].keys():
                returnlist.append(propdata)
        return returnlist


    def getProperty(self, normurl, propname):
        if not self._loaded:
            self._performInitialization()
        if normurl not in self._dict:
            return None
        # TODO: sometimes we get exceptions here: (catch or otherwise make more robust?)
        try:
            resourceprops = self._dict[normurl]
        except Exception, e:
            util.log("getProperty(%s, %s) failed : %s" % (normurl, propname, e))
            raise
        return resourceprops.get(propname)


    def writeProperty(self, normurl, propname, propertyvalue, dryRun=False):
        self._log("writeProperty(%s, %s, dryRun=%s):\n\t%s" % (normurl, propname, dryRun, propertyvalue))
        if dryRun:
            return  # TODO: can we check anything here?
        
        propertyname = propname
        self._write_lock.acquire(True)
        try:
            if not self._loaded:
                self._performInitialization()
            if normurl in self._dict:
                locatordict = self._dict[normurl] 
            else:
                locatordict = dict([])    
            locatordict[propertyname] = propertyvalue
            self._dict[normurl] = locatordict
            self._dict.sync()
        finally:
            self._write_lock.release()
        self._check()         

    def removeProperty(self, normurl, propname, dryRun=False):
        """
        Specifying the removal of a property that does not exist is NOT an error.
        """
        self._log("removeProperty(%s, %s, dryRun=%s)" % (normurl, propname, dryRun))
        if dryRun:
            # TODO: can we check anything here?
            return  
        propertyname = propname
        self._write_lock.acquire(True)
        try:
            if not self._loaded:
                self._performInitialization()
            if normurl in self._dict:      
                locatordict = self._dict[normurl] 
                if propertyname in locatordict:
                    del locatordict[propertyname]
                    self._dict[normurl] = locatordict
                    self._dict.sync()
        finally:
            self._write_lock.release()         
        self._check()         

    def removeProperties(self, normurl):
        self._write_lock.acquire(True)
        self._log("removeProperties(%s)" % normurl)
        try:
            if not self._loaded:
                self._performInitialization()
            if normurl in self._dict:      
                del self._dict[normurl] 
        finally:
            self._write_lock.release()         

    def copyProperties(self, origurl, desturl):
        self._write_lock.acquire(True)
        self._log("copyProperties(%s, %s)" % (origurl, desturl))
        self._check()         
        try:
            if not self._loaded:
                self._performInitialization()
            if origurl in self._dict:      
                self._dict[desturl] = self._dict[origurl].copy() 
        finally:
            self._write_lock.release()         
        self._check("after copy")         

    def __repr__(self):
        return repr(self._dict)

    def __del__(self):
        self._check()         
        if self._loaded:
            self._dict.close()
        self._check()         
