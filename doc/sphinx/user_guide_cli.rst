Command Line Interface
======================

*This section describes how to use WsgiDAV from the command line.*

The WsgiDAV server was tested with these platforms

  * Mac OS X 10.9 - 10.13
  * Ubuntu 13 - 16
  * Windows (Win 7 - 10, Vista, XP)

To serve the ``/tmp`` folder as WebDAV ``/`` share, simply run::

	$ wsgidav --host=0.0.0.0 --port=80 --root=/tmp
	WARNING: share '/' will allow anonymous access.
	Running WsgiDAV/2.3.1 Cheroot/6.0.0 Python/3.6.1
	Serving on http://127.0.0.1:8080 ...

.. warning::
	By default, WsgiDAV will publish the folder for anonymous access.
	Read :doc:`user_guide_configure` how to set up authentication.


CLI Options
-----------

Use the ``--help`` or ``-h`` argument to get help::

	$ wsgidav --help
	usage: wsgidav [-h] [-p PORT] [-H HOST] [-r ROOT_PATH]
	               [--server {cheroot,cherrypy-wsgiserver,ext-wsgiutils,flup-fcgi,flup-fcgi-fork,paste,wsgiref}]
	               [--ssl-adapter {builtin,pyopenssl}] [-v] [-q] [-c CONFIG_FILE]
	               [--no-config] [-V]

	Run a WEBDAV server to share file system folders.

	Examples:

	  Share filesystem folder '/temp':
	    wsgidav --port=80 --host=0.0.0.0 --root=/temp

	  Run using a specific configuration file:
	    wsgidav --port=80 --host=0.0.0.0 --config=~/wsgidav.conf

	  If no config file is specified, the application will look for a file named
	  'wsgidav.conf' in the current directory.
	  See
	    http://wsgidav.readthedocs.io/en/latest/run-configure.html
	  for some explanation of the configuration file format.


	optional arguments:
	  -h, --help            show this help message and exit
	  -p PORT, --port PORT  port to serve on (default: 8080)
	  -H HOST, --host HOST  host to serve from (default: localhost). 'localhost' is only accessible from the local computer. Use 0.0.0.0 to make your application public
	  -r ROOT_PATH, --root ROOT_PATH
	                        path to a file system folder to publish as share '/'.
	  --server {cheroot,cherrypy-wsgiserver,ext-wsgiutils,flup-fcgi,flup-fcgi-fork,paste,wsgiref}
	                        type of pre-installed WSGI server to use (default: cheroot).
	  --ssl-adapter {builtin,pyopenssl}
	                        used by 'cheroot' server if SSL certificates are configured (default: builtin.
	  -v, --verbose         increment verbosity by one (default: 1, range: 0..5)
	  -q, --quiet           set verbosity 0: suppress any output except for errors
	  -c CONFIG_FILE, --config CONFIG_FILE
	                        configuration file (default: wsgidav.conf in current directory)
	  --no-config           do not try to load default wsgidav.conf
	  -V, --version         show program's version number and exit

	Licensed under the MIT license.
	See https://github.com/mar10/wsgidav for additional information.
	$


Use a Configuration File
------------------------
Much more options are available when a configuration file is specified.
By default ``wsgidav.conf`` and ``wsgidav.json`` is searched in the local directory. |br|
An alternative file name can be specified like so::

	$ wsgidav --config=my_config.conf

To *prevent* the use of of a local default configuration file, use this option::

  $ wsgidav --no-config

.. seealso::
	:doc:`user_guide_configure`


..
  Exit Codes
  ----------

  The CLI returns those exit codes::

      0: OK
      2: CLI syntax error
      3: Aborted by user
