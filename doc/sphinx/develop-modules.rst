*****************
 WsgiDAV Modules
*****************

This document gives a brief introduction to the WsgiDAV application package 
(targeted to developers).

.. note::
   This documentation is under construction.
 
.. note:: 
   There is also an `API documentation`_ available.

.. toctree::
   :maxdepth: 1


API documentation
=================
Follow this link to browse the `API documentation`_.


DAV providers
=============
DAV providers are abstractions layers that are used by the ``RequestServer`` to
access and manipulate DAV resources.

All DAV providers must implement a common interface. This is usually done by 
deriving from the abstract base class ``dav_provider.DAVProvider``.

WsgiDAV comes with a DAV provider for file systems, called 
``fs_dav_provider.FilesystemProvider``. That is why WsgiDAV is a WebDAV file
server out-of-the-box. 

There are also a few other modules that may serve as examples on how to plug-in
your own custom DAV providers: :doc:`addons`.
See also :doc:`develop-custom-providers`. 


FilesystemProvider
==================
.. automodule:: wsgidav.fs_dav_provider


Property Managers
=================
DAV providers may use a property manager to support persistence for *dead 
properties*.  

WsgiDAV comes with two default implementations, one based on a in-memory 
dictionary, and a persistent one based in shelve::

    property_manager.PropertyManager
    property_manager.ShelvePropertyManager

``PropertyManager`` is used by default, but ``ShelvePropertyManager`` can be 
enabled by uncommenting two lines in the configuration file.

In addition, this may be replaced by a custom version, as long as the required
interface is implemented.

.. automodule:: wsgidav.property_manager
  

Lock Managers
=============
DAV providers may use a lock manager to support exclusive and shared write 
locking.  

WsgiDAV comes with two default implementations, one based on a in-memory 
dictionary, and a persistent one based in shelve::

    lock_manager.LockManager
    lock_manager.ShelveLockManager

``LockManager`` is used by default, but ``ShelveLockManager`` can be 
enabled by uncommenting two lines in the configuration file.

In addition, this may be replaced by a custom version, as long as the required
interface is implemented.

.. automodule:: wsgidav.lock_manager


Domain controllers
==================
A domain controller provides user/password checking for a realm to the 
HTTPAuthenticator.

WsgiDAV comes with a default implementation that reads a user/password list from
the config file.

However, this may be replaced by a custom version, as long as the required
interface is implemented.

``wsgidav.addons.nt_domain_controller`` is an example for such an extension.   


Other objects
=============
``wsgidav.domain_controller.WsgiDAVDomainController``
    Default implementation of a domain controller as used by ``HTTPAuthenticator``.

                                               
  
.. _API documentation : http://apidoc.wsgidav.googlecode.com/hg/html/index.html
