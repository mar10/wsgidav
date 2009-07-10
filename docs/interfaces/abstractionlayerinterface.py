
class AbstractionLayerInterface(object):
   """
   This class is an interface for a resource abstraction layer. Implementations of
   this layer for PyFileServer include::
   
      pyfileserver.fileabstractionlayer.FilesystemAbstractionLayer 
      pyfileserver.fileabstractionlayer.ReadOnlyFilesystemAbstractionLayer
   
   All methods must be implemented. You could implement, for example, a read only
   abstraction layer by raising 403 Forbidden for write methods and 409 Conflict for
   write property methods.
   
   ``pyfileserver.processrequesterrorhandler.HTTPRequestException`` instances raised
   within these methods will cause the corresponding error code to be returned.
   Other exceptions will result in a 500 Internal Server Error code to be returned.
   """
   def resolvePath(self, resheadpath, urlelementlist):
      """
      resolves a given url access to a resource path identifier.
      
      Example, in the case of a filesystem, the resource path identifier might
      be the file path. Then, if the server is sharing C:\\test as 
      http://server/testarea, an access to http://server/testarea/dir1/dir2/file3.txt
      will result in a call to resolvePath::
          
         resolvePath('C:\\test', ['dir1','dir2','file3.txt'])

      which should return 'C:\\test\\dir1\\dir2\\file3.txt'.            
      """

   def breakPath(self, resheadpath, respath):      
      """
      the inverse of resolvePath (see above). Given::
         
         breakPath('C:\\test', 'C:\\test\\dir1\\dir2\\file3.txt')
      
      the function should return the list ['dir1','dir2','file3.txt']
      """
   
   def getResourceDescriptor(self, respath):
      """
      respath - path identifier for the resource
      
      returns an array of attribute values (strings) that
      is to be shown on the directory listing in a browser.
      
      for files this would probably be:
      [ resourcedescription, filesize + " B", prettyprint(lastmodified) ]
      """
   
   def getResourceDescription(self, respath):
      """
      respath - path identifier for the resource
      
      returns a string describing the given resource. Given a filesystem, the
      description might be "File" or "Directory"
      """
      
   def getContentType(self, respath):
      """
      respath - path identifier for the resource
      
      returns the content type of the resource, e.g text/html, application/pdf, etc
      """

   def getLastModified(self, respath):
      """
      respath - path identifier for the resource
      
      returns the last modified time, as a number representing the number of seconds
      since the epoch, for the resource. It should return 0 if last modified time
      is not available or not applicable.
      """
   
   def getContentLength(self, respath):
      """
      respath - path identifier for the resource
      
      returns the length of the content, refering to file size or the number of
      bytes to be read from the stream as returned by openResourceForWrite(). This
      is required to be accurate.
      """
   
   def getEntityTag(self, respath):
      """
      respath - path identifier for the resource
      
      returns an Entity Tag for the content. It could return some default
      tag, like the invalid '[]',if the resource does not exist.
      """

   def isCollection(self, respath):
      """
      respath - path identifier for the resource
      
      returns True if resource is a collection, False otherwise      
      """
   
   def isResource(self, respath):
      """
      respath - path identifier for the resource
      
      returns True if resource is a non-collection resource, False otherwise      
      """
   
   def exists(self, respath):
      """
      respath - path identifier for the resource
      
      returns True if resource is a non-collection resource, False otherwise      
      """
   
   def createCollection(self, respath):
      """
      respath - path identifier for the resource
      
      creates a collection corresponding to the resource specified
      """
   
   def deleteCollection(self, respath):
      """
      respath - path identifier for the resource

      deletes a collection corresponding to the resource specified, if
      the collection is empty.
      """

   def supportEntityTag(self, respath):
      """
      respath - path identifier for the resource

      returns True if this resource supports Entity Tags, False otherwise
      
      NO entity tag comparison (headers if, if_match, if_none_match) is done for
      a resource that does not support entity tags. The Etag header will not be
      returned for get.
      """

   def supportLastModified(self, respath):
      """
      respath - path identifier for the resource

      returns True if this resource supports Last Modifed, False otherwise
      
      NO last modified comparison (headers if_modified_since, if_unmodified_since) is
      done for a resource that does not support last modified. The Last Modified
      header will not be returned for get.
      """
   
   def supportContentLength(self, respath):
      """
      respath - path identifier for the resource

      returns True if this resource supports Content Length, False otherwise
      
      if ContentLength is not supported, no Content-Length header will be returned
      for get.
      
      Content Ranges requires Ranges and ContentLength to be supported.      
      """
   
   def supportRanges(self, respath):
      """
      respath - path identifier for the resource

      returns True if this resource supports ranges, False otherwise.
      
      A resource supporting ranges must return a stream for 
      ``openResourceForRead()`` that is ``seek()``-able
      
      Content Ranges requires Ranges and ContentLength to be supported.
      """
   
   def openResourceForRead(self, respath):
      """
      respath - path identifier for the resource
            
      returns a file-like object / stream containing the contents of the
      resource specified.

      The application will close() the stream.      
      """
   
   def openResourceForWrite(self, respath, contenttype=None):
      """
      respath - path identifier for the resource

      contenttype - Content-Type header data given if available.
      
      returns a file-like object / stream that the resource data will 
      be ``write()``-en to. 
      """
   
   def deleteResource(self, respath):
      """
      respath - path identifier for the resource

      deletes the specified non-collection resource.      
      """
   
   def copyResource(self, respath, destrespath):
      """
      respath - source path identifier for the resource
      destrespath - destination path identifier for the resource
      
      copies the specified resource from respath to destrespath. 
      Non-recursive copy.      
      """
   
   def getContainingCollection(self, respath):
      """
      respath - path identifier for the resource
      
      returns the path identifier for the collection containing the resource
      """
   
   def getCollectionContents(self, respath):
      """
      respath - path identifier for the resource

      returns a list of names of resources contained in the collection resource
      specified
      """
      
   def joinPath(self, rescollectionpath, resname):
      """
      rescollectionpath - path identifier for a collection resource
      resname - name (not full path) for a resource
      
      returns the path identifier corresponding to a resource of name resname in
      the collection specified
      """

   def splitPath(self, respath):
      """
      respath - path identifier for the resource

      returns a tuple (a, b), where a is the path identifier of the collection
      containing the resource, and b is the name of the resource.      
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

   def writeProperty(self, respath, propertyname, propertyns, propertyvalue):
      """
      writes propertyvalue to the property {propertyns}propertyname for
      the resource specified by respath
      """

   def removeProperty(self, respath, propertyname, propertyns):
      """
      removes the property {propertyns}propertyname for
      the resource specified by respath
      """

   def getProperty(self, respath, propertyname, propertyns):
      """
      returns the value of the property {propertyns}propertyname for
      the resource specified by respath
      """
   
   def isPropertySupported(self, respath, propertyname, propertyns):
      """
      returns True, if the property {propertyns}propertyname is supported
      by the resource specified by respath, False otherwise
      """
   
   def getSupportedPropertyNames(self, respath):
      """
      returns a list of properties supported for
      the resource specified by respath.
      
      The return list is a list of tuples (propertyns, propertyname)
      """
   
