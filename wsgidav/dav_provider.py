"""
dav_provider
============

:Author: Martin Wendt, moogle(at)wwwendt.de 
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com (author of original PyFileServer)
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

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

_livePropNames = ["{DAV:}creationdate", 
                  "{DAV:}displayname", 
                  "{DAV:}getcontenttype",
                  "{DAV:}resourcetype",
                  "{DAV:}getlastmodified", 
                  "{DAV:}getcontentlength", 
                  "{DAV:}getetag", 
                  "{DAV:}getcontentlanguage", 
                  "{DAV:}source", 
                  "{DAV:}lockdiscovery", 
                  "{DAV:}supportedlock"]


#===============================================================================
# DAVResource 
#===============================================================================
class DAVResource(object):
    """Represents a single DAV resource instance.

    This class caches resource information on initialization, so querying 
    multiple live properties can be handled more efficiently.

    Instances of this class are created through the DAVProvider::
        
        davres = davprovider.getResourceInst(path)
        if davres.exists() and davres.isCollection():
            print davres.name()
            
    This default implementation expects that a dictionary is passed to the 
    constructor, containing the resource attributes:
    
        name:
            (str) name of resource / collection
        displayName:
            (str) display name of resource / collection
        displayType:
            (str) type of resource for display, e.g. 'Directory', 'DOC File', ... 
        isCollection:
            (bool) 
        modified:
            (int) last modification date (in seconds, compatible with time module)
        created: 
            (int) creation date (in seconds, compatible with time module)
    
    and additionally for simple resources (i.e. isCollection == False):
        contentType:
            (str) MIME type of content
        contentLength: 
            (int) resource size in bytes
        supportRanges:
            (bool)
        etag:
            (string)
    
    Single dictionary items are set to None, if they are not available, or
    not supported.   
    
    infoDict may be None, to create an DAVResource that does not exist (i.e. 
    is not mapped to an URL).

    typeList MAY be passed, to specify a list of requested information types.
    The implementation MAY uses this list to avoid expensive calculation of
    unwanted information types.

    Note, that custom DAVProviders may choose different implementations and
    return custom DAVResource objects as well. 
    Only make sure, that your DAVResource object implements this interface.  

    See also DAVProvider.getResourceInst().
    """
    def __init__(self, davProvider, path, infoDict, typeList):
        self.provider = davProvider
        self.path = path
        self._dict = infoDict
        self._exists = bool(self._dict)
        self._typeList = typeList 
    def __repr__(self):
        return "%s(%s): %s" % (self.__class__.__name__, self.path, self._dict)
    def exists(self):
        return self._exists
    def isCollection(self):
        return self._exists and self._dict["isCollection"]
    def isResource(self):
        return self._exists and not self._dict["isCollection"]
    def contentLength(self):
        return self._dict.get("contentLength")
    def contentType(self):
        return self._dict.get("contentType")
    def created(self):
        return self._dict.get("created")
    def displayName(self):
        return self._dict.get("displayName")
    def displayType(self):
        return self._dict.get("displayType")
    def etag(self):
        return self._dict.get("etag")
    def modified(self):
        return self._dict.get("modified")
    def name(self):
        return self._dict.get("name")
    def supportRanges(self):
        return self._dict.get("supportRanges")
    def supportEtag(self):
        return self._dict.get("etag") is not None
    def supportModified(self):
        return self._dict.get("modified") is not None
    def supportContentLength(self):
        return self._dict.get("contentLength") is not None
    def supportedLivePropertyNames(self):
        """Return list of supported live properties in Clark Notation.

        SHOULD NOT add {DAV:}lockdiscovery and {DAV:}supportedlock.
        """
        propmap = {"created": "{DAV:}creationdate",
                   "contentType": "{DAV:}getcontenttype",
                   "isCollection": "{DAV:}resourcetype",
                   "modified": "{DAV:}getlastmodified",
                   "displayName": "{DAV:}displayname",
                   "etag": "{DAV:}getetag",
                   }
        if not self.isCollection():
            propmap["contentLength"] = "{DAV:}getcontentlength"
            
        appProps = []
        for k, v in propmap.items(): 
            if k in self._dict:
                appProps.append(v)
        return appProps


#===============================================================================
# DAVProvider
#===============================================================================

class DAVProvider(object):
    """Abstract base class for DAV resource providers.
    
    There will be only one DAVProvider instance per share (not per request).
    """
    
    
    """Available info types, that a DAV Provider MAY support.
       See DAVProvider.getInfoDict() for details."""

    def __init__(self):
        self.mountPath = ""
        self.sharePath = None 
        self.lockManager = None
        self.propManager = None 
        self.verbose = 2
        self.caseSensitiveUrls = True

    
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
        self.propManager = propManager

        
    def getPreferredPath(self, path):
        """Return preferred mapping for a resource mapping.
        
        Different URLs may map to the same resource, e.g.:
            '/a/b' == '/A/b' == '/a/b/'
        getPreferredPath() returns the same value for all these variants, e.g.:
            '/a/b/'   (assuming resource names considered case insensitive)

        @param path: a UTF-8 encoded, unquoted byte string.
        @return: a UTF-8 encoded, unquoted byte string.
        """
        if path in ("", "/"):
            return "/"
        assert path.startswith("/")
        # Append '/' for collections
        # TODO: we should avoid calling isCollection() her, since this may be expensive.
        if not path.endswith("/") and self.isCollection(path):
            path += "/"
        # TODO: handle case-sensitivity, depending on OS 
        # (FileSystemProvider could do this with os.path:
        # (?) on unix we can assume that the path already matches exactly the case of filepath
        #     on windows we could use path.lower() or get the real case from the file system
        return path
        

    def getRefUrl(self, path):
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
        return urllib.quote(self.sharePath + self.getPreferredPath(path))


#    def getRefKey(self, path):
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


    def getHref(self, path):
        """Convert path to a URL that can be passed to XML responses.
        
        Byte string, UTF-8 encoded, quoted.

        @see http://www.webdav.org/specs/rfc4918.html#rfc.section.8.3
        We are using the path-absolute option. i.e. starting with '/'. 
        URI ; See section 3.2.1 of [RFC2068]
        """
        # Nautilus chokes, if href encodes '(' as '%28'
        # So we don't encode 'extra' and 'safe' characters (see rfc2068 3.2.1)
        safe = "/" + "!*'()," + "$-_|."
        return urllib.quote(self.mountPath + self.sharePath + self.getPreferredPath(path), safe=safe)


    def refUrlToPath(self, refUrl):
        """Convert a refUrl to a path, by stripping the mount prefix.
        
        Used to calculate the <path> from a storage key by inverting getRefUrl().
        """
        return "/" + urllib.unquote(util.lstripstr(refUrl, self.sharePath)).lstrip("/")


    def getParent(self, path):
        """Return URL of parent collection (with a trailing '/') or None.
        
        Note: there is no checking, if the parent is really a mapped collection. 
        """
        if not path or path == "/":
            return None
        parentUrl = path.rstrip("/").rsplit("/", 1)[0]
        return parentUrl + "/"


    def getMemberNames(self, path):
        """Return list of (direct) collection member names (UTF-8 byte strings).
        
        Every provider must override this method.
        """
        raise NotImplementedError()


    def iter(self, path, 
            collections=True, resources=True, 
            depthFirst=False,
            depth="infinity",
            addSelf=True):
        """Return iterator of child path's.
        
        This default implementation calls getMemberNames() recursively.
        
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

        if addSelf and not depthFirst:
            yield path
        if depth != "0" and self.isCollection(path):
            for e in self.getMemberNames(path):
                childUri = path.rstrip("/") + "/" + e
                isColl = self.isCollection(childUri)
                if isColl:
                    childUri += "/"
                want = (collections and isColl) or (resources and not isColl)
                if want and not depthFirst: 
                    yield childUri
                if isColl and depth == "infinity":
                    for e in self.iter(childUri, collections, resources, depthFirst, depth, False):
                        yield e
                if want and depthFirst: 
                    yield childUri
        if addSelf and depthFirst:
            yield path


    def getDescendants(self, 
            path, 
            collections=True, resources=True, 
            depthFirst=False,
            depth="infinity",
            addSelf=False):
        """Return a list member path's of a collection (children, grand-children, ...)."""
        return list(self.iter(path, collections, resources, depthFirst, depth, addSelf))
        
        
    def getChildren(self, path): 
        """Return a list of internal member path's of a collection (direct children only)."""
        return list(self.iter(path, collections=True, resources=True, depthFirst=False, depth="1", addSelf=False))
        
        
    def getResourceInst(self, path, typeList=None):
        """Return a DAVResource object for path.

        This function is mainly used to query live properties for a resource.
        The assumption is, that it is more efficient to query all infos in one
        call, rather than have single calls for every info type. 

        It should be called only once per request and resource::
            
            davres = davprovider.getResourceInst(path)
            [..]
            if davres.exists():
                print davres.contentType()
        
        If <path> does not exist, the resulting DAVResource object will return 
        False for davres.exists().
        
        typeList MAY be passed, to specify a list of requested information types.
        The implementation MAY uses this list to avoid expensive calculation of
        unwanted information types.

        See DAVResource for details.

        This method must be implemented.
        """
        raise NotImplementedError()


    def exists(self, path):
        """Return True, if path maps to an existing resource.

        This method must be implemented."""
        raise NotImplementedError()


    def isCollection(self, path):
        """Return True, if path maps to a collection resource.

        This method must be implemented."""
        raise NotImplementedError()


    def isResource(self, path):
        """Return True, if path maps to a simple resource.

        The default implementation returns True for existing non-collections.
        
        This method could be overwritten with a more efficient variant. 
        """
        return self.exists(path) and not self.isCollection(path)
    
    
    # --- Properties -----------------------------------------------------------
     
    def getPropertyNames(self, davres, mode="allprop"):
        """Return list of supported property names in Clark Notation.
        
        @param mode: 'allprop': common properties, that should be sent on 'allprop' requests. 
                     'propname': all available properties.

        This default implementation returns a combination of:
        
        - davres.supportedLivePropertyNames()
        - {DAV:}lockdiscovery and {DAV:}supportedlock, if a lock manager is 
          present
        - a list of dead properties, if a property manager is present
        """
        # TODO: currently, we assume that allprop == propname
        if not mode in ("allprop", "propname"):
            raise ValueError("Invalid mode '%s'." % mode)

        # use a copy
#        propNameList = self.getSupportedLivePropertyNames(davres) [:]
        propNameList = davres.supportedLivePropertyNames()

        if self.lockManager:
            if not "{DAV:}lockdiscovery" in propNameList:
                propNameList.append("{DAV:}lockdiscovery")
            if not "{DAV:}supportedlock" in propNameList:
                propNameList.append("{DAV:}supportedlock")
        
        if self.propManager:
            refUrl = self.getRefUrl(davres.path)
            for deadProp in self.propManager.getProperties(refUrl):
                propNameList.append(deadProp)
                
        return propNameList


    def getProperties(self, davres, mode, nameList=None, namesOnly=False):
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
            nameList = self.getPropertyNames(davres, mode)
        else:
            assert nameList is not None

        propList = []
        for name in nameList:
            try:
                if namesOnly:
                    propList.append( (name, None) )
                else:
                    value = self.getPropertyValue(davres.path, name, davres)
                    propList.append( (name, value) )
            except DAVError, e:
                propList.append( (name, e) )
            except Exception, e:
                propList.append( (name, asDAVError(e)) )
                if self.verbose >= 2:
                    traceback.print_exc(10, sys.stderr)  
                    
        return propList


    def getPropertyValue(self, path, propname, davres=None):
        """Return the value of a property.
        
        path:
            resource path.
        propname:
            is the property name in Clark notation.
        davres:
            DAVResource instance. Contains cached resource information.
            Manadatory for live properties, but may be omitted for 
            '{DAV:}lockdiscovery' or dead properties.
        return value:
            may have different types, depending on the status:
             
            - string or unicode: for standard property values.
            - lxml.etree.Element: for complex values.
            
            If the property is not available, a DAVError is raised.
            
        This default implementation handles ``{DAV:}lockdiscovery`` and
        ``{DAV:}supportedlock`` using the associated lock manager.
        
        All other *live* properties (i.e. propname starts with ``{DAV:}``) are 
        delegated to self.getLivePropertyValue()
        
        Finally, other properties are considered *dead*, and are handled  using 
        the associated property manager. 
        """
        refUrl = self.getRefUrl(path)

#        print "getPropertyValue(%s, %s)" % (path, propname)
        
        if self.lockManager and propname == "{DAV:}lockdiscovery":
            # TODO: we return HTTP_NOT_FOUND if no lockmanager is present. Correct?
            lm = self.lockManager     
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
                ownerEL = etree.XML(lock["owner"])
                activelockEL.append(ownerEL)
                
                timeout = lock["timeout"]
                if timeout < 0:
                    timeout =  "Infinite"
                else:
                    timeout = "Second-" + str(long(timeout - time.time())) 
                etree.SubElement(activelockEL, "{DAV:}timeout").text = timeout
                
                locktokenEL = etree.SubElement(activelockEL, "{DAV:}locktoken")
                etree.SubElement(locktokenEL, "{DAV:}href").text = lock["token"]

                lockRoot = self.getHref(self.refUrlToPath(lock["root"]))
                lockrootEL = etree.SubElement(activelockEL, "{DAV:}lockroot")
                etree.SubElement(lockrootEL, "{DAV:}href").text = lockRoot

            return lockdiscoveryEL            

        elif self.lockManager and propname == "{DAV:}supportedlock":
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
            assert davres is not None, "Must pass DAVResource for querying live properties"
            # Standard live property (raises HTTP_NOT_FOUND if not supported)
            return self.getLivePropertyValue(davres, propname)
        
        # Dead property
        if self.propManager:
            refUrl = self.getRefUrl(path)
            value = self.propManager.getProperty(refUrl, propname)
            if value is not None:
#                return value 
                return etree.XML(value) 

        # No persistence available, or property not found
        raise DAVError(HTTP_NOT_FOUND)               
    

    def setPropertyValue(self, path, propname, value, dryRun=False):
        """Set or remove property value.
        
        value == None means 'remove property'.
        Raise HTTP_FORBIDDEN if property is read-only, or not supported.
        Removing a non-existing prop is NOT an error. 
        
        When dryRun is True, this function should raise errors, as in a real
        run, but MUST NOT change any data.
                 
        @param path:
        @param propname: property name in Clark Notation
        @param value: value == None means 'remove property'.
        @param dryRun: boolean
        """
#        if value is not None and not isinstance(value, (unicode, str, etree._Element)):
        if value is not None and not isinstance(value, (etree._Element)):
            raise ValueError() 
        if self.lockManager and propname in ("{DAV:}lockdiscovery", "{DAV:}supportedlock"):
            raise DAVError(HTTP_FORBIDDEN,  # TODO: Chun used HTTP_CONFLICT 
                           preconditionCode=PRECONDITION_CODE_ProtectedProperty)  
        if propname.startswith("{DAV:}"):
            # raises DAVError(HTTP_FORBIDDEN) if read-only, or not supported
            return self.setLivePropertyValue(path, propname, value, dryRun)
        # Dead property
        if self.propManager:
            # TODO: do we write all proprties?
            # TODO: accept etree._Element
            refUrl = self.getRefUrl(path)
            if value is None:
                return self.propManager.removeProperty(refUrl, propname)
            else:
                value = etree.tostring(value)
                return self.propManager.writeProperty(refUrl, propname, value, dryRun)             

        raise DAVError(HTTP_FORBIDDEN)  # TODO: Chun used HTTP_CONFLICT 


    def removeAllProperties(self, path):
        """Remove all associated dead properties."""
        if self.propManager:
            self.propManager.removeProperties(self.getRefUrl(path))


#    def getSupportedLivePropertyNames(self, davres):
#        """Return list of supported live properties in Clark Notation.
#
#        SHOULD NOT add {DAV:}lockdiscovery and {DAV:}supportedlock.
#        
#        This default implementation uses self.getInfoDict() to figure it out.
#        """
#        propmap = {"created": "{DAV:}creationdate",
#                   "contentType": "{DAV:}getcontenttype",
#                   "isCollection": "{DAV:}resourcetype",
#                   "modified": "{DAV:}getlastmodified",
#                   "displayName": "{DAV:}displayname",
#                   "etag": "{DAV:}getetag",
#                   }
#        if not davres.isCollection():
#            propmap["contentLength"] = "{DAV:}getcontentlength"
#            
#        appProps = []
#        for k, v in propmap.items(): 
#            if k in davres._dict:
#                appProps.append(v)
#        return appProps


    def getLivePropertyValue(self, davres, propname):
        """Return list of supported live properties in Clark Notation.

        SHOULD NOT add {DAV:}lockdiscovery and {DAV:}supportedlock.
        
        This default implementation uses self.getInfoDict() to figure it out.
        """
        if not davres.exists():
            raise DAVError(HTTP_NOT_FOUND)

        if propname == "{DAV:}creationdate":
            return util.getRfc1123Time(davres.created())

        elif propname == "{DAV:}getcontenttype":
            return davres.contentType()
        
        elif propname == "{DAV:}resourcetype":
            if davres.isCollection():
                resourcetypeEL = etree.Element(propname)
                etree.SubElement(resourcetypeEL, "{DAV:}collection")
                return resourcetypeEL            
            return ""   
        
        elif propname == "{DAV:}getlastmodified":
            return util.getRfc1123Time(davres.modified())
        
        elif propname == "{DAV:}getcontentlength":
            if davres.contentLength() is not None:
                return str(davres.contentLength())
        
        elif propname == "{DAV:}getetag":
            return davres.etag()

        elif propname == "{DAV:}displayname":
            return davres.displayName()

        # No persistence available, or property not found
        raise DAVError(HTTP_NOT_FOUND)               


    def setLivePropertyValue(self, path, propname, value, dryRun=False):
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

    def isLocked(self, path):
        """Return True, if URI is locked.
        
        This does NOT check, if path exists.
        """
        if self.lockManager is None:
            return False
        return self.lockManager.isUrlLocked(self.getRefUrl(path))


    def removeAllLocks(self, path):
        if self.lockManager:
            self.lockManager.removeAllLocksFromUrl(self.getRefUrl(path))


    # --- Read / write ---------------------------------------------------------
    
    def createEmptyResource(self, path):
        """Create an empty (length-0) resource.
        
        This default implementation simply raises HTTP_FORBIDDEN.
        
        This method must be implemented by all providers that support locking."""
        raise DAVError(HTTP_FORBIDDEN)               
    

    def createCollection(self, path):
        """Create a new collection.
        
        This default implementation raises HTTP_FORBIDDEN.
        
        The caller must make sure that <path> does not yet exist, and the parent
        is not locked."""
        raise DAVError(HTTP_FORBIDDEN)               

    
    def openResourceForRead(self, path, davres=None):
        """Every provider must override this method."""
        raise NotImplementedError()
    

    def openResourceForWrite(self, path, contenttype=None):
        raise DAVError(HTTP_FORBIDDEN)               

    
    def deleteCollection(self, path):
        raise DAVError(HTTP_FORBIDDEN)               

    
    def deleteResource(self, path):
        raise DAVError(HTTP_FORBIDDEN)               

    
    def copyResource(self, srcLoc, destLoc):
        raise DAVError(HTTP_FORBIDDEN)               


    def remove(self, path):
        """Remove the resource and associated locks and properties.
        
        This default implementation calls self.deleteResource(lco) or 
        .deleteCollection(path), followed by .removeAllProperties(path) and 
        .removeAllLocks(path)
        Errors are raised on failure. 

        This function should NOT be implemented in a recursive way.
        Instead, the caller is responsible to call remove() for all child 
        resources before.
        The caller is also responsible for checking of locks and permissions. 
        """
        if self.isCollection(path):
            self.deleteCollection(path)
        elif self.isResource(path):
            self.deleteResource(path)
        self.removeAllProperties(path)
        self.removeAllLocks(path)


#    def copyFlat(self, srcUrl, destUrl, withProperties):
#        if self.isCollection(path):
#            self.deleteCollection(path)
#        elif self.isResource(path):
#            self.deleteResource(path)
#        self.removeAllProperties(path)
#        self.removeAllLocks(path)
