"""
dav_provider
============

:Author: Martin Wendt, moogle(at)wwwendt.de 
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com (author of original PyFileServer)
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

This module implements DAVResource and DAVProvider objects.

DAVResource
-----------
Represents an existing (i.e. mapped) WebDAV resource or collection.
A DAVResource object is created by a call the DAVProvider::

    res = provider.getResourceInst(path)
    if res is None:
        raise DAVError(HTTP_NOT_FOUND)

The resource then may be used to query different attributes like ``res.name()``,
``res.isCollection()``, ``res.contentLength()``, and ``res.supportEtag()``. 

It also implements operations, that require an *existing* resource, like:
``getPreferredPath()``, ``createCollection()``, or ``getPropertyValue()``.

Usage::

    res = provider.getResourceInst(path)
    if res is not None:
        print res.getName()


DAVProvider
-----------
A DAV provider represents a shared WebDAV system.

There is only one provider instance per share, which is created during 
server start-up. After that, the dispatcher (``request_resolver.RequestResolver``) 
parses the request URL and adds it to the WSGI environment, so it 
can be accessed like this::

    provider = environ["wsgidav.provider"]

The main purpose of the provider is to create DAVResource objects for URLs.



Abstract base class for DAV resource providers.

This module serves these purposes:

  1. Documentation of the DAVProvider interface
  2. Common base class for all DAV providers
  3. Default implementation for most functionality that a resource provider must
     deliver.

If no default implementation can be provided, then all write actions generate
FORBIDDEN errors. Read requests generate NOT_IMPLEMENTED errors.
 
See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  

Supporting Objects
------------------

The DAVProvider takes two supporting objects:   
   
propertyManager
   An object that provides storage for dead properties assigned for webDAV resources.
   
   PropertyManagers must provide the methods as described in 
   ``wsgidav.interfaces.propertymanagerinterface``

   See property_manager.PropertyManager for a sample implementation
   using shelve.

lockmMnager
   An object that provides storage for locks made on webDAV resources.
   
   LockManagers must provide the methods as described in 
   ``wsgidav.interfaces.lockmanagerinterface``

   See lock_manager.LockManager for a sample implementation
   using shelve.
"""
__docformat__ = "reStructuredText"

import sys
import time
import traceback
import urllib
from wsgidav import util
# Trick PyDev to do intellisense and don't produce warnings:
from util import etree #@UnusedImport
if False: from xml.etree import ElementTree as etree     #@Reimport @UnresolvedImport

from dav_error import DAVError, \
    HTTP_NOT_FOUND, HTTP_FORBIDDEN,\
    PRECONDITION_CODE_ProtectedProperty, asDAVError

_logger = util.getModuleLogger(__name__)

#_livePropNames = ["{DAV:}creationdate", 
#                  "{DAV:}displayname", 
#                  "{DAV:}getcontenttype",
#                  "{DAV:}resourcetype",
#                  "{DAV:}getlastmodified", 
#                  "{DAV:}getcontentlength", 
#                  "{DAV:}getetag", 
#                  "{DAV:}getcontentlanguage", 
#                  "{DAV:}source", 
#                  "{DAV:}lockdiscovery", 
#                  "{DAV:}supportedlock"]


#===============================================================================
# DAVResource 
#===============================================================================
class DAVResource(object):
    """Represents a single existing DAV resource or collection instance.

    Instances of this class are created through the DAVProvider::
        
        res = provider.getResourceInst(path)
        if res and res.isCollection():
            print res.name()
            
    In the example above res will be ``None``, if the path cannot be mapped to
    an existing resource.
    The following attributes and methods are considered 'cheap':: 
    
        res.path
        res.provider
        res.isCollection()
        res.name()
    
    Querying other attributes is considered 'expensive' and delayed until the
    first access. 

    This default implementation expects that ``self._init()`` is implemented, in 
    order to use these getter methods::
        
        contentLength()
        contentType()
        created()
        displayName()
        displayType()
        etag()
        modified()
        supportRanges()
        supportEtag()
        supportModified()
        supportContentLength()
    
    These functions return ``None``, if the property is not available, or
    not supported.   
    
    Note, that custom DAVProviders may choose different implementations and
    return custom DAVResource objects, that do not use ``self._init()`` to
    cache properties. Only make sure, that your DAVResource object implements 
    the getters.  

    See also DAVProvider.getResourceInst().
    """
    def __init__(self, provider, path, isCollection):
        assert path=="" or path.startswith("/")
        self.provider = provider
        self.path = path
        self._isCollection = isCollection
        self._name = util.getUriName(self.path)
        self._dict = None
    
    
    def __repr__(self):
        d = None
        if hasattr(self, "_dict"):
            d = self._dict
        return "%s(%s): %s" % (self.__class__.__name__, self.path, d)


    def _init(self):
        """Read resource information into self._dict, for cached access.
        
        These items are expected:       
            created: 
                (int) creation date (in seconds, compatible with time module)
            displayName:
                (str, utf8) display name of resource / collection
            displayType:
                (str, utf8) type of resource for display, e.g. 'Directory', 
                'DOC File', ... 
            modified:
                (int) last modification date (in seconds, compatible with time 
                module)
            supportRanges:
                (bool) True, if resource supports HTTP_RANGE
        
        and additionally for simple resources (i.e. isCollection == False):
            contentLength: 
                (int) resource size in bytes
            contentType:
                (str) MIME type of content
            etag:
                (str)
        
        Single dictionary items are set to None, if they are not available, or
        not supported.   
        
        Every provider MUST override this method, if following default getters 
        are used.
        """
        raise NotImplementedError()

    
    def isCollection(self):
        return self._isCollection
    def name(self):
        return self._name

    
    def _getInfo(self, info):
        if self._dict is None:
            self._init()
        return self._dict.get(info)       
    def contentLength(self):
        return self._getInfo("contentLength")
    def contentType(self):
        return self._getInfo("contentType")
    def created(self):
        return self._getInfo("created")
    def displayName(self):
        return self._getInfo("displayName")
    def displayType(self):
        return self._getInfo("displayType")
    def etag(self):
        return self._getInfo("etag")
    def modified(self):
        return self._getInfo("modified")
    def supportContentLength(self):
        return self.contentLength() is not None
    def supportEtag(self):
        return self.etag() is not None
    def supportModified(self):
        return self.modified() is not None
    def supportNativeCopy(self):
        return False
    def supportNativeDelete(self):
        return False
    def supportNativeMove(self):
        return False
    def supportRanges(self):
        return self._getInfo("supportRanges") is True
#    def supportRecursiveCopy(self):
#        return False
    def supportRecursiveDelete(self):
        return False
    def supportRecursiveMove(self):
        return False
    
    
    def getPreferredPath(self):
        """Return preferred mapping for a resource mapping.
        
        Different URLs may map to the same resource, e.g.:
            '/a/b' == '/A/b' == '/a/b/'
        getPreferredPath() returns the same value for all these variants, e.g.:
            '/a/b/'   (assuming resource names considered case insensitive)

        @param path: a UTF-8 encoded, unquoted byte string.
        @return: a UTF-8 encoded, unquoted byte string.
        """
        if self.path in ("", "/"):
            return "/"
        # Append '/' for collections
        if self.isCollection() and not self.path.endswith("/"):
            return self.path + "/"
        # TODO: handle case-sensitivity, depending on OS 
        # (FileSystemProvider could do this with os.path:
        # (?) on unix we can assume that the path already matches exactly the case of filepath
        #     on windows we could use path.lower() or get the real case from the file system
        return self.path

    
    def getRefUrl(self):
        """Return the quoted, absolute, unique URL of a resource, relative to appRoot.
        
        Byte string, UTF-8 encoded, quoted.
        Starts with a '/'. Collections also have a trailing '/'.
        
        This is basically the same as getPreferredPath, but deals with 
        'virtual locations' as well.
        
        e.g. '/a/b' == '/A/b' == '/bykey/123' == '/byguid/abc532'
        
        getRefUrl() returns the same value for all these URLs, so it can be
        used as a key for locking and persistence storage. 

        DAV providers that allow virtual-mappings must override this method.

        See also comments in DEVELOPERS.txt glossary.
        """
        return urllib.quote(self.provider.sharePath + self.getPreferredPath())

    
#    def getRefKey(self):
#        """Return an unambigous identifier string for a resource.
#        
#        Since it is always unique for one resource, <refKey> is used as key for 
#        the lock- and property storage dictionaries.
#        
#        This default implementation calls getRefUrl(), and strips a possible 
#        trailing '/'.
#        """
#        refKey = self.getRefUrl(path)
#        if refKey == "/":
#            return refKey
#        return refKey.rstrip("/")

    
    def getHref(self):
        """Convert path to a URL that can be passed to XML responses.
        
        Byte string, UTF-8 encoded, quoted.

        @see http://www.webdav.org/specs/rfc4918.html#rfc.section.8.3
        We are using the path-absolute option. i.e. starting with '/'. 
        URI ; See section 3.2.1 of [RFC2068]
        """
        # Nautilus chokes, if href encodes '(' as '%28'
        # So we don't encode 'extra' and 'safe' characters (see rfc2068 3.2.1)
        safe = "/" + "!*'()," + "$-_|."
        return urllib.quote(self.provider.mountPath + self.provider.sharePath 
                            + self.getPreferredPath(), safe=safe)


    def getParent(self):
        """Return parent DAVResource or None.
        
        There is NO checking, if the parent is really a mapped collection.
         
        """
        # TODO: check all calls to this: maybe we should return DavResource.exist=False instead of None
        parentpath = util.getUriParent(self.path)
        if not parentpath:
            return None
        return self.provider.getResourceInst(parentpath)


    def getMemberNames(self):
        """Return list of (direct) collection member names (UTF-8 byte strings).
        
        Every provider MUST override this method.
        """
        raise NotImplementedError()


    def getDescendants(self, collections=True, resources=True, 
                       depthFirst=False, depth="infinity", addSelf=False):
        """Return a list DAVResource objects of a collection (children, grand-children, ...).

        This default implementation calls getMemberNames() and 
        provider.getResourceInst() recursively.
        
        :Parameters:
            depthFirst : bool
                use <False>, to list containers before content.
                (e.g. when moving / copying branches.)
                Use <True>, to list content before containers. 
                (e.g. when deleting branches.)
            depth : string
                '0' | '1' | 'infinity'
        """
        assert depth in ("0", "1", "infinity")
        res = []
        if addSelf and not depthFirst:
            res.append(self)
        if depth != "0" and self.isCollection():
            pathPrefix = self.path.rstrip("/") + "/"
            for name in self.getMemberNames():
                child = self.provider.getResourceInst(pathPrefix + name)
                assert child, "Could not read resource inst '%s'" % (pathPrefix + name)
                want = (collections and child.isCollection()) or (resources and not child.isCollection())
                if want and not depthFirst: 
                    res.append(child)
                if child.isCollection() and depth == "infinity":
                    res.extend(child.getDescendants(collections, resources, depthFirst, depth, addSelf=False))
                if want and depthFirst: 
                    res.append(child)
        if addSelf and depthFirst:
            res.append(self)
        return res

        
    def getDirInfo(self):
        """Return list of dictionaries describing direct collection members.
        
        This method is called by dir_browser middleware, and may be used to
        provide the directory listing info in a efficient way.
        """
        assert self.isCollection()
        raise NotImplementedError()


    # --- Properties -----------------------------------------------------------
     
    def getPropertyNames(self, mode="allprop"):
        """Return list of supported property names in Clark Notation.
        
        @param mode: 'allprop': common properties, that should be sent on 'allprop' requests. 
                     'propname': all available properties.

        This default implementation returns a combination of:
        
        - Standard live properties in the {DAV:} namespace, using the getter
          methods.
        - {DAV:}lockdiscovery and {DAV:}supportedlock, if a lock manager is 
          present
        - Result of getCustomLiveProperties()
        - a list of dead properties, if a property manager is present
        """
        # TODO: currently, we assume that allprop == propname
        if not mode in ("allprop", "propname"):
            raise ValueError("Invalid mode '%s'." % mode)

        ## Live properties
        propNameList = []
        if self.created() is not None:
            propNameList.append("{DAV:}creationdate")
        if self.contentLength() is not None:
            assert not self.isCollection() 
            propNameList.append("{DAV:}getcontentlength")
        if self.contentType() is not None:
            propNameList.append("{DAV:}getcontenttype")
        if self.isCollection() is not None:
            propNameList.append("{DAV:}resourcetype")
        if self.modified() is not None:
            propNameList.append("{DAV:}getlastmodified")
        if self.displayName() is not None:
            propNameList.append("{DAV:}displayname")
        if self.etag() is not None:
            propNameList.append("{DAV:}getetag")
            
        ## Locking properties 
        if self.provider.lockManager:
            if not "{DAV:}lockdiscovery" in propNameList:
                propNameList.append("{DAV:}lockdiscovery")
            if not "{DAV:}supportedlock" in propNameList:
                propNameList.append("{DAV:}supportedlock")

        ## Dead properties
        if self.provider.propManager:
            refUrl = self.getRefUrl()
            for deadProp in self.provider.propManager.getProperties(refUrl):
                propNameList.append(deadProp)
                
        return propNameList


    def getProperties(self, mode, nameList=None, namesOnly=False):
        """Return properties as list of 2-tuples (name, value).

        name 
            is the property name in Clark notation.
        value 
            may have different types, depending on the status: 
            - string or unicode: for standard property values.
            - etree.Element: for complex values.
            - DAVError in case of errors.
            - None: if namesOnly was passed.

        @param path: 
        @param mode: "allprop", "propname", or "named"
        @param nameList: list of property names in Clark Notation (only for mode 'named')
        @param namesOnly: return None for <value>
        @param davres: pass a DAVResource to access cached info  
        """
        if not mode in ("allprop", "propname", "named"):
            raise ValueError("Invalid mode '%s'." % mode)

        if mode in ("allprop", "propname"):
            # TODO: allprop can have nameList, when <include> option is implemented
            assert nameList is None
            nameList = self.getPropertyNames(mode)
        else:
            assert nameList is not None

        propList = []
        for name in nameList:
            try:
                if namesOnly:
                    propList.append( (name, None) )
                else:
                    value = self.getPropertyValue(name)
                    propList.append( (name, value) )
            except DAVError, e:
                propList.append( (name, e) )
            except Exception, e:
                propList.append( (name, asDAVError(e)) )
                if self.provider.verbose >= 2:
                    traceback.print_exc(10, sys.stderr)  
                    
        return propList


    def getPropertyValue(self, propname):
        """Return the value of a property.
        
        propname:
            the property name in Clark notation.
        return value:
            may have different types, depending on the status:
             
            - string or unicode: for standard property values.
            - lxml.etree.Element: for complex values.
            
            If the property is not available, a DAVError is raised.
            
        This default implementation handles ``{DAV:}lockdiscovery`` and
        ``{DAV:}supportedlock`` using the associated lock manager.
        
        All other *live* properties (i.e. propname starts with ``{DAV:}``) are 
        delegated to the self.xxx() getters.
        
        Finally, other properties are considered *dead*, and are handled  by 
        the associated property manager. 
        """
        refUrl = self.getRefUrl()
        lm = self.provider.lockManager     
        if lm and propname == "{DAV:}lockdiscovery":
            # TODO: we return HTTP_NOT_FOUND if no lockmanager is present. Correct?
            activelocklist = lm.getUrlLockList(refUrl)
            lockdiscoveryEL = etree.Element(propname)
            for lock in activelocklist:
                activelockEL = etree.SubElement(lockdiscoveryEL, "{DAV:}activelock")

                locktypeEL = etree.SubElement(activelockEL, "{DAV:}locktype")
                etree.SubElement(locktypeEL, "{DAV:}%s" % lock["type"])

                lockscopeEL = etree.SubElement(activelockEL, "{DAV:}lockscope")
                etree.SubElement(lockscopeEL, "{DAV:}%s" % lock["scope"])
                
                etree.SubElement(activelockEL, "{DAV:}depth").text = lock["depth"]
                # lock["owner"] is an XML string
                ownerEL = util.stringToXML(lock["owner"])

                activelockEL.append(ownerEL)
                
                timeout = lock["timeout"]
                if timeout < 0:
                    timeout =  "Infinite"
                else:
                    timeout = "Second-" + str(long(timeout - time.time())) 
                etree.SubElement(activelockEL, "{DAV:}timeout").text = timeout
                
                locktokenEL = etree.SubElement(activelockEL, "{DAV:}locktoken")
                etree.SubElement(locktokenEL, "{DAV:}href").text = lock["token"]

                # TODO: this is ugly: 
                #       res.getPropertyValue("{DAV:}lockdiscovery")
                #       
#                lockRoot = self.getHref(self.provider.refUrlToPath(lock["root"]))
                lockPath = self.provider.refUrlToPath(lock["root"])
                lockRes = self.provider.getResourceInst(lockPath)
                lockHref = lockRes.getHref()
#                print "lockedRoot: %s -> href=%s" % (lockPath, lockHref)

                lockrootEL = etree.SubElement(activelockEL, "{DAV:}lockroot")
                etree.SubElement(lockrootEL, "{DAV:}href").text = lockHref

            return lockdiscoveryEL            

        elif lm and propname == "{DAV:}supportedlock":
            # TODO: we return HTTP_NOT_FOUND if no lockmanager is present. Correct?
            # TODO: the lockmanager should decide about it's features
            supportedlockEL = etree.Element(propname)

            lockentryEL = etree.SubElement(supportedlockEL, "{DAV:}lockentry")
            lockscopeEL = etree.SubElement(lockentryEL, "{DAV:}lockscope")
            etree.SubElement(lockscopeEL, "{DAV:}exclusive")
            locktypeEL = etree.SubElement(lockentryEL, "{DAV:}locktype")
            etree.SubElement(locktypeEL, "{DAV:}write")

            lockentryEL = etree.SubElement(supportedlockEL, "{DAV:}lockentry")
            lockscopeEL = etree.SubElement(lockentryEL, "{DAV:}lockscope")
            etree.SubElement(lockscopeEL, "{DAV:}shared")
            locktypeEL = etree.SubElement(lockentryEL, "{DAV:}locktype")
            etree.SubElement(locktypeEL, "{DAV:}write")
            
            return supportedlockEL

        elif propname.startswith("{DAV:}"):
            # Standard live property (raises HTTP_NOT_FOUND if not supported)
            if propname == "{DAV:}creationdate" and self.created() is not None:
                return util.getRfc1123Time(self.created())
            elif propname == "{DAV:}getcontenttype" and self.contentType() is not None:
                return self.contentType()
            elif propname == "{DAV:}resourcetype":
                if self.isCollection():
                    resourcetypeEL = etree.Element(propname)
                    etree.SubElement(resourcetypeEL, "{DAV:}collection")
                    return resourcetypeEL            
                return ""   
            elif propname == "{DAV:}getlastmodified" and self.modified() is not None:
                return util.getRfc1123Time(self.modified())
            elif propname == "{DAV:}getcontentlength" and self.contentLength() is not None:
                return str(self.contentLength())
            elif propname == "{DAV:}getetag" and self.etag() is not None:
                return self.etag()
            elif propname == "{DAV:}displayname" and self.displayName() is not None:
                return self.displayName()
    
            # Unsupported No persistence available, or property not found
            raise DAVError(HTTP_NOT_FOUND)               
        
        # Dead property
        pm = self.provider.propManager
        if pm:
            value = pm.getProperty(refUrl, propname)
            if value is not None:
#                return etree.XML(value)
                return util.stringToXML(value) 

        # No persistence available, or property not found
        raise DAVError(HTTP_NOT_FOUND)               
    

    def setPropertyValue(self, propname, value, dryRun=False):
        """Set or remove property value.
        
        value == None means 'remove property'.
        Raise HTTP_FORBIDDEN if property is read-only, or not supported.
        Removing a non-existing prop is NOT an error. 
        
        When dryRun is True, this function should raise errors, as in a real
        run, but MUST NOT change any data.
                 
        This default implementation delegates {DAV:} properties to 
        ``setLivePropertyValue()`` and stores everything else as dead property.
        
        @param path:
        @param propname: property name in Clark Notation
        @param value: value == None means 'remove property'.
        @param dryRun: boolean
        """
        assert value is None or isinstance(value, (etree._Element))

        if propname in ("{DAV:}lockdiscovery", "{DAV:}supportedlock"):
            # Locking properties are always read-only
            raise DAVError(HTTP_FORBIDDEN,  
                           preconditionCode=PRECONDITION_CODE_ProtectedProperty)  
        elif propname.startswith("{DAV:}"):
            # raises DAVError(HTTP_FORBIDDEN) if read-only, or not supported
            return self.setLivePropertyValue(propname, value, dryRun)

        # Dead property
        pm = self.provider.propManager
        if pm:
            # TODO: do we write all proprties?
            refUrl = self.getRefUrl()
            if value is None:
                return pm.removeProperty(refUrl, propname)
            else:
                value = etree.tostring(value)
                return pm.writeProperty(refUrl, propname, value, dryRun)             

        raise DAVError(HTTP_FORBIDDEN)  # TODO: Chun used HTTP_CONFLICT 




    def removeAllProperties(self, recursive):
        """Remove all associated dead properties."""
        if self.provider.propManager:
            self.provider.propManager.removeProperties(self.getRefUrl())




    def setLivePropertyValue(self, propname, value, dryRun=False):
        """Set or remove a live property value.
        
        value == None means 'remove property'.
        Raise HTTP_FORBIDDEN if property is read-only, or not supported.

        When dryRun is True, this function should raise errors, as in a real
        run, but MUST NOT change any data.
                 
        This function MUST NOT handle {DAV:}lockdiscovery and {DAV:}supportedlock,
        since this is done by the calling .setPropertyValue() function.

        This will usually be forbidden, since live properties cannot be
        removed.

        @param path:
        @param propname: property name in Clark Notation
        @param value: value == None means 'remove property'.
        @param dryRun: boolean
        
        This default implementation raises DAVError(HTTP_FORBIDDEN), since 
        {DAV:} live properties are mostly read-only, .
        
        TODO: RFC 3253 states that {DAV:}displayname 'SHOULD NOT be protected' 
        so we could implement {DAV:}displayname as RW, if propMan is available
        Maybe in a 'create-on-write' way.        
        """
        raise DAVError(HTTP_FORBIDDEN,  # TODO: Chun used HTTP_CONFLICT 
                       preconditionCode=PRECONDITION_CODE_ProtectedProperty)  
    
    
    # --- Locking --------------------------------------------------------------

    def isLocked(self):
        """Return True, if URI is locked."""
        if self.provider.lockManager is None:
            return False
        return self.provider.lockManager.isUrlLocked(self.getRefUrl())


    def removeAllLocks(self, recursive):
        if self.provider.lockManager:
            self.provider.lockManager.removeAllLocksFromUrl(self.getRefUrl())


    # --- Read / write ---------------------------------------------------------
    
    def createEmptyResource(self, name):
        """Create and return an empty (length-0) resource as member of self.
        
        Called for LOCK requests on unmapped URLs.
        
        Preconditions (to be ensured by caller):
        
          - this must be a collection
          - <self.path + name> must not exist  
          - there must be no conflicting locks

        Returns a DAVResuource.
        
        This method MUST be implemented by all providers that support write 
        access.
        This default implementation simply raises HTTP_FORBIDDEN.
        """
        assert self.isCollection()
        raise DAVError(HTTP_FORBIDDEN)               
    

    def createCollection(self, name):
        """Create a new collection as member of self.
        
        Preconditions (to be ensured by caller):
        
          - this must be a collection
          - <self.path + name> must not exist  
          - there must be no conflicting locks

        This method MUST be implemented by all providers that support write 
        access.
        This default implementation raises HTTP_FORBIDDEN.
        """
        assert self.isCollection()
        raise DAVError(HTTP_FORBIDDEN)               


    def getContent(self):
        """Open content as a stream for reading.

        Returns a file-like object / stream containing the contents of the
        resource specified.
        The application will close() the stream.      
         
        This method MUST be implemented by all providers.
        """
        assert not self.isResource()
        raise NotImplementedError()
    

    # TODO: rename to beginWrite() and add endWrite(success)
    def openResourceForWrite(self, contentType=None):
        """Open content as a stream for writing.
         
        This method MUST be implemented by all providers that support write 
        access.
        """
        assert self.isResource()
        raise DAVError(HTTP_FORBIDDEN)               

    
    def delete(self):
        """Remove this resource (recursive).
        
        Preconditions (to be ensured by caller):
        
          - there must not be any conflicting locks  

        This function
        
          - removes this resource and all members
          - removes associated locks
          - removes associated dead properties
          - raises HTTP_FORBIDDEN for read-only resources
          - raises HTTP_INTERNAL_ERROR on error
        
        An implementation may choose to apply other semantics.
        For example deleting '\by_tag\cool\myres' may simply remove the 'cool' 
        tag from 'my_res'. 
        In this case, the resource might still be available by other URLs, so 
        locks and properties are not removed.

        This method MUST be implemented by all providers that support write 
        access.
        """
        raise DAVError(HTTP_FORBIDDEN)               

    
    def move(self, destPath):
        """Move this resource to destPath (recursive).
        
        Preconditions (to be ensured by caller):
        
          - there must not be any conflicting locks on source
          - there must not be any conflicting locks on destination
          - destPath must not exist 
          - destPath must not be a member of this resource

        This function
        
          - moves this resource and all members to destPath.
          - MUST NOT move associated locks.
            Instead, if the source (or children thereof) have locks, then
            these locks should be removed.
          - SHOULD maintain associated live properties, when applicable
          - MUST maintain associated dead properties
          - raises HTTP_FORBIDDEN for read-only resources
          - raises HTTP_INTERNAL_ERROR on error
        
        An implementation may choose to apply other semantics.
        For example copying '\by_tag\cool\myres' to '\by_tag\new\myres' may 
        simply add a 'new' tag to 'my_res'. 

        This method is only called, when self.supportRecursiveMove() returns 
        True. Otherwise, the request server implements MOVE using delete/copy.
        
        This method MAY be implemented in order to improve performance.
        """
        raise DAVError(HTTP_FORBIDDEN)               


    def copy(self, destPath):
        """Copy this resource to destPath (non-recursive).
        
        Preconditions (to be ensured by caller):
        
          - there must not be any conflicting locks on destination
          - overwriting is only allowed (i.e. destPath exists), when source and 
            dest both are non-collections and a Overwrite='T' was passed 
          - destPath must not be a child path of this resource

        This function
        
          - MUST NOT copy collection members
          - Overwrites non-collections content, if destination exists.
          - MUST NOT copy locks
          - SHOULD copy live properties, when appropriate.
            E.g. displayname should be copied, but creationdate should be
            reset if the target did not exist before.
          - SHOULD copy dead properties
          - raises HTTP_FORBIDDEN for read-only providers
          - raises HTTP_INTERNAL_ERROR on error
        
        This method MUST be implemented by all providers that support write 
        access.
        """
        raise DAVError(HTTP_FORBIDDEN)               



#    def copyNative(self, destPath):
#        """Copy this resource and all members to destPath.
#        
#        Preconditions (to be ensured by caller):
#        
#          - there must not be any conflicting locks on destination
#          - overwriting is only allowed (i.e. destPath exists), when source and 
#            dest both are non-collections and a Overwrite='T' was passed 
#          - destPath must not be a child path of this resource
#
#        This function
#        
#          - copies this resource to destPath.
#            If source is a collection and ``recursive`` is True, then all 
#            members are copied as well.
#            If ``recursive`` is False, only the resource and it's properties
#            are copied
#          - MUST NOT copy locks
#          - SHOULD copy live properties, when appropriate.
#            E.g. displayname should be copied, but creationdate should be
#            reset if the target did not exist before.
#          - SHOULD copy dead properties
#          - raises HTTP_FORBIDDEN for read-only providers
#          - raises HTTP_INTERNAL_ERROR on error
#        
#        A depth-0 copy of collections can NOT be handled by this method.
#        
#        An implementation may choose to apply other semantics.
#        For example copying '\by_tag\cool\myres' to '\by_tag\new\myres' may 
#        simply add a 'new' tag to 'my_res'. 
#
#        This method MUST be implemented by all providers that support write 
#        access.
#        """
#        raise DAVError(HTTP_FORBIDDEN)               



#===============================================================================
# DAVProvider
#===============================================================================

class DAVProvider(object):
    """Abstract base class for DAV resource providers.
    
    There will be only one DAVProvider instance per share (not per request).
    """
    def __init__(self):
        self.mountPath = ""
        self.sharePath = None 
        self.lockManager = None
        self.propManager = None 
        self.verbose = 2

        self._count_getResourceInst = 0
        self._count_getResourceInstInit = 0
#        self.caseSensitiveUrls = True

    
    def __repr__(self):
        return self.__class__.__name__


    def setMountPath(self, mountPath):
        """Set application root for this resource provider.
        
        This is the value of SCRIPT_NAME, when WsgiDAVApp is called.
        """
        assert mountPath in ("", "/") or not mountPath.endswith("/")
        self.mountPath = mountPath

    
    def setSharePath(self, sharePath):
        """Set application location for this resource provider.
        
        @param sharePath: a UTF-8 encoded, unquoted byte string.
        """
        if isinstance(sharePath, unicode):
            sharePath = sharePath.encode("utf8")
        assert sharePath=="" or sharePath.startswith("/")
        if sharePath == "/":
            sharePath = ""  # This allows to code 'absPath = sharePath + path'
        assert sharePath in ("", "/") or not sharePath.endswith("/")
        self.sharePath = sharePath
        

    def setLockManager(self, lockManager):
#        assert isinstance(lockManager, LockManager)
        self.lockManager = lockManager


    def setPropManager(self, propManager):
#        assert isinstance(lockManager, PropManager)
        self.propManager = propManager

        
    def refUrlToPath(self, refUrl):
        """Convert a refUrl to a path, by stripping the share prefix.
        
        Used to calculate the <path> from a storage key by inverting getRefUrl().
        """
        return "/" + urllib.unquote(util.lstripstr(refUrl, self.sharePath)).lstrip("/")


    def getResourceInst(self, path):
        """Return a DAVResource object for a path.

        This function is mainly used to query live properties for a resource.
        The assumption is, that it is more efficient to query all infos in one
        call, rather than have single calls for every info type. 

        It should be called only once per request and resource::
            
            res = provider.getResourceInst(path)
            if res and not res.isCollection():
                print res.contentType()
        
        If <path> does not exist, None is returned.
        
        See DAVResource for details.

        This method MUST be implemented.
        """
        raise NotImplementedError()


    def exists(self, path):
        """Return True, if path maps to an existing resource.

        This method should only be used, if no other information is queried
        for <path>. Otherwise a DAVResource should be created first.
        
        This method SHOULD be overridden by a more efficient implementation.
        """
        return self.getResourceInst(path) is not None


    def isCollection(self, path):
        """Return True, if path maps to a collection resource.

        This method should only be used, if no other information is queried
        for <path>. Otherwise a DAVResource should be created first.
        """
        res = self.getResourceInst(path)
        return res and res.isCollection()


#    def removeAtomic(self, pathOrRes):
#        """Remove the resource and associated locks and properties.
#        
#        This default implementation calls self.deleteResource(path), followed by 
#        .removeAllProperties(path) and .removeAllLocks(path).
#        Errors are raised on failure. 
#
#        This function should NOT be implemented in a recursive way.
#        Instead, the caller is responsible to call remove() for all child 
#        resources before.
#        The caller is also responsible for checking of locks and permissions. 
#        """
#        if isinstance(pathOrRes, str):
#            pathOrRes = self.getResourceInst(pathOrRes)
#        pathOrRes.deleteResource()
#        pathOrRes.removeAllProperties()
#        pathOrRes.removeAllLocks()


    def copyAtomic(self, srcPath, destPath):
        """Remove the resource and associated locks and properties.
        
        This default implementation calls self.deleteResource(path), followed by 
        .removeAllProperties(path) and .removeAllLocks(path).
        Errors are raised on failure. 

        This function should NOT be implemented in a recursive way.
        Instead, the caller is responsible to call remove() for all child 
        resources before.
        The caller is also responsible for checking of locks and permissions. 
        """
        self.deleteResource()
        self.removeAllProperties()
        self.removeAllLocks()

