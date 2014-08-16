**************************
 WsgiDAV API Doc
**************************

This section gives a brief introduction to the WsgiDAV application package 
(targeted to developers).

.. toctree::
   :maxdepth: 1
   

Overview
========
wsgidav package:


Classes
=======
.. inheritance-diagram:: wsgidav.dav_provider wsgidav.fs_dav_provider
   :parts: 1
   :private-bases:

   
Packages
========
wsgidav
-------
.. autosummary::
   :toctree: _generated
   
   wsgidav.dav_error
   wsgidav.dav_provider
   wsgidav.debug_filter
   wsgidav.dir_browser
   wsgidav.domain_controller
   wsgidav.error_printer
   wsgidav.fs_dav_provider
   wsgidav.http_authenticator
   wsgidav.lock_manager
   wsgidav.lock_storage
   wsgidav.middleware
   wsgidav.property_manager
   wsgidav.request_resolver
   wsgidav.request_server
   wsgidav.rw_lock
   wsgidav.util
   wsgidav.version
   wsgidav.wsgidav_app
   wsgidav.xml_tools


wsgidav.samples
---------------
.. autosummary::
   :toctree: _generated
   
   wsgidav.samples.dav_provider_tools
   wsgidav.samples.mongo_dav_provider
   wsgidav.samples.virtual_dav_provider


wsgidav.addons
--------------
.. autosummary::
   :toctree: _generated
   
   wsgidav.addons.couch_property_manager
   wsgidav.addons.hg_dav_provider
   wsgidav.addons.mongo_property_manager
   wsgidav.addons.mysql_dav_provider
   wsgidav.addons.nt_domain_controller

wsgidav.server
--------------
.. autosummary::
   :toctree: _generated
   
   wsgidav.server.ext_wsgiutils_server
   wsgidav.server.run_reloading_server
   wsgidav.server.run_server
   wsgidav.server.server_sample
