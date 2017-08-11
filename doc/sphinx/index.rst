.. _main-index:

#############################
WsgiDAV Documentation
#############################

:Project: WsgiDAV, https://github.com/mar10/wsgidav/
:Copyright: Licensed under `The MIT License <https://raw.github.com/mar10/wsgidav/master/LICENSE>`_
:Author: Martin Wendt
:Release: |version|
:Date: |today|

..
	WsgiDAV Documentation |logo|

WsgiDAV is a generic `WebDAV <http://www.ietf.org/rfc/rfc4918.txt>`_ server
written in Python and based on `WSGI <http://www.python.org/dev/peps/pep-0333/>`_.

(WsgiDAV is a `refactored version of PyFileServer <https://github.com/mar10/wsgidav/blob/master/doc/changelog04.md>`_ written by Ho Chun Wei.)

Status
======
Version 2.x introduces Python 3 compatibility and is considered stable.

.. seealso::
	The `Change Log <https://github.com/mar10/wsgidav/blob/master/CHANGELOG.md>`_.


Main Features
=============
- Comes bundled with a server and a file system provider, so we can share a
  directory right away from the command line.
- Designed to run behind any WSGI compliant server.
- Tested with different clients on different platforms (Windows, Unix, Mac).
- Supports online editing of MS Office documents.
- Contains a simple web browser interface.
- SSL support
- Support for authentication using Basic or Digest scheme.
- Passes `litmus test suite <http://www.webdav.org/neon/litmus/>`_.
- Open architecture allows to write custom providers (i.e. storage, locking,
  authentication, ...).


Quickstart
===========
**Install**

Releases are hosted on `PyPI <https://pypi.python.org/pypi/WsgiDAV>`_.
Install like::

	$ pip install -U wsgidav

Or install the latest (potentially unstable) development version::

	$ pip install git+https://github.com/mar10/wsgidav.git

.. seealso ::
	:doc:`run-install` for details and how to install with developer access.


**Run Server**

To serve the ``/tmp`` folder as WebDAV ``/`` share, simply run::

	$ wsgidav --host=0.0.0.0 --port=80 --root=/tmp

Much more options are available when a configuration file is specified.
By default ``wsgidav.conf`` is searched in the local directory. Otherwise a
file name can be specified::

	$ wsgidav --config=my_config.conf

.. seealso ::
	:doc:`run-configure`


Supported Clients
=================
WsgiDAV comes with a web interface and was tested with different clients
(Windows File Explorer and drive mapping, MS Office, Ubuntu, Mac OS X, ...).

.. image :: https://raw.github.com/mar10/wsgidav/master/doc/teaser.png

.. seealso ::
	:doc:`run-access`


More info
=========

.. toctree::
   :maxdepth: 1
   :numbered:

   run-install.rst
   run-configure.rst
   run-access.rst
   addons.rst
   develop.rst
   faq.rst

contents

.. contents::
	:local:
	:depth: 1

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. |logo| image:: https://raw.github.com/mar10/wsgidav/master/logo.png
