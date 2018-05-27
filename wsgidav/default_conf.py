# (c) 2009-2018 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
::

     _      __         _ ___  ___ _   __
    | | /| / /__ ___  (_) _ \/ _ | | / /
    | |/ |/ (_-</ _ `/ / // / __ | |/ /
    |__/|__/___/\_, /_/____/_/ |_|___/
               /___/

Default confguration.
"""
from wsgidav.addons.dir_browser import WsgiDavDirBrowser
from wsgidav.debug_filter import WsgiDavDebugFilter
from wsgidav.error_printer import ErrorPrinter
from wsgidav.http_authenticator import HTTPAuthenticator
from wsgidav.request_resolver import RequestResolver

__docformat__ = "reStructuredText"

# Use these settings, if config file does not define them (or is totally missing)
DEFAULT_VERBOSE = 3

DEFAULT_CONFIG = {
    "mount_path": None,  # Application root, e.g. <mount_path>/<share_name>/<res_path>
    "provider_mapping": {},
    "host": "localhost",
    "port": 8080,
    "server": "cheroot",

    "add_header_MS_Author_Via": True,
    "unquote_path_info": False,  # See #8
    "re_encode_path_info": None,  # (See #73) None: activate on Python 3
    #    "use_text_files": False,

    "propsmanager": None,  # True: use property_manager.PropertyManager
    "locksmanager": True,  # True: use lock_manager.LockManager

    # HTTP Authentication Options
    "user_mapping": {},       # dictionary of dictionaries
    # None: domain_controller.WsgiDAVDomainController(user_mapping)
    "domaincontroller": None,
    "acceptbasic": True,      # Allow basic authentication, True or False
    "acceptdigest": True,     # Allow digest authentication, True or False
    "defaultdigest": True,    # True (default digest) or False (default basic)
    # Name of a header field that will be accepted as authorized user
    "trusted_auth_header": None,

    # Error printer options
    "catchall": False,

    "enable_loggers": [
    ],

    # Verbose Output
    # 0 - no output
    # 1 - no output (excepting application exceptions)
    # 2 - show warnings
    # 3 - show single line request summaries (for HTTP logging)
    # 4 - show additional events
    # 5 - show full request/response header info (HTTP Logging)
    #     request body and GET response bodies not shown
    "verbose": DEFAULT_VERBOSE,

    "dir_browser": {
        # "enable": True,               # Render HTML listing for GET requests on collections
        # List of fnmatch patterns:
        "ignore": [],
        "response_trailer": "",       # Raw HTML code, appended as footer
        # Send <dm:mount> response if request URL contains '?davmount'
        "davmount": False,
        # Add an 'open as webfolder' link (requires Windows clients):
        "ms_mount": False,
        "ms_sharepoint_plugin": True,  # Invoke MS Offce documents for editing using WebDAV
        "ms_sharepoint_urls": False,  # Prepend 'ms-word:ofe|u|' to URL for MS Offce documents
        },
    "middleware_stack": [
        WsgiDavDebugFilter,
        ErrorPrinter,
        HTTPAuthenticator,
        WsgiDavDirBrowser,
        RequestResolver,
        ],
}
