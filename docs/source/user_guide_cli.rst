Command Line Interface
======================

*This section describes how to use WsgiDAV from the command line.*

The WsgiDAV server was tested with these platforms

  * Mac OS X
  * Ubuntu
  * Windows

To serve the ``/tmp`` folder as WebDAV ``/`` share, simply run::

    $ wsgidav --host 0.0.0.0 --port 80 --root /tmp --auth anonymous
    Running without configuration file.
    10:54:16.597 - INFO    : WsgiDAV/4.0.0-a1 Python/3.9.1 macOS-12.0.1-x86_64-i386-64bit
    10:54:16.598 - INFO    : Lock manager:      LockManager(LockStorageDict)
    10:54:16.598 - INFO    : Property manager:  None
    10:54:16.598 - INFO    : Domain controller: SimpleDomainController()
    10:54:16.598 - INFO    : Registered DAV providers by route:
    10:54:16.598 - INFO    :   - '/:dir_browser': FilesystemProvider for path '/Users/martin/prj/git/wsgidav/wsgidav/dir_browser/htdocs' (Read-Only) (anonymous)
    10:54:16.599 - INFO    :   - '/': FilesystemProvider for path '/tmp' (Read-Write) (anonymous)
    10:54:16.599 - WARNING : Basic authentication is enabled: It is highly recommended to enable SSL.
    10:54:16.599 - WARNING : Share '/' will allow anonymous write access.
    10:54:16.599 - WARNING : Share '/:dir_browser' will allow anonymous read access.
    10:54:16.599 - WARNING : Could not import lxml: using xml instead (up to 10% slower). Consider `pip install lxml`(see https://pypi.python.org/pypi/lxml).
    10:54:16.813 - INFO    : Running WsgiDAV/4.0.0-a1 Cheroot/8.5.2 Python 3.9.1
    10:54:16.813 - INFO    : Serving on http://0.0.0.0:80 ...

.. warning::
	Here, WsgiDAV will publish the folder for anonymous access.
	Read :doc:`user_guide_configure` how to set up authentication.


CLI Options
-----------

Use the ``--help`` or ``-h`` argument to get help::

  $ wsgidav --help
  usage: wsgidav [-h] [-p PORT] [-H HOST] [-r ROOT_PATH] [--auth {anonymous,nt,pam-login}] [--server {cheroot,ext-wsgiutils,gevent,gunicorn,paste,uvicorn,wsgiref}]
                [--ssl-adapter {builtin,pyopenssl}] [-v | -q] [-c CONFIG_FILE | --no-config] [--browse] [-V]

  Run a WEBDAV server to share file system folders.

  Examples:

    Share filesystem folder '/temp' for anonymous access (no config file used):
      wsgidav --port=80 --host=0.0.0.0 --root=/temp --auth=anonymous

    Run using a specific configuration file:
      wsgidav --port=80 --host=0.0.0.0 --config=~/my_wsgidav.yaml

    If no config file is specified, the application will look for a file named
    'wsgidav.yaml' in the current directory.
    See
      http://wsgidav.readthedocs.io/en/latest/run-configure.html
    for some explanation of the configuration file format.


  optional arguments:
    -h, --help            show this help message and exit
    -p PORT, --port PORT  port to serve on (default: 8080)
    -H HOST, --host HOST  host to serve from (default: localhost). 'localhost' is only accessible from the local computer. Use 0.0.0.0 to make your application public
    -r ROOT_PATH, --root ROOT_PATH
                          path to a file system folder to publish as share '/'.
    --auth {anonymous,nt,pam-login}
                          quick configuration of a domain controller when no config file is used
    --server {cheroot,ext-wsgiutils,gevent,gunicorn,paste,uvicorn,wsgiref}
                          type of pre-installed WSGI server to use (default: cheroot).
    --ssl-adapter {builtin,pyopenssl}
                          used by 'cheroot' server if SSL certificates are configured (default: builtin).
    -v, --verbose         increment verbosity by one (default: 3, range: 0..5)
    -q, --quiet           decrement verbosity by one
    -c CONFIG_FILE, --config CONFIG_FILE
                          configuration file (default: ('wsgidav.yaml', 'wsgidav.json') in current directory)
    --no-config           do not try to load default ('wsgidav.yaml', 'wsgidav.json')
    --browse              open browser on start
    -V, --version         print version info and exit (may be combined with --verbose)

  Licensed under the MIT license.
  See https://github.com/mar10/wsgidav for additional information.
  $


Use a Configuration File
------------------------
Much more options are available when a configuration file is specified.

.. seealso::
	:doc:`user_guide_configure`


..
  Exit Codes
  ----------

  The CLI returns those exit codes::

      0: OK
      2: CLI syntax error
      3: Aborted by user
