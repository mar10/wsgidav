
class PropertyManagerInterface(object):
    """
    +----------------------------------------------------------------------+
    | TODO: document this interface                                        |
    | For now, see wsgidav.lock_manager instead                            |
    +----------------------------------------------------------------------+ 

    This class is an interface for a PropertyManager.
    Implementations of a property manager in WsgiDAV include::
      
        <wsgidav.property_manager.PropertyManager>_
        wsgidav.property_manager.ShelvePropertyManager
      
    All methods must be implemented.
   
    The url variable in methods refers to the relative URL of a resource. e.g. the 
    resource http://server/share1/dir1/dir2/file3.txt would have a url of 
    '/share1/dir1/dir2/file3.txt'
      
      
    All methods must be implemented.
   
    The url variables in methods refers to the relative URL of a resource. e.g. the 
    resource http://server/share1/dir1/dir2/file3.txt would have a url of 
    '/share1/dir1/dir2/file3.txt'
   
   Properties and WsgiDAV
   ----------------------
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
      ``wsgidav.lock_manager`` and dead properties library in
      ``wsgidav.property_manager``
         
   Dead properties
      They refer to arbitrarily assigned properties not actively maintained. 
   
      These properties are implemented by the dead properties library in
      ``wsgidav.property_manager``
   
   """
