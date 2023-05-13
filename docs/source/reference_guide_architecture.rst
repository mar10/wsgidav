============
Architecture
============

This document gives a brief introduction to the WsgiDAV application package
(targeted to developers).

.. toctree::
   :maxdepth: 1


WSGI Application Stack
======================
WsgiDAV is a WSGI application.

`WSGI <http://www.python.org/peps/pep-3333.html>`_ stands for Web Server Gateway
Interface, a proposed standard interface between web servers and Python web
applications or frameworks, to promote web application portability across a
variety of web servers. If you are unfamiliar with WSGI, do take a moment to
read the PEP.

As most WSGI applications, WsgiDAV consists of middleware which serve as
pre-filters and post-processors, and the actual application.

WsgiDAV implements this WSGI application stack::

 <Request>
   |
 <Server> -> wsgidav_app.WsgiDavApp (container)
              |
              +-> debug_filter.WsgiDavDebugFilter (middleware, optional)
                    |
                  error_printer.ErrorPrinter (middleware)
                    |
                  http_authenticator.HTTPAuthenticator (middleware)
                    |           \- Uses a domain controller object
                    |
                  dir_browser.WsgiDavDirBrowser (middleware, optional)
                    |
                  request_resolver.RequestResolver (middleware)
                    |
                    *-> request_server.RequestServer (application)
                                \- Uses a DAVProvider object
                                    \- Uses a lock manager object
                                       and  a property  manager object

.. note::
    This is the default stack. Middleware applications and order can be configured using
    ``middleware_stack`` option. You can write your own or extend existing
    middleware and place it on middleware stack.

See the following sections for details.


Building Blocks
===============

DAV Providers
-------------

.. inheritance-diagram:: wsgidav.dav_provider wsgidav.fs_dav_provider
   :parts: 2
   :private-bases:

DAV providers are abstractions layers that are used by the
:class:`~wsgidav.request_server.RequestServer` to access and manipulate DAV resources.

All DAV providers must implement a common interface. This is usually done by
deriving from the abstract base class :class:`~wsgidav.dav_provider.DAVProvider`.

WsgiDAV comes with a DAV provider for file systems, called
:class:`~wsgidav.fs_dav_provider.FilesystemProvider`. That is why WsgiDAV is a 
WebDAV file server out-of-the-box.

There are also a few other modules that may serve as examples on how to plug-in
your own custom DAV providers (see also :doc:`user_guide_custom_providers`).


Property Managers
-----------------

.. inheritance-diagram:: wsgidav.prop_man.property_manager
   :parts: 2
   :private-bases:

DAV providers may use a property manager to support persistence for *dead
properties*.

WsgiDAV comes with two default implementations, one based on a in-memory
dictionary, and a persistent one based on shelve::

    prop_man.property_manager.PropertyManager
    prop_man.property_manager.ShelvePropertyManager

:class:`~wsgidav.prop_man.property_manager.PropertyManager` is used by default,
but :class:`~wsgidav.prop_man.property_manager.ShelvePropertyManager` can be enabled by
uncommenting two lines in the configuration file.

In addition, this may be replaced by a custom version, as long as the required
interface is implemented.


Lock Managers
-------------

.. inheritance-diagram:: wsgidav.lock_man.lock_manager wsgidav.lock_man.lock_storage
   :parts: 2
   :private-bases:

DAV providers have a :class:`~wsgidav.lock_man.lock_manager.LockManager` to support
exclusive and shared write locking.
The lock manager uses a lock storage implementation for persistence.

WsgiDAV comes with two default implementations, one based on a in-memory
dictionary, and a persistent one based on shelve::

    lock_storage.LockStorageDict
    lock_storage.LockStorageShelve

:class:`~wsgidav.lock_man.lock_storage.LockStorageDict` is used by default, but
:class:`~wsgidav.lock_man.lock_storage.LockStorageShelve` can be enabled by uncommenting
two lines in the configuration file.

In addition, this may be replaced by a custom version, as long as the required
interface is implemented.


Domain Controllers
------------------

.. inheritance-diagram:: wsgidav.http_authenticator wsgidav.dc.simple_dc wsgidav.dc.pam_dc wsgidav.dc.nt_dc
   :parts: 2

A domain controller provides user/password checking for a realm to the
HTTPAuthenticator.

WsgiDAV comes with a default implementation that reads a user/password list from
the config file.

However, this may be replaced by a custom version, as long as the required
interface is implemented.

:mod:`wsgidav.dc.nt_dc` is an example for such an extension.


:class:`~wsgidav.dc.simple_dc.SimpleDomainController`
    Default implementation of a domain controller as used by
    :class:`~wsgidav.http_authenticator.HTTPAuthenticator`.


Applications
============

.. inheritance-diagram:: wsgidav.mw.base_mw wsgidav.dir_browser wsgidav.mw.cors wsgidav.mw.debug_filter wsgidav.dav_error wsgidav.error_printer wsgidav.http_authenticator wsgidav.rw_lock wsgidav.wsgidav_app wsgidav.request_server wsgidav.request_resolver
   :parts: 2
   :private-bases:


WsgiDavApp
----------
..
  .. automodule:: wsgidav.wsgidav_app


Cors
----
Middleware :class:`wsgidav.mw.cors.Cors`.
Respond to CORS preflight OPTIONS request and inject CORS headers.

On init:
    Store CORS preferences and prepare header lists.

For every request:
    Add CORS headers to responses.

..
  .. autoclass:: wsgidav.mw.cors.Cors

ErrorPrinter
------------
Middleware :class:`wsgidav.error_printer.ErrorPrinter`.
Handle DAV exceptions and internal errors.

On init:
    Store error handling preferences.

For every request:
    Pass the request to the next middleware.
    If a DAV exception occurs, log info, then pass it on.
    Internal exceptions are converted to HTTP_INTERNAL_ERRORs.


HTTPAuthenticator
-----------------
Middleware :class:`wsgidav.http_authenticator.HTTPAuthenticator`.
Uses a domain controller to establish HTTP authentication.

On init:
    Store the domain controller object that is used for authentication.

For every request:
    if authentication is required and user is not logged in: return authentication
    response.

    Else set these values::

        ``environ['httpauthentication.realm']``
        ``environ['httpauthentication.username']``


WsgiDavDirBrowser
-----------------
Middleware :class:`wsgidav.dir_browser._dir_browser.WsgiDavDirBrowser`.
Handles GET requests on collections to display a HTML directory listing.

On init:

    -

For every request:

    If path maps to a collection:
        Render collection members as directory (HTML table).


RequestResolver
---------------
Middleware :class:`wsgidav.request_resolver.RequestResolver`.
Must be configured as last in `middleware_stack` config option.
Find the mapped DAV-Provider, create a new :class:`~wsgidav.request_server.RequestServer`
instance, and dispatch the request.

On init:

    Store URL-to-DAV-Provider mapping.

For every request:

    Setup ``environ["SCRIPT_NAME"]`` to request realm and and
    ``environ["PATH_INFO"]`` to resource path.

    Then find the registered DAV-Provider for this realm, create a new
    :class:`~wsgidav.request_server.RequestServer` instance, and pass the
    request to it.

    Note: The OPTIONS method for '*' is handled directly.


WsgiDavDebugFilter
------------------
..
  .. automodule:: wsgidav.mw.debug_filter


RequestServer
-------------
Application :class:`wsgidav.request_server.RequestServer`.
Handles one single WebDAV request.

On init:

    Store a reference to the DAV-Provider object.

For every request:

    Handle one single WebDAV method (PROPFIND, PROPPATCH, LOCK, ...) using a
    DAV-Provider instance. Then return the response body or raise an DAVError.

    Note: this object only handles one single request.
