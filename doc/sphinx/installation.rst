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
  * Optionally `lxml <http://codespeak.net/lxml/>`_ (will fall back to xml)


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
