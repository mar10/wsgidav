***************************
 Sample configuration file 
***************************

The configuration file uses Python syntax to specify these options:
  * List of share-name / WebDAV provider mappings
  * List of users for authentication
  * Optional custom DAV providers (i.e. other than `FilesystemProvider`)
  * Optional custom lock manager, property manager and domain controller
  * (and more)

For a start, you should copy 
`wsgidav.conf <http://wsgidav.googlecode.com/hg/wsgidav/server/sample_wsgidav.conf>`_

and edit it to your needs.
 
.. literalinclude:: ../../wsgidav/wsgidav/server/sample_wsgidav.conf
    :linenos:
    :language: python
