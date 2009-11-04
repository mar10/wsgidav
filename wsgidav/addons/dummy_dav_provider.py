"""
:Author: Martin Wendt
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

Sample implementation of a DAV provider that does nothing.

+--------------------------------------------------------+
| TODO: this module has to be ported to the current API. |
+--------------------------------------------------------+

This could be a starting point, when creating own resource providers for
WsgiDAV:

  1. Copy and rename this module
  2. Rename the class. 
     Don't forget the super(DummyDAVProvider, ...).
  3. Implement member functions 

See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
"""
__docformat__ = "reStructuredText"

from wsgidav.dav_provider import DAVProvider

 

#===============================================================================
# DummyDAVProvider
#===============================================================================

class DummyDAVProvider(DAVProvider):
    def __init__(self, options=None):
        super(DummyDAVProvider, self).__init__()
        # The constructor may define arguments, that then will be stored here:
        self.verbose = 1
        self.options = options
    
    def __repr__(self):
        return "%s with options %s" % (self.__class__.__name__, self.options)


    def getPreferredPath(self, path):
        """Return preferred mapping for a resource URL.
        
        Different URLs may map to the same resource, e.g.:
            '/a/b' == '/A/b' == '/a/b/'
        getPreferredPath() returns the same value for all these variants, e.g.:
            '/a/b/'
        """
        return super(DummyDAVProvider, self).getPreferredPath(path)
        

#    def getNormPath(self, path):
#        """Return the quoted, preferred mapping of a resource, relative to the server.
#        
#        Starts with a '/'. Collections also have a trailing '/'.
#        @rtype: quoted,  ISO-8859-1 encoded byte string.
#        """
#        return super(DummyDAVProvider, self).getNormPath(path)


    def getRefUrl(self, path):
        """Return the quoted, unique mapping of a resource, relative to the server.
        
        Byte string, ISO-8859-1 encoded.
        Starts with a '/'. Collections also have a trailing '/'.
        
        This is basically the same as normPath, but deals with 'virtual locations'
        as well.
        Since it is always unique for one resource, <refUrl> is used as key for the
        lock- and property storage.
        
        e.g. '/a/b' == '/A/b' == '/bykey/123' == '/byguid/as532'
        
        getRefUrl() returns the same value for all these URLs, so it can be
        used for locking and persistence. 

        DAV providers that allow these virtual-mappings should  override this 
        method.

        See also comments in module request_server.
        @rtype: quoted,  ISO-8859-1 encoded byte string.
        """
        return super(DummyDAVProvider, self).getRefUrl(path)


    def getHref(self, path):
        """This value can be passed to XML responses.
        
        We are using the path-absolute option. ie starting with '/'.
        @see http://www.webdav.org/specs/rfc4918.html#rfc.section.8.3
        """
        return super(DummyDAVProvider, self).getHref(path)


    def refUrlToPath(self, refUrl):
        """Convert a refUrl to a path, by stripping the mount prefix."""
        return super(DummyDAVProvider, self).refUrlToPath(refUrl)


    def getResourceInfo(self, path):
        """Return info dictionary for path.
        
        The result may be used to display HTML directory pages to the user.
        It is not intended to be used for implementing WebDAV APIs.
        
        (This default implementation should be overridden by a more efficient
        variant.)

        name: (str) name of resource
        resourceType: (str) type of resource, e.g. 'Directory', 'File'
        contentType: (str) MIME type of content
        isCollection: (bool) 
        displayName: (str) display name of resource
        size: (int) resource size in bytes
        modified: modification date of resource (in seconds, compatible with time module)
        created: creation date of resource (in seconds, compatible with time module)
        """
        return super(DummyDAVProvider, self).getResourceInfo(path)
    

    def getPropertyNames(self, davres, mode="allprop"):
        """Return list of supported property names in Clark Notation.
        
        @param mode: 'allprop': common properties, that should be send on 'allprop' requests. 
                     'propname': all available properties.
        """
        return super(DummyDAVProvider, self).getPropertyNames(davres, mode)


    def getProperties(self, davres, mode, nameList=None, namesOnly=False):
        """Return properties as list of 2-tuples (name, value).

        <name> is the property name in Clark notation.
        <value> may have different types, depending on the status:
         
            - string or unicode: for standard property values.
            - lxml.etree.Element: for complex values.
            - DAVError in case of errors.
            - None: if namesOnly was passed.

        @param path: 
        @param mode: "allprop", "propname", or "named"
        @param nameList: list of property names in Clark Notation (only for mode 'named')
        @param namesOnly: return None for <value>  
        """
        return super(DummyDAVProvider, self).getProperties(davres, mode, nameList, namesOnly)


    def getPropertyValue(self, path, propname, davres=None):
        return super(DummyDAVProvider, self).getPropertyValue(path, propname, davres)


    def setPropertyValue(self, path, name, value, dryRun=False):
        """Set or remove property value.
        
        value == None means 'remove property'.
        Raise HTTP_FORBIDDEN if property is read-only, or not supported.
        Removing a non-existing prop is NOT an error. 
        
        When dryRun is True, this function should raise errors, as in a real
        run, but MUST NOT change any data.
                 
        @param path:
        @param name: property name in Clark Notation
        @param value: value == None means 'remove property'.
        @param dryRun: boolean
        """
        return super(DummyDAVProvider, self).setPropertyValue(path, name, value, dryRun)


    def removeAllProperties(self, path):
        return super(DummyDAVProvider, self).removeAllProperties(path)


    def createEmptyResource(self, path):
        raise NotImplementedError()
    

    def isLocked(self, path):
        """Return True, if URI is locked.
        
        This does NOT check, if path exists.
        """
        return super(DummyDAVProvider, self).isLocked(path)


    def remove(self, path):
        return super(DummyDAVProvider, self).remove(path)


#    def copyFlat(self, srcUrl, destUrl, withProperties):
#        return super(DummyDAVProvider, self).copyFlat(locsrcUrl, destUrl, withProperties)


    def removeAllLocks(self, path):
        return super(DummyDAVProvider, self).removeAllLocks(path)

    #---------------------------------------------------------------------------
     
    def getSupportedLivePropertyNames(self, davres):
        """Return list of supported live properties in Clark Notation.

        Do NOT add {DAV:}lockdiscovery and {DAV:}supportedlock.
        """
        return NotImplementedError()  # Provider must override this


    def getLivePropertyValue(self, davres, propname):
        """Set list of supported live properties in Clark Notation.
        
        Raise HTTP_NOT_FOUND if property is not supported.
        Do NOT handle {DAV:}lockdiscovery and {DAV:}supportedlock.
        """
        return NotImplementedError()  # Provider must override this


    def setLivePropertyValue(self, path, name, value, dryRun=False):
        """Set or remove a live property value.
        
        value == None means 'remove property'.
        Raise HTTP_FORBIDDEN if property is read-only, or not supported.

        When dryRun is True, this function should raise errors, as in a real
        run, but MUST NOT change any data.
                 
        This function MUST NOT handle {DAV:}lockdiscovery and {DAV:}supportedlock,
        since this is done by the calling .setPropertyValue() function.

        TODO; ?This will usually be forbidden, since live properties cannot be
        removed.

        @param path:
        @param name: property name in Clark Notation
        @param value: value == None means 'remove property'.
        @param dryRun: boolean
        """
        return NotImplementedError()  # Provider must override this
