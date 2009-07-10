"""
propertylibrary
===============

:Module: pyfileserver.propertylibrary
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com
:Project: PyFileServer, http://pyfilesync.berlios.de/
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

This module consists of a number of miscellaneous functions for the dead 
properties features of webDAV.

It also includes an implementation of a PropertyManager for
storage of dead properties. This implementation use
shelve for file storage.  See extrequestserver.py for details.

PropertyManagers must provide the methods as described in 
propertymanagerinterface_

.. _propertymanagerinterface : interfaces/propertymanagerinterface.py



Properties and PyFileServer
---------------------------
Properties of a resource refers to the attributes of the resource. A property
is referenced by the property name and the property namespace. We usually
refer to the property as ``{property namespace}property name`` 

Properties of resources as defined in webdav falls under three categories:

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
   ``pyfileserver.locklibrary`` and dead properties library in
   ``pyfileserver.propertylibrary``
      
Dead properties
   They refer to arbitrarily assigned properties not actively maintained. 

   These properties are implemented by the dead properties library in
   ``pyfileserver.propertylibrary``

Interface
---------

Classes::

   class PropertyManager(object)

Misc and Interface methods::

   removeProperties(pm, displaypath)
   copyProperties(pm, displaypath, destdisplaypath)
   writeProperty(pm, resourceAL, mappedpath, displaypath, propns, propname, propupdatemethod, propvalue, reallydoit = True)
   getProperty(pm, lm, resourceAL, mappedpath, displaypath, propns, propname)
   getApplicablePropertyNames(pm, lm, resourceAL, mappedpath, displaypath)


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
import locklibrary

"""
A low performance dead properties library using shelve
"""

class PropertyManager(object):

    def __init__(self, persiststore):
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

    def getProperties(self, normurl):
        if not self._loaded:
            self._performInitialization()        
        returnlist = []
        if normurl in self._dict:
            for propdata in self._dict[normurl].keys():
                pns, pname = propdata.split(';',1)
                returnlist.append((pns, pname))
        return returnlist

    def getProperty(self, normurl, propname, propns):
        if propns is None:
            propns = ''        
        propertyname = propns + ';' + propname
        if not self._loaded:
            self._performInitialization()
        if normurl not in self._dict:
            return None
        resourceprops = self._dict[normurl]
        if propertyname not in resourceprops:
            return None
        else:
            return resourceprops[propertyname]

    def writeProperty(self, normurl, propname, propns, propertyvalue):
        if propns is None:
            propns = ''        
        propertyname = propns + ';' + propname
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

    def removeProperty(self, normurl, propname, propns):
        if propns is None:
            propns = ''        
        propertyname = propns + ';' + propname
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

    def removeProperties(self, normurl):
        self._write_lock.acquire(True)
        try:
            if not self._loaded:
                self._performInitialization()
            if normurl in self._dict:      
                del self._dict[normurl] 
        finally:
            self._write_lock.release()         

    def copyProperties(self, origurl, desturl):
        self._write_lock.acquire(True)
        try:
            if not self._loaded:
                self._performInitialization()
            if origurl in self._dict:      
                self._dict[desturl] = self._dict[origurl].copy() 
        finally:
            self._write_lock.release()         

    def __repr__(self):
        return repr(self._dict)

    def __del__(self):
        if self._loaded:
            self._dict.close()

def removeProperties(pm, displaypath):
    pm.removeProperties(displaypath)

def copyProperties(pm, displaypath, destdisplaypath):
    pm.copyProperties(displaypath, destdisplaypath)

def writeProperty(pm, resourceAL, mappedpath, displaypath, propns, propname, propupdatemethod, propvalue, reallydoit = True):

    if propns is None:
        propns = ''

    # live properties
    if resourceAL.isPropertySupported(mappedpath, propname, propns):
        if reallydoit:
            if propupdatemethod == 'set':
                resourceAL.writeProperty(mappedpath, propname, propns, propvalue)
            elif propupdatemethod == 'remove':
                resourceAL.removeProperty(mappedpath, propname, propns)
        return 
        
    # raise exception for those reserved DAV: properties not supported by live properties
    reservedprops = ['creationdate', 'displayname', 'getcontenttype','resourcetype','getlastmodified', 'getcontentlength', 'getetag', 'getcontentlanguage', 'source', 'lockdiscovery', 'supportedlock']
    if propns == 'DAV:':
        if propname in reservedprops:
            raise HTTPRequestException(processrequesterrorhandler.HTTP_CONFLICT)               

    # rest of the items go to dead properties library
    if reallydoit:
        if propupdatemethod == 'set':
            pm.writeProperty(displaypath, propname, propns, propvalue)
        elif propupdatemethod == 'remove':
            pm.removeProperty(displaypath, propname, propns)
    return      

# raises HTTPRequestException(processrequesterrorhandler.HTTP_NOT_FOUND) if not found
def getProperty(pm, lm, resourceAL, mappedpath, displaypath, propns, propname):
    if propns is None:
        propns = ''

    # live properties
    if resourceAL.isPropertySupported(mappedpath, propname, propns):
        return resourceAL.getProperty(mappedpath, propname, propns)

    # reserved properties
    if propns == 'DAV:':
        reservedprops = ['creationdate', 'displayname', 'getcontenttype','resourcetype','getlastmodified', 'getcontentlength', 'getetag', 'getcontentlanguage', 'source', 'lockdiscovery', 'supportedlock']
        if propname == 'displayname':
            return displaypath
        elif propname == 'lockdiscovery':
            lockinfo = ''         
            activelocklist = locklibrary.getTokenListForUrl(lm, displaypath)
            for activelocktoken in activelocklist:
                lockinfo = lockinfo + '<D:activelock>\n'
                lockinfo = lockinfo + '<D:locktype><' + locklibrary.getLockProperty(lm, activelocktoken, 'LOCKTYPE') + '/></D:locktype>\n'
                lockinfo = lockinfo + '<D:lockscope><' + locklibrary.getLockProperty(lm, activelocktoken, 'LOCKSCOPE') + '/></D:lockscope>\n'
                lockinfo = lockinfo + '<D:depth>' + locklibrary.getLockProperty(lm, activelocktoken, 'LOCKDEPTH') + '</D:depth>\n'
                lockinfo = lockinfo + '<D:owner>' + locklibrary.getLockProperty(lm, activelocktoken, 'LOCKOWNER') + '</D:owner>\n'
                lockinfo = lockinfo + '<D:timeout>' + locklibrary.getLockProperty(lm, activelocktoken, 'LOCKTIME') + '</D:timeout>\n'
                lockinfo = lockinfo + '<D:locktoken><D:href>' + activelocktoken + '</D:href></D:locktoken>\n'
                lockinfo = lockinfo + '</D:activelock>\n'
            return lockinfo
        elif propname == 'supportedlock':
            return '<D:lockentry xmlns:D=\"DAV:\" >\n<D:lockscope><D:exclusive/></D:lockscope>\n<D:locktype><D:write/></D:locktype>\n</D:lockentry>\n<D:lockentry xmlns:D=\"DAV:\" >\n<D:lockscope><D:shared/></D:lockscope>\n<D:locktype><D:write/></D:locktype>\n</D:lockentry>'
        elif propname in reservedprops:
            raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_FOUND)               

    # dead properties
    propvalue = pm.getProperty(displaypath, propname, propns)
    if propvalue is None:
        raise HTTPRequestException(processrequesterrorhandler.HTTP_NOT_FOUND)               
    else:
        return propvalue

def getApplicablePropertyNames(pm, lm, resourceAL, mappedpath, displaypath):
    appProps = []
    
    appProps[0:0] = resourceAL.getSupportedPropertyNames(mappedpath)
    if ('DAV:','displayname') not in appProps:
        appProps.append( ('DAV:','displayname') )            
    appProps.append( ('DAV:','lockdiscovery') ) 
    appProps.append( ('DAV:','supportedlock') ) 

    otherprops = pm.getProperties(displaypath)
    for (otherns, othername) in otherprops:
        appProps.append( (otherns, othername) )
    return appProps







