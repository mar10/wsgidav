.. _main-index:

############################
|logo| WsgiDAV Documentation
############################

A generic and extendable `WebDAV <http://www.ietf.org/rfc/rfc4918.txt>`_ server
written in Python and based on `WSGI <http://www.python.org/dev/peps/pep-3333/>`_.

:Project:   https://github.com/mar10/wsgidav/
:Version:   |version|, Date: |today|

|gh_badge| |nbsp| |pypi_badge| |nbsp| |lic_badge| |nbsp| |rtd_badge|

.. toctree::
   :hidden:

   Overview<self>
   quickstart
   installation
   user_guide
   reference_guide
   development
   changes


Main Features
=============

- Comes bundled with a server and a file system provider, so we can share a
  directory right away from the command line.
- Designed to run behind any WSGI compliant server.
- Tested with different clients on different platforms (Windows, Linux, macOS).
- Supports online editing of MS Office documents.
- Contains a simple web browser interface.
- SSL support
- Support for authentication using Basic or Digest scheme.
- Passes the `litmus test suite <http://www.webdav.org/neon/litmus/>`_.
- Open architecture allows to :doc:`user_guide_custom_providers`
  (i.e. storage, locking, authentication, virtual file systems, ...).


DAV Explorer
------------
WsgiDAV comes with a slick web interface that allows to explore the DAV share and 
perform basic operations (create, delete, move, copy, rename, ...) directly
in the browser, without the need for additional software or drive mapping. |br|
Up- and downloading of files is supported using drag-and-drop or file dialogs. |br|
Also inline editing of office documents is supported when MS Office or LibreOffice is 
installed on the client machine.

.. image:: DAV_Explorer.png
  :name: WsgiDAV explorer

.. note::

  DAV Explorer is available since version 4.4. |br|
  It has beta status and is not enabled by default, but must be explicitly enabled 
  in the configuration file ``wsgidav.yaml``.


Supported Clients
-----------------

WsgiDAV comes with a web interface and was tested with different clients
(Windows File Explorer, macOS Finder, MS Office, LibreOffice, ...).

.. image:: teaser.png
  :name: WsgiDAV clients

..
  .. seealso::
  	:doc:`run-access`


Quickstart
==========

Install WsgiDAV together with a WSGI server, for example using
`uv <https://docs.astral.sh/uv/>`_::

  $ uv tool install wsgidav --with cheroot

.. note::
   Windows users may prefer ``winget install wsgidav`` or the
   `MSI installer <https://github.com/mar10/wsgidav/releases/latest>`_.
   A `Docker image <https://hub.docker.com/r/mar10/wsgidav/>`_ is available
   as well.

Share a folder with anonymous read-write access (no configuration file
needed)::

  $ wsgidav --host 0.0.0.0 --port 8080 --root /path/to/share --auth anonymous --no-config

Then open `http://HOST:8080/ <http://localhost:8080/>`_ in your browser, or
map it as a network drive in Windows File Explorer, macOS Finder, or a Linux
file manager.

Read :doc:`quickstart` for more installation options (pipx, pip, Docker,
Podman), authentication, and step-by-step instructions to map a drive on
Windows, macOS, and Linux.


.. |logo| image:: logo.png

.. |gh_badge| image:: https://github.com/mar10/wsgidav/actions/workflows/tests.yml/badge.svg
   :alt: Build Status
   :target: https://github.com/mar10/wsgidav/actions/workflows/tests.yml

.. |pypi_badge| image:: https://img.shields.io/pypi/v/wsgidav.svg
   :alt: PyPI Version
   :target: https://pypi.python.org/pypi/wsgidav/

.. |lic_badge| image:: https://img.shields.io/pypi/l/wsgidav.svg
   :alt: License
   :target: https://github.com/mar10/wsgidav/blob/master/LICENSE

.. |rtd_badge| image:: https://readthedocs.org/projects/wsgidav/badge/?version=latest
   :target: https://wsgidav.readthedocs.io/
   :alt: Documentation Status
