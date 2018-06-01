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
    "server": "cheroot",
    "server_args": {},

    "host": "localhost",
    "port": 8080,

    "mount_path": None,  # Application root, e.g. <mount_path>/<share_name>/<res_path>
    "provider_mapping": {},

    "add_header_MS_Author_Via": True,
    "unquote_path_info": False,  # See issue #8
    "re_encode_path_info": None,  # (See issue #73) None: activate on Python 3

    "property_manager": None,  # True: use property_manager.PropertyManager
    "lock_manager": True,  # True: use lock_manager.LockManager

    "middleware_stack": [
        WsgiDavDebugFilter,
        ErrorPrinter,
        HTTPAuthenticator,
        WsgiDavDirBrowser,
        RequestResolver,
        ],

    # HTTP Authentication Options
    "http_authenticator": {
        "accept_basic": True,      # Allow basic authentication, True or False
        "accept_digest": True,     # Allow digest authentication, True or False
        "default_to_digest": True,    # True (default digest) or False (default basic)
        # Name of a header field that will be accepted as authorized user
        "trusted_auth_header": None,
        },

    # None: domain_controller.WsgiDAVDomainController(user_mapping)
    "domain_controller": None,
    "user_mapping": {},

    # Verbose Output
    # 0 - no output
    # 1 - no output (excepting application exceptions)
    # 2 - show warnings
    # 3 - show single line request summaries (for HTTP logging)
    # 4 - show additional events
    # 5 - show full request/response header info (HTTP Logging)
    #     request body and GET response bodies not shown
    "verbose": DEFAULT_VERBOSE,

    # Error printer options
    "error_printer": {
        "catch_all": True,  # False,
        },

    "enable_loggers": [],

    "dir_browser": {
        # "enable": True,               # Render HTML listing for GET requests on collections
        # List of fnmatch patterns:
        "ignore": [
            ".DS_Store",  # macOS folder meta data
            "._*",  # macOS hidden data files
            "Thumbs.db",  # Windows image previews
            ],
        "icon": True,
        "response_trailer": True,  # Raw HTML code, appended as footer (True: use a default)
        "show_user": True,  # Show authenticated user an realm
        # Send <dm:mount> response if request URL contains '?davmount'
        "davmount": False,
        # Add an 'open as webfolder' link (requires Windows clients):
        "ms_mount": False,
        "ms_sharepoint_plugin": True,  # Invoke MS Offce documents for editing using WebDAV
        "ms_sharepoint_urls": False,  # Prepend 'ms-word:ofe|u|' to URL for MS Offce documents
        },
}
