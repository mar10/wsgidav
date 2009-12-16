======
README
======

:Authors: - Ho Chun Wei, fuzzybr80(at)gmail.com (original PyFileServer)
          - Martin Wendt
:Project: WsgiDAV, http://wsgidav.googlecode.com/
:Copyright: Lesser GNU Public License, see LICENSE file attached with package
:Abstract: This document gives a brief introduction to the WsgiDAV application package.


.. contents:: Table Of Contents



What is WsgiDAV?
================
WsgiDAV is a WSGI web application for sharing filesystem directories 
over WebDAV.

For a more detailed discussion of the package, go to the project page
<http://wsgidav.googlecode.com/>



Installing WsgiDAV
==================

1. Get and install the latest release of Python, available from

       http://www.python.org/

   Python 2.3 or later is required; Python 2.4.1 or later is
   recommended.

2. Use the latest WsgiDAV release. Get the code from:

       http://wsgidav.googlecode.com/


3. Unpack the archive in a temporary directory (**not** directly in
   Python's ``site-packages``) and install with the standard ::

       python setup.py install

   WsgiDAV requires the PyXML library <http://pyxml.sourceforge.net/>
   to run, and the installation process will install it if it is
   not present on the system.
   
   

Configuring WsgiDAV
===================

WsgiDAV reads its configuration from a user-specified configuration file. 
An example of this file is given in the package as 'WsgiDAV-example.conf'. 

You should make a copy of this file to use as your configuration file. The file
is self-documented and you can modify any settings as required.

Refer to the TUTORIAL documentation for an example.


Running WsgiDAV
===============

WsgiDAV comes bundled with a simple wsgi webserver.

Running as standalone server
----------------------------

To run as a standalone server using the bundled ext_wsgiutils_server.py:: 

      usage: python ext_wsgiutils_server.py [options] [config-file]
      
      config-file:
        The configuration file for WsgiDAV. if omitted, the application
        will look for a file named 'WsgiDAV.conf' in the current directory
      
      options:
        --port=PORT  Port to serve on (default: 8080)
        --host=HOST  Host to serve from (default: localhost, which is only
                     accessible from the local computer; use 0.0.0.0 to make your
                     application public)
        -h, --help   show this help message and exit
      
      
Running using other web servers
-------------------------------

To run it with other WSGI web servers, you can::
   
      from pyfileserver.mainappwrapper import PyFileApp
      publish_app = PyFileApp('WsgiDAV.conf')   
      # construct the application with configuration file 
      # if configuration file is omitted, the application
      # will look for a file named 'WsgiDAV.conf'
      # in the current directory
 
where ``publish_app`` is the WSGI application to be run, it will be called with 
``publish_app(environ, start_response)`` for each incoming request, as 
described in WSGI <http://www.python.org/peps/pep-0333.html>

Note: if you are using the paster development server (from Paste 
<http://pythonpaste.org>), you can copy ``ext_wsgi_server.py`` to 
``<Paste-installation>/paste/servers`` and use this server to run the 
application by specifying ``server='ext_wsgiutils'`` in the ``server.conf`` 
or appropriate paste configuration.


Help and Documentation
======================

For further help or documentation, please refer to the project web page or
send a query to the mailing list.

Project Page: WsgiDAV <http://wsgidav.googlecode.com/>

