**************************
 WsgiDAV Developers Guide
**************************

This section gives a brief introduction to the WsgiDAV application package 
(targeted to developers).

.. toctree::
   :maxdepth: 1
   
   develop-architecture.rst
   develop-modules.rst
   develop-glossary.rst
   develop-custom-providers.rst


API reference
=============
There is also an `API documentation`_ available.

.. _API documentation : http://apidoc.wsgidav.googlecode.com/hg/html/index.html


test automodule wsgidav.dav_provider
====================================
.. automodule:: wsgidav.dav_provider
   :no-undoc-members:


test automodule wsgidav.fs_dav_provider
=======================================
.. automodule:: wsgidav.fs_dav_provider

test autoclass wsgidav.fs_dav_provider
=======================================
.. autoclass:: wsgidav.fs_dav_provider.FileResource


Overview
========
wsgidav package:

.. automodule:: wsgidav
   :no-members:
   :no-undoc-members:
   :no-inherited-members:
   :no-show-inheritance:

wsgidav package 2:

.. automodule:: wsgidav
	:members:

Classes
=======
.. inheritance-diagram:: wsgidav.dav_provider wsgidav.fs_dav_provider
   :parts: 1
   :private-bases:
   
autosummary
===========
.. autosummary::
   :nosignatures:
   :toctree: _generated
   
   wsgidav.dav_provider
   wsgidav.fs_dav_provider
