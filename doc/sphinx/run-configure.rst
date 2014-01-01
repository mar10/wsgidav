**********************************
 Configure and Run WsgiDAV Server
**********************************

*This document describes, how to configure and run a WsgiDAV server.*

The WsgiDAV server was tested with these platforms

  * Mac OS X 10.9
  * Ubuntu 13
  * Windows (Win7, Vista, XP)

and these WSGI servers

  * cherrypy.wsgiserver
  * paste.httpserver
  * Pylons
  * wsgidav.ext_wsgiutils_server (bundled with WsgiDAV)
  * wsgiref.simple_server


.. toctree::
   :maxdepth: 1
   
   configuration-file
   run-configure-pylons.rst


Run as stand-alone server
=========================
WsgiDAV is a WSGI application, that can be run by any WSGI compliant server.

This package comes with a built-in WSGI server called `wsgidav` 
(See `wsgidav.wsgidav_server.run_server.py` for details).

In the most simple case, no configuration file is required. The following line 
starts publishing the local folder `/tmp` for anonymous WebDAV access::

    ~/wsgidav$ wsgidav --host=0.0.0.0 --port=80 --root=/tmp

To test it, you may start a browser on ``http://127.0.0.1/``.

However, most of the time we want to specify a configuration file with advanced 
settings::

    ~/wsgidav$ wsgidav --host=0.0.0.0 --port=80 --config=./wsgidav.conf

By default, WsgiDAV will search for a file called ``wsgidav.conf`` in the current
working directory. Use the `-h` option for a list of additional commands::

    ~/wsgidav$ wsgidav -h


Configuration file
==================
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

.. seealso:: :doc:`configuration-file`.


Run inside a 3rd-party WSGI server
==================================
Setup up the configuration dictionary, create a ``WsgiDAVApp`` object and 
pass it to your favorite WSGI server:

.. literalinclude:: ../../wsgidav/wsgidav/server/server_sample.py
   :linenos:
   :language: python


Run inside Pylons
=================

See :doc:`run-configure-pylons` for an example how WsgiDAV can be 
configured as Pylons controller.
