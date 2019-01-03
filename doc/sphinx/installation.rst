Installation
============

This section describes, how a WsgiDAV server is installed.

.. seealso::

  If you plan to contribute to the WsgiDAV project, check out :doc:`development`
  for details on how to install in development mode.


Preconditions
-------------

WsgiDAV server was tested with these operating systems (among others):

  * Linux (Ubuntu 13)
  * Mac OS X 10.9
  * Windows (Windows 10, 8, 7, Vista, XP)

WsgiDAV requires

  * `Python <https://www.python.org/downloads/>`_ 2.7 or 3.4+
  * A WSGI compliant web server. |br|
    WsigDAV is a WSGI application, that must be served by a compliant web server.
    Among others, there are `CherryPy / Cheroot <https://github.com/cherrypy/cheroot>`_,
    `gevent <http://www.gevent.org/>`_,
    `gunicorn <http://gunicorn.org/>`_,
    `mod_wsgi <http://modwsgi.readthedocs.io/>`_,
    `uWSGI <https://uwsgi-docs.readthedocs.io/>`_,
    and many more.
    |br|
    Simply choose a server that suites you best.
    If unsure, we recommend Cheroot (the server that backs CherryPy) which has
    `proven to be pretty performant and stable <https://blog.appdynamics.com/engineering/a-performance-analysis-of-python-wsgi-servers-part-2/>`_.
    Cheroot comes also bundled with the MSI installer.
  * Optionally `lxml <http://codespeak.net/lxml/>`_ for slight performance
    improvements (speed up performance of PROPPATCH requests up to 10%).


Unix / Linux
------------

Releases are hosted on `PyPI <https://pypi.python.org/pypi/WsgiDAV>`_ and can
be installed using `pip <http://www.pip-installer.org/>`_::

  $ pip install --upgrade wsgidav

Or install the latest (potentially unstable) development version directly
from GitHub::

	$ pip install git+https://github.com/mar10/wsgidav.git

In order to run the WsgiDAV server from the command line, we also need a WSGI server
such as `Cheroot <https://cheroot.readthedocs.io/>`_::

  $ pip install cheroot

The following examples were tested on Ubuntu 13.04.
Install lxml (optional)::

    $ sudo apt-get install python-lxml

If everything is cool, this should work now::

    $ wsgidav --version -v
    WsgiDAV/2.4.0 Python/3.6.1 Darwin-17.5.0-x86_64-i386-64bit
    $ wsgidav --help

..
    $ wsgidav --version
    bash-3.2$     2.3.1


Windows
-------

Install the preconditions if neccessary.
Basically the same as for `Unix / Linux`_

.. note::

   MS Windows users that only need the command line interface may prefer the
   `MSI installer <https://github.com/mar10/wsgidav/releases>`_.


Docker
------

An experimental Docker image that exposes a local directory using WebDAV
is available here:
https://hub.docker.com/r/mar10/wsgidav/

::

    $ docker pull mar10/wsgidav
    $ docker run --rm -it -p <PORT>:8080 -v <ROOT_FOLDER>:/var/wsgidav-root mar10/wsgidav

for example::

    $ docker run --rm -it -p 8080:8080 -v c:/temp:/var/wsgidav-root mar10/wsgidav

Then open (or enter this URL in Windows File Explorer or any other WebDAV client)
http://localhost:8080/
