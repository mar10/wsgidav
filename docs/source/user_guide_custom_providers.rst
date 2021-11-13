========================
Writing Custom Providers
========================

.. note::
   This documentation is under construction.

Samples and Addons for WsgiDAV
------------------------------

.. toctree::
   :hidden:
   :maxdepth: 1

   addons-mercurial.rst
   addons-mongo.rst
   addons-mysql.rst
   addons-clouddav.rst
   addons-virtual.rst

   addons-ntdc.rst
   addons-mongo-propman
   addons-couch-propman


.. note::
  Not all samples have yet been ported to WsgiDAV 2.x.


:doc:`addons-mercurial`
    WebDAV provider that publishes a Mercurial repository.
:doc:`addons-mongo`
    WebDAV provider that publishes a mongoDB database.
:doc:`addons-mysql`
    Implementation of a WebDAV provider that provides a very basic, read-only
    resource layer emulation of a MySQL database.
:doc:`addons-clouddav`
    Implementation of a WebDAV provider that implements a virtual file system
    built on Google App Engine's data store ('Bigtable').
    This project also implements a lock storage provider that uses memcache.
:doc:`addons-virtual`
    Sample implementation of a DAV provider that provides a browsable,
    multi-categorized resource tree.
:doc:`addons-ntdc`
    Implementation of a domain controller that allows users to authenticate
    against a Windows NT domain or a local computer (used by HTTPAuthenticator).
:doc:`addons-mongo-propman`
    Implementation of a property manager, that stores dead properties in
    mongoDB (used by WebDAV providers).
:doc:`addons-couch-propman`
    Implementation of a property manager, that stores dead properties in
    CouchDB (used by WebDAV providers).
