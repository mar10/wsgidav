# (c) 2009-2011 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Simple example how to a run WsgiDAV in a 3rd-party WSGI server.
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
    "propsmanager": True,      # True: use property_manager.PropertyManager                    
    "locksmanager": True,      # True: use lock_manager.LockManager                   
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

# Or we could use default the server that is part of the WsgiDAV package:
#from wsgidav.server import ext_wsgiutils_server
#ext_wsgiutils_server.serve(config, app)
