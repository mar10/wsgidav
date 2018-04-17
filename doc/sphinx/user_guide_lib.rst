-----------------
Using the Library
-----------------

.. toctree::
   :hidden:

..
   sample_wsgi_server
   sample_run_pylons


This section describes how to use the ``wsgidav`` package to implement custom
WebDAV servers.

The ``wsgidav`` package can be used in Python code::

  $ python
  >>> from wsgidav import __version__
  >>> __version__
  '2.3.1'


Run Inside a WSGI Server
------------------------

The WsgiDAV server was tested with these WSGI servers:

  * Cheroot
  * cherrypy.wsgiserver
  * paste.httpserver
  * Pylons
  * wsgidav.ext_wsgiutils_server (bundled with WsgiDAV)
  * wsgiref.simple_server


In order to run WsgiDAV, we need to create an instance of :class:`~wsgidav.wsgidav_app.WsgiDAVApp`,
pass options, and mount it on a WSGI compliant web server. |br|
Here we keep most of the default options and use the
`cheroot WSGI server <https://cheroot.cherrypy.org/>`_ ::

  from cheroot import wsgi
  from wsgidav.wsgidav_app import WsgiDAVApp

  config = {
      "host": "0.0.0.0",
      "port": 8080,
      "mount_path": "/dav",
      "root": "/User/joe/pub",
      "verbose": 1,
      }

  app = WsgiDAVApp(config)

  server_args = {
      "bind_addr": (config["host"], config["port"]),
      "wsgi_app": app,
      }
  server = wsgi.Server(**server_args)
  server.start()

Options are passed as Python dict, see the :doc:`user_guide_configure` for details.

By default, the :class:`~wsgidav.fs_dav_provider.FilesystemProvider` is used.
This provider creates instances of :class:`~wsgidav.fs_dav_provider.FileResource`
and :class:`~wsgidav.fs_dav_provider.FolderResource` to represent files and
directories respectively.

This is why the example above will publish the directory ``/User/joe/pub`` as
``http://HOST:8080/dav``.

See the :doc:`sample_wsgi_server` for another example.


Run Inside Pylons
=================

See :doc:`sample_run_pylons` for an example how WsgiDAV can be
configured as Pylons controller.


Custom Providers
----------------

If we want to implement custom behavior, we can define our own variant of a
(derived from :class:`~wsgidav.dav_provider.DAVProvider`), which typically also
uses custom instances of :class:`~wsgidav.dav_provider.DAVNonCollection` and
:class:`~wsgidav.dav_provider.DAVCollection`.

::

    from cheroot import wsgi
    from wsgidav.wsgidav_app import WsgiDAVApp
    from bar_package import FooProvider

    config = {
        "host": "0.0.0.0",
        "port": 8080,
        "provider_mapping": {
            "/dav": FooProvider(),
            },
        "verbose": 1,
        }

    app = WsgiDAVApp(config)



Logging
-------

By default, the library initializes and uses a
`python logger <https://docs.python.org/library/logging.html>`_ named 'wsgidav'.
This logger can be customized like so::

    import logging

    logger = logging.getLogger("wsgidav")
    logger.setLevel(logging.DEBUG)

and replaced like so::

    import logging
    import logging.handlers
    from wsgidav.util import set_wsgidav_logger

    custom_logger = logging.getLogger("my.logger")
    log_path = "/my/path/wsgidav.log"
    handler = logging.handlers.WatchedFileHandler(log_path)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    custom_logger.addHandler(handler)

    set_wsgidav_logger(custom_logger)


.. note::

    The CLI calls ``set_wsgidav_logger(None)`` on startup, so it logs to stdout
    (and stderr).
