=============
Configuration
=============

*This document describes the configuration options of a WsgiDAV server.*


.. toctree::
   :maxdepth: 1


The :class:`~wsgidav.wsgidav_app.WsgiDAVApp` object is configured by passing
a Python ``dict`` with distinct options, that define

  * Server options (hostname, port, SSL cert, ...)
  * List of share-name / WebDAV provider mappings
  * Optional list of users for authentication
  * Optional custom DAV providers (i.e. other than :class:`~wsgidav.fs_dav_provider.FilesystemProvider`)
  * Optional custom lock manager, property manager and domain controller
  * Advanced debugging options
  * (and more)

This section shows the available options and defaults:

.. literalinclude:: ../../wsgidav/default_conf.py
    :linenos:

When a Python dict is passed to the :class:`~wsgidav.wsgidav_app.WsgiDAVApp`
constructor, its values will override the defaults from above::

    root_path = gettempdir()
    provider = FilesystemProvider(root_path, readonly=False, fs_opts={})

    config = {
        "host": "0.0.0.0",
        "port": 8080,
        "provider_mapping": {"/": provider},
        "verbose": 1,
        }
    app = WsgiDAVApp(config)


Use a Configuration File
------------------------
When running from the CLI (command line interface), *some* settings may be
passed as arguments, e.g.::

    $ wsgidav --host=0.0.0.0 --port=8080 --root=/tmp --auth=anonymous

    Serving on http://0.0.0.0:8080 ...

Much more options are available when a configuration file is used.
By default ``wsgidav.yaml`` and  ``wsgidav.json`` are searched in the
local directory.
An alternative file name can be specified like so::

    $ wsgidav --config=my_config.yaml

To *prevent* the use of a local default configuration file, use this option::

    $ wsgidav --no-config

The options described below can be defined for the CLI either

  * in `YAML <https://yaml.org/spec>`_ syntax inside a wsgidav.yaml file
  * or `JSON <https://www.json.org>`_ syntax inside a wsgidav.json file

.. note::
   The two supported file formats are just different ways for the CLI to
   generate a Python dict that is then passed to the
   :class:`~wsgidav.wsgidav_app.WsgiDAVApp` constructor.

   The YAML format is recommended.

For a start, copy
:download:`YAML Sample Configuration<../../sample_wsgidav.yaml>`
and edit it to your needs.
(Alternatively use
:download:`JSON Sample Configuration<./sample_wsgidav.json>`.)


Verbosity Level
---------------

The verbosity level can have a value from 0 to 5 (default: 3):

=========  ======  ===========  ======================================================
Verbosity  Option  Log level    Remarks
=========  ======  ===========  ======================================================
  0        -qqq    CRITICAL     quiet
  1        -qq     ERROR        no output (excepting application exceptions)
  2        -q      WARN         warnings and errors only
  3                INFO         show single line request summaries (for HTTP logging)
  4        -v      DEBUG        show additional events
  5        -vv     DEBUG        show full request/response header info (HTTP Logging)
                                request body and GET response bodies not shown
=========  ======  ===========  ======================================================


Middleware Stack
----------------

WsgiDAV is built as WSGI application (:class:`~wsgidav.wsgidav_app.WsgiDAVApp`)
that is extended by a list of middleware components which implement additional
functionality.

This stack is defined as a list of WSGI compliant application instances, e.g.::

    from wsgidav.mw.debug_filter import WsgiDavDebugFilter

    debug_filter = WsgiDavDebugFilter(wsgidav_app, next_app, config)

    conf = {
        ...
        "middleware_stack": [
            debug_filter,
            ...
            ],
        ...
        }

If the middleware class constructor has a common signature, it is sufficient to
pass the class instead of the instantiated object.
The built-in middleware derives from :class:`~wsgidav.mw.base_mw.BaseMiddleware`,
so we can simplify as::

    from wsgidav.dir_browser import WsgiDavDirBrowser
    from wsgidav.mw.debug_filter import WsgiDavDebugFilter
    from wsgidav.error_printer import ErrorPrinter
    from wsgidav.http_authenticator import HTTPAuthenticator
    from wsgidav.request_resolver import RequestResolver

    conf = {
        ...
        "middleware_stack": [
            WsgiDavDebugFilter,
            ErrorPrinter,
            HTTPAuthenticator,
            WsgiDavDirBrowser,
            RequestResolver,  # this must be the last middleware item
            ],
        ...
        }

The middleware stack can be configured and extended. The following example
removes the directory browser, and adds a third-party debugging tool::

    import dozer

    # from wsgidav.dir_browser import WsgiDavDirBrowser
    from wsgidav.mw.debug_filter import WsgiDavDebugFilter
    from wsgidav.error_printer import ErrorPrinter
    from wsgidav.http_authenticator import HTTPAuthenticator
    from wsgidav.request_resolver import RequestResolver

    # Enable online profiling and GC inspection. See https://github.com/mgedmin/dozer
    # (Requires `pip install Dozer`):
    dozer_app = dozer.Dozer(wsgidav_app)
    dozer_profiler = dozer.Profiler(dozer_app, None, "/tmp")

    conf = {
        ...
        "middleware_stack": [
            dozer_app,
            dozer_profiler,
            WsgiDavDebugFilter,
            ErrorPrinter,
            HTTPAuthenticator,
            # WsgiDavDirBrowser,
            RequestResolver,  # this must be the last middleware item
            ],
        ...
        }

The stack can also be defined in text files, for example YAML.
Again, we can pass an import path for a WSGI compliant class if the signature
is known.
For third-party middleware however, the constructor's positional arguments
should be explicitly listed::

    ...
    middleware_stack:
        - class: dozer.Dozer
          args:
            - "${application}"
        - class: dozer.Profiler
          args:
            - "${application}"
            - null  # global_conf
            - /tmp  # profile_path
        - wsgidav.mw.debug_filter.WsgiDavDebugFilter
        - wsgidav.error_printer.ErrorPrinter
        - wsgidav.http_authenticator.HTTPAuthenticator
        - wsgidav.dir_browser.WsgiDavDirBrowser
        - wsgidav.request_resolver.RequestResolver

It is also possible to pass options as named args (i.e. 'kwargs')::

    ...
    middleware_stack:
        ...
        - class: dozer.Profiler
          kwargs:
            app: "${application}"
            profile_path: /tmp
        ...

Note that the external middleware must be available, for example by calling
``pip install Doze``, so this will not be possible if WsgiDAV is running from
the MSI installer.


DAVProvider
-----------

A DAVProvider handles read and write requests for all URLs that start with
a given share path.

WsgiDAV comes bundled with :class:`~wsgidav.fs_dav_provider.FilesystemProvider`,
a DAVProvider that serves DAV requests by reading and writing to the server's
file system. |br|
However, custom DAVProviders may be implemented and used, that publish a
database backend, cloud drive, or any virtual data structure.

The ``provider_mapping`` configuration routes share paths to specific
DAVProvider instances.

By default a writable :class:`~wsgidav.fs_dav_provider.FilesystemProvider` is
assumed, but can be forced to read-only.
Note that a DomainController may still restrict access completely or prevent
editing depending on authentication.

Three syntax variants are supported:

1. ``<share_path>: <folder_path>``:
   use ``FilesystemProvider(folder_path)``
2. ``<share_path>: { "root": <folder_path>, "readonly": <bool> }``:
   use ``FilesystemProvider(folder_path, readonly)``
3. ``<share_path>: { "class": <class_path>, args: [arg, ...], kwargs: {"arg1": val1, "arg2": val2, ... }}``
   Instantiate a custom class (derived from ``DAVProvider``) using named
   kwargs.

..
   1. ``<share_path>: { "provider": <class_path>, "args:" ..., "kwargs": ... }``

For example::

    provider_mapping:
        "/": "/path/to/share1"
        "/home": "~"
        "/pub":
            root: "/path/to/share2"
            readonly: true
        "/share3":
            class: path.to.CustomDAVProviderClass
            args:
                - pos_arg1
                - pos_arg2
            kwargs:
                path: '/path/to/share3'
                another_arg: 42


Property Manager
----------------

The built-in :class:`~wsgidav.prop_man.property_manager.PropertyManager``.

Possible options are:

- Disable locking, by passing ``property_manager: null``.
- Enable default storage, which is implemented using a memory-based,
  **not** persistent storage, by passing ``property_manager: true``.
  (This is an alias for ``property_manager: wsgidav.prop_man.property_manager.PropertyManager``)
- Enable an installed or custom storage

Example: Use a persistent shelve based property storage::

    property_manager:
        class: wsgidav.prop_man.property_manager.ShelvePropertyManager
        storage_path: /path/to/wsgidav_locks.shelve


Lock Manager and Storage
------------------------

The built-in :class:`~wsgidav.lock_man.lock_manager.LockManager` requires a
:class:`~wsgidav.lock_man.lock_storage.LockStorageDict` instance.

Possible options are:

- Disable locking, by passing ``lock_storage: null``.
- Enable default locking, which is implemented using a memory-based,
  **not** persistent storage, by passing ``lock_storage: true``.
  (This is an alias for ``lock_storage: wsgidav.lock_man.lock_storage.LockStorageDict``)
- Enable an installed lock storage

A persistent, shelve based :class:`~wsgidav.lock_man.lock_storage.LockStorageShelve`
is also available::

    lock_storage:
        class: wsgidav.lock_man.lock_storage.LockStorageShelve
        kwargs:
            storage_path: /path/to/wsgidav_locks.shelve


Domain Controller
-----------------

The HTTP authentication middleware relies on a domain controller.
Currently three variants are supported.

SimpleDomainController
~~~~~~~~~~~~~~~~~~~~~~

The :class:`wsgidav.dc.simple_dc.SimpleDomainController` allows to authenticate
against a plain mapping of shares and user names.

The pseudo-share ``"*"`` maps all URLs that are not explicitly listed.

A value of ``true`` can be used to enable anonymous access.

Example YAML configuration::

    http_authenticator:
        domain_controller: null  # Same as wsgidav.dc.simple_dc.SimpleDomainController
        accept_basic: true  # Pass false to prevent sending clear text passwords
        accept_digest: true
        default_to_digest: true

    simple_dc:
        user_mapping:
            "*":
                "user1":
                    password: "abc123"
                "user2":
                    password: "qwerty"
            "/pub": true

An optional `roles` list will be passed in `environ["wsgidav.auth.roles"]` to
downstream middleware. This is currently not used by the provided middleware,
but may be handy for custom handlers::

    simple_dc:
        user_mapping:
            "*":
                "user1":
                    password: "abc123"
                    roles: ["editor", "admin"]
                "user2":
                    password: "abc123"
                    roles: []

If no config file is used, anonymous authentication can be enabled on the
command line like::

    $ wsgidav ... --auth=anonymous

which simply defines this setting::

    simple_dc:
        user_mapping:
            "*": true


NTDomainController
~~~~~~~~~~~~~~~~~~
Allows users to authenticate against a Windows NT domain or a local computer.

The :class:`wsgidav.dc.nt_dc.NTDomainController` requires basic authentication
and therefore should use SSL.

Example YAML configuration::

    ssl_certificate: wsgidav/server/sample_bogo_server.crt
    ssl_private_key: wsgidav/server/sample_bogo_server.key
    ssl_certificate_chain: None

    http_authenticator:
        domain_controller: wsgidav.dc.nt_dc.NTDomainController
        accept_basic: true
        accept_digest: false
        default_to_digest: false

    nt_dc:
        preset_domain: null
        preset_server: null

If no config file is used, NT authentication can be enabled on the command
line like::

    $ wsgidav ... --auth=nt


PAMDomainController
~~~~~~~~~~~~~~~~~~~
Allows users to authenticate against a PAM (Pluggable Authentication Modules),
that are at the core of user authentication in any modern linux distribution
and macOS.

The :class:`wsgidav.dc.pam_dc.PAMDomainController` requires basic
authentication and therefore should use SSL.

Example YAML configuration that authenticates users against the server's
known user accounts::

    ssl_certificate: wsgidav/server/sample_bogo_server.crt
    ssl_private_key: wsgidav/server/sample_bogo_server.key
    ssl_certificate_chain: None

    http_authenticator:
        domain_controller: wsgidav.dc.pam_dc.PAMDomainController
        accept_basic: true
        accept_digest: false
        default_to_digest: false

    pam_dc:
        service: "login"
        allow_users: "all"
        #: or "current" for the current user, or a list of user names like deny_users
        # deny_users:
        #   - "root"
        #   - "daemon"

If no config file is used, PAM authentication can be enabled on the command
line like::

    $ wsgidav ... --auth=pam-login


Custom Domain Controllers
~~~~~~~~~~~~~~~~~~~~~~~~~

A custom domain controller can be used like so::

    http_authenticator:
        domain_controller: path.to.CustomDomainController

The constructor must accept two arguments::

    def __init__(self, wsgidav_app, config)

Note that this allows the custom controller to read the configuration dict
and look for a custom section there.


Cors Middleware
---------------

The :class:`wsgidav.mw.cors.Cors` Respond to CORS preflight OPTIONS request and 
inject CORS headers. 
This middleware is available by default, but needs configuration to be enabled.
A minimal (yet )::

    cors:
        #: List of allowed Origins or '*'
        #: Default: false, i.e. prevent CORS
        # allow_origin: null
        allow_origin: '*'

This may be too unspecific though. 
See `Cross-Origin Resource Sharing (CORS) <https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS>`_ .

Annotated YAML configuration::

    cors:
        #: List of allowed Origins or '*'
        #: Default: false, i.e. prevent CORS
        allow_origin: null
        # allow_origin: '*'
        # allow_origin:
        #   - 'https://example.com'
        #   - 'https://localhost:8081'

        #: List or comma-separated string of allowed methods (returned as
        #: response to preflight request)
        allow_methods:
        # allow_methods: POST,HEAD
        #: List or comma-separated string of allowed header names (returned as
        #: response to preflight request)
        allow_headers:
        #   - X-PINGOTHER
        #: List or comma-separated string of allowed headers that JavaScript in
        #: browsers is allowed to access.
        expose_headers:
        #: Set to true to allow responses on requests with credentials flag set
        allow_credentials: false
        #: Time in seconds for how long the response to the preflight request can
        #: be cached (default: 5)
        max_age: 600
        #: Add custom response headers (dict of header-name -> header-value items)
        #: (This is not related to CORS or required to implement CORS functionality)
        add_always:
        #    'X-Foo-Header: 'qux'


Sample ``wsgidav.yaml``
-----------------------

The `YAML <https://yaml.org/spec>`_ syntax is the recommended
format to define configuration:

:download:`Download Sample Configuration<../../sample_wsgidav.yaml>`.

.. literalinclude:: ../../sample_wsgidav.yaml
    :linenos:


Sample ``wsgidav.json``
-----------------------

We can also use a `JSON <https://www.json.org>`_ file for configuration.
The structure is identical to the YAML format.

See the :doc:`./sample_wsgidav.json` example.
(Note that the parser allows JavaScript-style comments)


Configuration Tips
------------------

Running Behind a Reverse Proxy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If WsgiDAV is running behind a reverse proxy, ... 

For example, when `nginx <https://docs.nginx.com/>`_ is used to expose the
local WsgiDAV share ``http://127.0.0.1:8080/public_drive`` as
``http://example.com/drive``, the configuration files may look like this:

``wsgidav.yaml`` ::

    host: 127.0.0.1
    port: 8080
    mount_path: "/drive"
    provider_mapping:
        "/public_drive":  # Exposed as http://HOST/drive by nginx reverse proxy
            root: "fixtures/share"

``nginx.conf``::

    http {
        ...
        server {
            listen       80;
            server_name  example.com;
            ...
            location /drive/ {
                proxy_pass http://127.0.0.1:8080/public_drive/;
                proxy_set_header X-Forwarded-Proto $scheme;
                proxy_set_header X-Forwarded-Host $host;
            }
            # If dir browser is enabled for WsgiDAV:
            location /drive/:dir_browser/ {
                proxy_pass http://127.0.0.1:8080/:dir_browser/;
            }

See the `nginx docs <https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/>`_
for details.
