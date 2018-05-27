=============
Configuration
=============

*This document describes the configuration options of a WsgiDAV server.*


.. toctree::
   :maxdepth: 1

   sample_wsgidav_conf


The :class:`~wsgidav.wsgidav_app.WsgiDAVApp` object is configured by passing
a Python ``dict`` with distinct options, that define

  * Server options (hostname, port, SSL cert, ...)
  * List of share-name / WebDAV provider mappings
  * Optional list of users for authentication
  * Optional custom DAV providers (i.e. other than `FilesystemProvider`)
  * Optional custom lock manager, property manager and domain controller
  * Advanced debugging options
  * (and more)

This section shows the available options and defaults:

.. literalinclude:: ../../wsgidav/default_conf.py
    :linenos:

When a Python dict is passed to the :class:`~wsgidav.wsgidav_app.WsgiDAVApp` constructor,
its values will override those defaults::

    root_path = gettempdir()
    provider = FilesystemProvider(root_path)

    config = {
        "host": "0.0.0.0",
        "port": 8080,
        "provider_mapping": {"/": provider},
        "verbose": 1,
        }
    app = WsgiDAVApp(config)


Use a Configuration File
------------------------
When running from the CLI (command line interface), *some* settings may be passed as arguments,
e.g.::

	$ wsgidav --host=0.0.0.0 --port=8080 --root=/tmp

	Serving on http://0.0.0.0:8080 ...

Much more options are available when a configuration file is used.
By default ``wsgidav.yaml``,  ``wsgidav.json``, and ``wsgidav.conf`` are searched in the
local directory.
An alternative file name can be specified like so::

	$ wsgidav --config=my_config.yaml

To *prevent* the use of of a local default configuration file, use this option::

  $ wsgidav --no-config

The options described below can be defined for the CLI either

  * in `YAML <http://yaml.org/spec/1.2/spec.html>`_ syntax inside a wsgidav.yaml file,
  * in `JSON <http://www.json.org>`_ syntax inside a wsgidav.json file, or
  * in Python syntax inside a wsgidav.conf file.

.. note::
   The three supported file formats are just different ways for the CLI to
   generate a Python dict that is then passed to the
   :class:`~wsgidav.wsgidav_app.WsgiDAVApp` constructor.

   The YAML format is recommended.

For a start, copy
:download:`YAML Sample Configuration<../../sample_wsgidav.yaml>`
and edit it to your needs.
(Alternatively use
:download:`JSON Sample Configuration<../sample_wsgidav.json>` or
:download:`Python Sample Configuration<../sample_wsgidav.conf>`.)


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
that is extended by a list of middleware components that implement additional
functionality.

This stack is defined as a list WSGI compliant application instances, e.g.::

    from wsgidav.debug_filter import WsgiDavDebugFilter

    debug_filter = WsgiDavDebugFilter(wsgidav_app, next_app, config)

    conf = {
        ...
        "middleware_stack": [
            debug_filter,
            ...
            ],
        ...
        }

If the middleware class constructor has a common signature, it is sufficient to pass the class
instead of the instantiated object.
The built-in middleware derives from :class:`~wsgidav.middleware.BaseMiddleware`, so we can
simplify as::

    from wsgidav.addons.dir_browser import WsgiDavDirBrowser
    from wsgidav.debug_filter import WsgiDavDebugFilter
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
            RequestResolver,
            ],
        ...
        }

The middleware stack can be configured and extended. The following example removes the
directory browser, and adds a third-party debugging tool::

    import dozer

    # from wsgidav.addons.dir_browser import WsgiDavDirBrowser
    from wsgidav.debug_filter import WsgiDavDebugFilter
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
            RequestResolver,
            ],
        ...
        }

The stack can also be defined in text files, for example YAML.
Again, we can pass an import path for a WSGI compliant class if the signature
is known.
For third-party middleware however, the constructor's positional arguments should be
explicitly listed::

    ...
    middleware_stack:
        - dozer.Dozer:
            - "${application}"
        - dozer.Profiler:
            - "${application}"
            - null  # global_conf
            - /tmp  # profile_path
        - wsgidav.debug_filter.WsgiDavDebugFilter
        - wsgidav.error_printer.ErrorPrinter
        - wsgidav.http_authenticator.HTTPAuthenticator
        - wsgidav.addons.dir_browser.WsgiDavDirBrowser
        - wsgidav.request_resolver.RequestResolver

Note that the external middleware must be available, for example by calling
``pip install Doze``, so this will not be possible if WsgiDAV is running from the
MSI installer.


Property Manager
----------------

.. todo:: TODO


Lock Manager
------------

.. todo:: TODO


Domain Controller
-----------------

Example:
use a domain controller that allows users to authenticate against a
Windows NT domain or a local computer.
The :class:`~wsgidav.addons.nt_domain_controller.NTDomainController`
requires basic authentication::

    from wsgidav.addons.nt_domain_controller import NTDomainController
    domaincontroller = NTDomainController(presetdomain=None, presetserver=None)
    acceptbasic = True
    acceptdigest = False
    defaultdigest = False


Sample ``wsgidav.yaml``
-----------------------

The `YAML <http://yaml.org/spec/1.2/spec.html>`_ syntax is probably the most
concise format to define configuration:

:download:`Download Sample Configuration<../sample_wsgidav.conf>`.

.. literalinclude:: ../../sample_wsgidav.yaml
    :linenos:


Sample ``wsgidav.json``
-----------------------

We can also use a `JSON <http://www.json.org>`_ file for configuration.
The structure is identical to the YAML format.

Note that the parser tolerates JavaScript-style comments:

.. literalinclude:: ../sample_wsgidav.json
    :linenos:
    :language: json


Sample ``wsgidav.conf``
-----------------------

This format uses plain Python syntax, which allows us to use Python data structures,
and even write helper functions, etc.

This is the most powerful and flexible format, that can be used in complex scenarios.

See the :doc:`sample_wsgidav_conf` example.
