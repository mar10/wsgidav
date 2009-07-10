
class PropertyManagerInterface(object):

   """
   This class is an interface for a PropertyManager. Implementations for the 
   property manager in PyFileServer include::
      
      pyfileserver.propertylibrary.PropertyManager
      
   All methods must be implemented.
   
   The url variables in methods refers to the relative URL of a resource. e.g. the 
   resource http://server/share1/dir1/dir2/file3.txt would have a url of 
   '/share1/dir1/dir2/file3.txt'
   
   """

   """
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
   
   """

   def getProperties(self, normurl):
      """
      return a list of properties for url specified by normurl
      
      return list is a list of tuples (a, b) where a is the property namespace
      and b the property name
      """
   
   def getProperty(self, normurl, propname, propns):
      """
      return the value of the property for url specified by normurl where
      propertyname is propname and property namespace is propns
      """
   
   def writeProperty(self, normurl, propname, propns, propertyvalue):
      """
      write propertyvalue as value of the property for url specified by 
      normurl where propertyname is propname and property namespace is propns
      """
   
   def removeProperty(self, normurl, propname, propns):
      """
      delete the property for url specified by normurl where
      propertyname is propname and property namespace is propns
      """
   
   def removeProperties(self, normurl):
      """
      delete all properties from url specified by normurl
      """
         
   def copyProperties(self, origurl, desturl):
      """
      copy all properties from url specified by origurl to url specified by desturl
      """
      