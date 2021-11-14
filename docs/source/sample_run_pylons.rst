******************************
 Running as Pylons controller
******************************


.. toctree::
   :maxdepth: 1

This example shows how configure a Pylons application, so that URLs starting
with `/dav/...` are handled by WsgiDAV. (Tested with Pylons 0.9.7)

First, we create a URL mapping by adding these lines to
``<pylons_project>/config/routing.py``::

    # CUSTOM ROUTES HERE
    # Add WsgiDAV server at /dav
    map.connect('wdavroot', '/dav', path_info='/', controller='wdav')
    map.connect('wdavres', '/dav/{path_info:.*}', controller='wdav')


Then add the controller by creating a new file
``<pylons_project>/controllers/wdav.py`` with this content::

    # -*- coding: utf-8 -*-
    from tempfile import gettempdir
    from wsgidav.fs_dav_provider import FilesystemProvider
    from wsgidav.wsgidav_app import DEFAULT_CONFIG, WsgiDAVApp

    def _make_app():
        rootpath = gettempdir()
        provider = FilesystemProvider(rootpath)

        config = DEFAULT_CONFIG.copy()
        config.update({
            "mount_path": "/dav",
            "provider_mapping": {"/": provider},
            "user_mapping": {},
            "verbose": 1,
            })
        return WsgiDAVApp(config)

    WdavController = _make_app()


Note that we have to use the `mount_path` option to tell WsgiDAV about the
application root.

In the example above, we used a root share ('`/`'), so WebDAV resources will
be available as

``http://192.168.0.2:5000/dav/resource.bin``


If the provider is configured with a share name::

    config.update({
        "mount_path": "/dav",
        "provider_mapping": {"/my_share": provider},
        ...
        })

the WebDAV resources will be available as

``http://192.168.0.2:5000/dav/my_share/resource.bin``
