# -*- coding: iso-8859-1 -*-
"""
server_sample
=============

:Author: Martin Wendt, moogle(at)wwwendt.de 
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

Simple example how to a run WsgiDAV in a 3rd-party WSGI server.

See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
"""
from tempfile import gettempdir
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.version import __version__
from wsgidav.wsgidav_app import DEFAULT_CONFIG, WsgiDAVApp

__docformat__ = "reStructuredText"


rootpath = gettempdir()
provider = FilesystemProvider(rootpath)

config = DEFAULT_CONFIG.copy()
config.update({
    "provider_mapping": {"/": provider},
    "user_mapping": {},
    "verbose": 1,
    "enable_loggers": [],
    "propsmanager": None,      # None: use property_manager.PropertyManager                    
    "locksmanager": None,      # None: use lock_manager.LockManager                   
    "domaincontroller": None,  # None: domain_controller.WsgiDAVDomainController(user_mapping)
    })
app = WsgiDAVApp(config)

# For an example. use paste.httpserver
# (See http://pythonpaste.org/modules/httpserver.html for more options)
from paste import httpserver
httpserver.serve(app, 
                 host="localhost", 
                 port=8080,
                 server_version="WsgiDAV/%s" % __version__,
                 )

# Or use default the server that is part of the WsgiDAV package:
#from wsgidav.server import ext_wsgiutils_server
#ext_wsgiutils_server.serve(config, app)
