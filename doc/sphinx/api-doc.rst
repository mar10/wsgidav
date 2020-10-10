=======
API Doc
=======

.. toctree::
   :maxdepth: 1

..
   pkg_wsgidav

..
  Classes
  =======
  .. inheritance-diagram:: wsgidav.dav_provider wsgidav.fs_dav_provider
     :parts: 1
     :private-bases:


  Packages
  ========

Package ``wsgidav``
-------------------
.. autosummary::
   :toctree: _autosummary

   wsgidav.compat
   wsgidav.dav_error
   wsgidav.dav_provider
   wsgidav.debug_filter
   wsgidav.dir_browser
   wsgidav.error_printer
   wsgidav.fs_dav_provider
   wsgidav.http_authenticator
   wsgidav.lock_manager
   wsgidav.lock_storage
   wsgidav.middleware
   wsgidav.request_resolver
   wsgidav.request_server
   wsgidav.rw_lock
   wsgidav.util
   wsgidav.wsgidav_app
   wsgidav.xml_tools


Package ``wsgidav.dc``
--------------------------
.. autosummary::
   :toctree: _autosummary

   wsgidav.dc.simple_dc
   wsgidav.dc.nt_dc


Package ``wsgidav.prop_man``
--------------------------
.. autosummary::
   :toctree: _autosummary

   wsgidav.prop_man.property_manager
   wsgidav.prop_man.couch_property_manager
   wsgidav.prop_man.mongo_property_manager


Package ``wsgidav.samples``
---------------------------
.. autosummary::
   :toctree: _autosummary

   wsgidav.samples.dav_provider_tools
   wsgidav.samples.hg_dav_provider
   wsgidav.samples.mongo_dav_provider
   wsgidav.samples.mysql_dav_provider
   wsgidav.samples.virtual_dav_provider


Package ``wsgidav.server``
--------------------------
.. autosummary::
   :toctree: _autosummary

   wsgidav.server.ext_wsgiutils_server
   wsgidav.server.run_reloading_server
   wsgidav.server.server_cli
   wsgidav.server.server_sample
