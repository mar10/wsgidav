Installation
============

This section describes, how a WsgiDAV server is installed.

.. seealso::

  If you plan to contribute to the WsgiDAV project, check out :doc:`development`
  for details on how to install in development mode.


Preconditions
-------------

WsgiDAV server was tested with these operating systems (among others):

  * Linux
  * Mac OS
  * Windows

WsgiDAV requires

  * `Python <https://www.python.org/downloads/>`_ 3.6 or later.
  * A WSGI compliant web server. |br|
    WsigDAV is a WSGI application, that must be served by a compliant web server.
    Among others, there are
    `Cheroot <https://cheroot.cherrypy.dev/>`_,
    `gevent <https://www.gevent.org/>`_,
    `Gunicorn <https://gunicorn.org/>`_,
    `Uvicorn <https://www.uvicorn.org/>`_,
    `wsgiref <https://docs.python.org/3/library/wsgiref.html>`_,
    and many more.
    |br|
    Simply choose a server that suites you best.
    If unsure, we recommend Cheroot (the server that backs CherryPy) which has
    `proven to be pretty performant and stable <https://blog.appdynamics.com/engineering/a-performance-analysis-of-python-wsgi-servers-part-2/>`_.
    Cheroot comes also bundled with the MSI installer.
  * Optionally `lxml <http://codespeak.net/lxml/>`_ for slight performance
    improvements (speed up performance of PROPPATCH requests up to 10%).


Linux / macOS
-------------

Releases are hosted on `PyPI <https://pypi.python.org/pypi/WsgiDAV>`_ and can
be installed using `pip <http://www.pip-installer.org/>`_.
Using a virtual environment is recommend::

  $ mkdir wsgidav_test
  $ cd wsgidav_test
  $ wsgidav_test % python -m venv .venv
  $ wsgidav_test % source .venv/bin/activate
  $ (.venv) wsgidav_test % python -m pip install -U pip
  $ (.venv) wsgidav_test % python -m pip install wsgidav cheroot lxml
  $ (.venv) wsgidav_test % wsgidav --root . --auth anonymous --browse


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
    WsgiDAV/4.0.1 Python/3.9.1(64 bit) macOS-12.1-x86_64-i386-64bit
    Python from: /Users/joe/prj/git/test_pip/.venv/bin/python
    $ wsgidav --help


.. seealso::

   `Deploying WebDAV on Debian 10 using WsgiDAV <https://www.vultr.com/docs/deploying-webdav-on-debian-10-using-wsgidav>`_.


Windows
-------

Install the preconditions if necessary.
Basically the same as for `Linux / macOS`_

.. note::
   MS Windows users that only need the command line interface may prefer the
   `MSI installer <https://github.com/mar10/wsgidav/releases>`_ or install
   using the Windows Package Manager::

     > winget install wsgidav


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
