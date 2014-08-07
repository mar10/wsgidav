**********************
 WsgiDAV Architecture
**********************

This document gives a brief introduction to the WsgiDAV application package 
(targeted to developers).

.. seealso:: 
   :doc:`api-doc`

.. toctree::
   :maxdepth: 1


WSGI application stack
----------------------
WsgiDAV is a WSGI application.

WSGI <http://www.python.org/peps/pep-0333.html> stands for Web Server Gateway
Interface, a proposed standard interface between web servers and Python web 
applications or frameworks, to promote web application portability across a 
variety of web servers. If you are unfamiliar with WSGI, do take a moment to 
read the PEP. 

As most WSGI applications, WsgiDAV consists of middleware which serve as 
pre-filters and post-processors, and the actual application.

WSGI application stack::

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

This is default stack. Middleware order can be configured using 
``middleware_stack`` option. You can write your own or extend existing 
middleware and place it on middleware stack.

See the following sections for details.


                                                
WsgiDavApp
----------
.. automodule:: wsgidav.wsgidav_app


WsgiDavDebugFilter
------------------
.. automodule:: wsgidav.debug_filter


ErrorPrinter
------------
Middleware ``error_printer.ErrorPrinter``
Handle DAV exceptions and internal errors.

On init:
    Store error handling preferences.
    
For every request:
    Pass the request to the next middleware. 
    If a DAV exception occurs, log info, then pass it on. 
    Internal exceptions are converted to HTTP_INTERNAL_ERRORs.  


HTTPAuthenticator
-----------------
Middleware ``http_authenticator.HTTPAuthenticator``
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
Middleware ``dir_browser.WsgiDavDirBrowser``
Handles GET requests on collections to display a HTML directory listing.

On init:

    -
    
For every request:

    If path maps to a collection: 
        Render collection members as directory (HTML table).  


RequestResolver
---------------
Middleware ``request_resolver.RequestResolver``
Find the mapped DAV-Provider, create a new RequestServer instance, and dispatch 
the request.
 
On init:

    Store URL-to-DAV-Provider mapping.
              
For every request:

    Setup ``environ["SCRIPT_NAME"]`` to request realm and and 
    ``environ["PATH_INFO"]`` to resource path.
    
    Then find the registered DAV-Provider for this realm, create a new 
    ``RequestServer`` instance, and pass the request to it.
    
    Note: The OPTIONS method for '*' is handled directly.


RequestServer
-------------
Application ``request_server.RequestServer``
Handles one single WebDAV request.
 
On init:

    Store a reference to the DAV-Provider object.
              
For every request:

    Handle one single WebDAV method (PROPFIND, PROPPATCH, LOCK, ...) using a 
    DAV-Provider instance. Then return the response body or raise an DAVError.
    
    Note: this object only handles one single request.  

                                              