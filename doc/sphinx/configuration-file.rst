***************************
 Sample configuration file 
***************************

The configuration file uses Python syntax to specify these options:
  * Server options (hostname, port, SSL cert, ...)
  * List of share-name / WebDAV provider mappings
  * List of users for authentication
  * Optional custom DAV providers (i.e. other than `FilesystemProvider`)
  * Optional custom lock manager, property manager and domain controller
  * Advanced debugging options
  * (and more)

For a start, you should copy 
:download:`Sample Configuration<../../wsgidav.conf.sample>` or 
:download:`Annotated Sample Configuration<../annotated_wsgidav.conf>`
and edit it to your needs.
 
.. literalinclude:: ../annotated_wsgidav.conf
    :linenos:
    :language: python
