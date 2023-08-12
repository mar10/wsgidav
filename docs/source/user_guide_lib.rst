-----------------
Using the Library
-----------------

.. toctree::
   :hidden:


This section describes how to use the ``wsgidav`` package to implement custom
WebDAV servers.


.. todo::
   This documentation is still under construction.


The ``wsgidav`` package can be used in Python code::

  $ python
  >>> from wsgidav import __version__
  >>> __version__
  '2.3.1'


Run Inside a WSGI Server
------------------------

The WsgiDAV server was tested with these WSGI servers:

  * `Cheroot <https://cheroot.cherrypy.dev/>`_
  * `gevent <https://www.gevent.org/>`_
  * `Gunicorn <https://gunicorn.org/>`_
  * `Uvicorn <https://www.uvicorn.org/>`_
  * `wsgiref <https://docs.python.org/3/library/wsgiref.html>`_
  * ... but any WSGI compliant server should work


In order to run WsgiDAV, we need to create an instance of :class:`~wsgidav.wsgidav_app.WsgiDAVApp`,
pass options, and mount it on a WSGI compliant web server. |br|
Here we keep most of the default options and use the
`cheroot WSGI server <https://cheroot.cherrypy.org/>`_ ::

  from cheroot import wsgi
  from wsgidav.wsgidav_app import WsgiDAVApp

  config = {
      "host": "0.0.0.0",
      "port": 8080,
      "provider_mapping": {
          "/": "/Users/joe/pub",
        },
      "verbose": 1,
    }
  app = WsgiDAVApp(config)

  server_args = {
      "bind_addr": (config["host"], config["port"]),
      "wsgi_app": app,
  }
  server = wsgi.Server(**server_args)

  try:
      server.start()
  except KeyboardInterrupt:
      print("Received Ctrl-C: stopping...")
  finally:    
      server.stop()

Options are passed as Python dict, see the :doc:`user_guide_configure` for
details.

By default, the :class:`~wsgidav.fs_dav_provider.FilesystemProvider` is used.
This provider creates instances of :class:`~wsgidav.fs_dav_provider.FileResource`
and :class:`~wsgidav.fs_dav_provider.FolderResource` to represent files and
directories respectively.

This is why the example above will publish the directory ``/User/joe/pub`` as
``http://HOST:8080/``.

..
    See the :mod:`~wsgidav.server.server_cli` for more examples.

See the :doc:`source_server_cli` for more examples.


Custom Providers
----------------

If we want to implement custom behavior, we can define our own variant of a
(derived from :class:`~wsgidav.dav_provider.DAVProvider`), which typically also
uses custom instances of :class:`~wsgidav.dav_provider.DAVNonCollection` and
:class:`~wsgidav.dav_provider.DAVCollection`.

::

    ...
    from bar_package import FooProvider
    ...
    config = {
        "host": "0.0.0.0",
        "port": 8080,
        "provider_mapping": {
            "/dav": FooProvider(),
        },
        "verbose": 1,
    }
    app = WsgiDAVApp(config)
    ...


Logging
-------

By default, the library initializes and uses a
`python logger <https://docs.python.org/library/logging.html>`_ named 'wsgidav' and
sub-loggers named like 'wsgidav.wsgidav_app', etc.

By default, the wsgidav logger only has a ``NullHandler`` assigned and does not
propagate to the root logger, so it is *silent*.

This logger can be enabled like so::

    config = {
        ...
        logging: {
            "enable": True,
        }
    }
    app = WsgiDAVApp(config)
    ...

.. note::

    Prior to v4.3.0 an application had to call 
    ``wsgidav.util.init_logging(config)`` explicitly.

.. note::

    The CLI calls :func:`util.init_logging` on startup, so it logs to stdout as 
    configured by the ``verbose`` and ``logging.enable_loggers`` options.
