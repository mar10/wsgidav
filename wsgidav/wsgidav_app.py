# -*- coding: utf-8 -*-
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

WSGI container, that handles the HTTP requests. This object is passed to the
WSGI server and represents our WsgiDAV application to the outside.

On init:

    Use the configuration dictionary to initialize lock manager, property manager,
    domain controller.

    Create a dictionary of share-to-provider mappings.

    Initialize middleware objects and RequestResolver and setup the WSGI
    application stack.

For every request:

    Find the registered DAV provider for the current request.

    Add or modify info in the WSGI ``environ``:

        environ["SCRIPT_NAME"]
            Mount-point of the current share.
        environ["PATH_INFO"]
            Resource path, relative to the mount path.
        environ["wsgidav.provider"]
            DAVProvider object that is registered for handling the current
            request.
        environ["wsgidav.config"]
            Configuration dictionary.
        environ["wsgidav.verbose"]
            Debug level [0-3].

    Log the HTTP request, then pass the request to the first middleware.

    Note: The OPTIONS method for the '*' path is handled directly.

"""
from wsgidav import __version__, compat, util
from wsgidav.dav_provider import DAVProvider
from wsgidav.default_conf import DEFAULT_CONFIG
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.http_authenticator import HTTPAuthenticator
from wsgidav.lock_manager import LockManager
from wsgidav.lock_storage import LockStorageDict
from wsgidav.middleware import BaseMiddleware
from wsgidav.prop_man.property_manager import PropertyManager
from wsgidav.util import (
    dynamic_import_class,
    dynamic_instantiate_middleware,
    safe_re_encode,
)

import copy
import inspect
import platform
import sys
import time


__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)


def _check_config(config):
    errors = []

    mandatory_fields = ("provider_mapping",)
    for field in mandatory_fields:
        if field not in config:
            errors.append("Missing required option '{}'.".format(field))

    deprecated_fields = {
        "dir_browser.app_class": "middleware_stack",
        "dir_browser.enable": "middleware_stack",
        "dir_browser.ms_sharepoint_plugin": "dir_browser.ms_sharepoint_support",
        "dir_browser.ms_sharepoint_url": "dir_browser.ms_sharepoint_support",
        "domaincontroller": "http_authenticator.domain_controller",
        "domain_controller": "http_authenticator.domain_controller",
        "acceptbasic": "http_authenticator.accept_basic",
        "acceptdigest": "http_authenticator.accept_digest",
        "defaultdigest": "http_authenticator.default_to_digest",
        "trusted_auth_header": "http_authenticator.trusted_auth_header",
        "propsmanager": "property_manager",
        "mutableLiveProps": "mutable_live_props",
        "locksmanager": "lock_manager",
        "catchall": "error_printer.catch_all",
    }
    for old, new in deprecated_fields.items():
        if "." in old:
            k, v = old.split(".", 1)
            d = config[k]
        else:
            d, v = config, old

        if d and v in d:
            errors.append("Deprecated option '{}': use '{}' instead.".format(old, new))

    if errors:
        raise ValueError("Invalid configuration:\n  - " + "\n  - ".join(errors))

    return True


# ========================================================================
# WsgiDAVApp
# ========================================================================
class WsgiDAVApp(object):
    def __init__(self, config):

        self.config = copy.deepcopy(DEFAULT_CONFIG)
        util.deep_update(self.config, config)
        # self.config.update(config)
        config = self.config

        # Evaluate configuration and set defaults
        _check_config(config)

        #        response_trailer = config.get("response_trailer", "")
        self.verbose = config.get("verbose", 3)

        lock_storage = config.get("lock_manager")
        if lock_storage is True:
            lock_storage = LockStorageDict()

        if not lock_storage:
            self.lock_manager = None
        else:
            self.lock_manager = LockManager(lock_storage)

        self.prop_manager = config.get("property_manager")
        if not self.prop_manager:
            # Normalize False, 0 to None
            self.prop_manager = None
        elif self.prop_manager is True:
            self.prop_manager = PropertyManager()

        self.mount_path = config.get("mount_path")
        auth_conf = config.get("http_authenticator", {})

        # Instantiate DAV resource provider objects for every share
        # provider_mapping may contain the args that are passed to a `FilesystemProvider`
        # instance:
        #     <mount_path>: <folder_path>
        # or
        #     <mount_path>: [folder_path, is_readonly]
        # or contain a complete new instance:
        #     <mount_path>: <DAVProvider Instance>

        provider_mapping = self.config["provider_mapping"]

        self.provider_map = {}
        self.sorted_share_list = None
        for share, provider in provider_mapping.items():
            self.add_provider(share, provider)

        # Figure out the domain controller, used by http_authenticator
        # dc = config.get("http_authenticator", {}).get("domain_controller")
        # if dc is True or not dc:
        #     # True or null:
        #     dc = SimpleDomainController

        # if compat.is_basestring(dc):
        #     # If a plain string is passed, try to import it as class
        #     dc = dynamic_import_class(dc)

        # if inspect.isclass(dc):
        #     # If a class is passed, instantiate that
        #     # assert issubclass(mw, BaseMiddleware)  # TODO: remove this assert with 3.0
        #     dc = dc(config)

        # domain_controller = dc
        # print(domain_controller)
        domain_controller = None

        # Define WSGI application stack
        middleware_stack = config.get("middleware_stack", [])
        mw_list = []

        # This is the 'outer' application, i.e. the WSGI application object that
        # is eventually called by the server.
        self.application = self

        # When building up the middleware stack, this app will be wrapped and replaced by the
        # next middleware in the list.
        # The `middleware_stack` is configured such that the first app in the list should be
        # called first. But since every app wraps its predecessor, we iterate in reverse
        # order:
        for mw in reversed(middleware_stack):
            # The middleware stack configuration may contain plain strings, dicts,
            # classes, or objects
            app = None
            if compat.is_basestring(mw):
                # If a plain string is passed, try to import it, assuming BaseMiddleware
                # signature
                app_class = dynamic_import_class(mw)
                app = app_class(self, self.application, config)
            elif type(mw) is dict:
                # If a dict with one entry is passed, use the key as module/class name
                # and the value as constructor arguments (positional or kwargs).
                assert len(mw) == 1
                name, args = list(mw.items())[0]
                expand = {"${application}": self.application}
                app = dynamic_instantiate_middleware(name, args, expand)
            elif inspect.isclass(mw):
                # If a class is passed, assume BaseMiddleware (or compatible)
                assert issubclass(
                    mw, BaseMiddleware
                )  # TODO: remove this assert with 3.0
                app = mw(self, self.application, config)
            else:
                # Otherwise assume an initialized middleware instance
                app = mw

            # FIXME: We should try to generalize this specific code:
            if isinstance(app, HTTPAuthenticator):
                domain_controller = app.get_domain_controller()
                # Check anonymous access
                for share, data in self.provider_map.items():
                    if app.allow_anonymous_access(share):
                        data["allow_anonymous"] = True

            # Add middleware to the stack
            if app:
                mw_list.append(app)
                self.application = app
            else:
                _logger.error("Could not add middleware {}.".format(mw))

        # Print info
        _logger.info(
            "WsgiDAV/{} Python/{} {}".format(
                __version__, util.PYTHON_VERSION, platform.platform(aliased=True)
            )
        )
        if self.verbose >= 4:
            _logger.info(
                "Default encoding: {!r} (file system: {!r})".format(
                    sys.getdefaultencoding(), sys.getfilesystemencoding()
                )
            )

        if self.verbose >= 3:
            _logger.info("Lock manager:      {}".format(self.lock_manager))
            _logger.info("Property manager:  {}".format(self.prop_manager))
            _logger.info("Domain controller: {}".format(domain_controller))

        if self.verbose >= 4:
            # We traversed the stack in reverse order. Now revert again, so
            # we see the order that was configured:
            _logger.info("Middleware stack:")
            for mw in reversed(mw_list):
                _logger.info("  - {}".format(mw))

        if self.verbose >= 3:
            _logger.info("Registered DAV providers by route:")
            for share in self.sorted_share_list:
                data = self.provider_map[share]
                hint = " (anonymous)" if data["allow_anonymous"] else ""
                _logger.info("  - '{}': {}{}".format(share, data["provider"], hint))

        if auth_conf.get("accept_basic") and not config.get("ssl_certificate"):
            _logger.warning(
                "Basic authentication is enabled: It is highly recommended to enable SSL."
            )

        for share, data in self.provider_map.items():
            if data["allow_anonymous"]:
                # TODO: we should only warn here, if --no-auth is not given
                _logger.warning("Share '{}' will allow anonymous access.".format(share))
        return

    def add_provider(self, share, provider, readonly=False):
        """Add a provider to the provider_map."""
        # Make sure share starts with, or is '/'
        share = "/" + share.strip("/")
        assert share not in self.provider_map
        # We allow a simple string as 'provider'. In this case we interpret
        # it as a file system root folder that is published.
        if compat.is_basestring(provider):
            provider = FilesystemProvider(provider, readonly)
        elif type(provider) in (list, tuple):
            provider = FilesystemProvider(provider[0], provider[1])

        if not isinstance(provider, DAVProvider):
            raise ValueError("Invalid provider {}".format(provider))

        provider.set_share_path(share)
        if self.mount_path:
            provider.set_mount_path(self.mount_path)

        # TODO: someday we may want to configure different lock/prop
        # managers per provider
        provider.set_lock_manager(self.lock_manager)
        provider.set_prop_manager(self.prop_manager)

        self.provider_map[share] = {"provider": provider, "allow_anonymous": False}

        # Store the list of share paths, ordered by length, so route lookups
        # will return the most specific match
        self.sorted_share_list = [s.lower() for s in self.provider_map.keys()]
        self.sorted_share_list = sorted(self.sorted_share_list, key=len, reverse=True)

        return provider

    def __call__(self, environ, start_response):

        # util.log("SCRIPT_NAME='{}', PATH_INFO='{}'".format(
        #    environ.get("SCRIPT_NAME"), environ.get("PATH_INFO")))

        path = environ["PATH_INFO"]

        # (#73) Failed on processing non-iso-8859-1 characters on Python 3
        #
        # Note: we encode using UTF-8 here (falling back to ISO-8859-1)!
        # This seems to be wrong, since per PEP 3333 PATH_INFO is always ISO-8859-1 encoded
        # (see https://www.python.org/dev/peps/pep-3333/#unicode-issues).
        # But also seems to resolve errors when accessing resources with Chinese characters, for
        # example.
        # This is done by default for Python 3, but can be turned off in settings.
        re_encode_path_info = self.config.get("re_encode_path_info")
        if re_encode_path_info is None:
            re_encode_path_info = compat.PY3
        if re_encode_path_info:
            path = environ["PATH_INFO"] = compat.wsgi_to_bytes(path).decode()

        # We optionally unquote PATH_INFO here, although this should already be
        # done by the server (#8).
        if self.config.get("unquote_path_info", False):
            path = compat.unquote(environ["PATH_INFO"])
        # GC issue 22: Pylons sends root as u'/'
        if not compat.is_native(path):
            _logger.warning("Got non-native PATH_INFO: {!r}".format(path))
            # path = path.encode("utf8")
            path = compat.to_native(path)

        # Always adding these values to environ:
        environ["wsgidav.config"] = self.config
        environ["wsgidav.provider"] = None
        environ["wsgidav.verbose"] = self.verbose

        # Find DAV provider that matches the share
        share = None
        lower_path = path.lower()
        for r in self.sorted_share_list:
            # @@: Case sensitivity should be an option of some sort here;
            # os.path.normpath might give the preferred case for a filename.
            if r == "/":
                share = r
                break
            elif lower_path == r or lower_path.startswith(r + "/"):
                share = r
                break

        # Note: we call the next app, even if provider is None, because OPTIONS
        #       must still be handled.
        #       All other requests will result in '404 Not Found'
        if share is not None:
            share_data = self.provider_map.get(share)
            environ["wsgidav.provider"] = share_data["provider"]
        # TODO: test with multi-level realms: 'aa/bb'
        # TODO: test security: url contains '..'

        # Transform SCRIPT_NAME and PATH_INFO
        # (Since path and share are unquoted, this also fixes quoted values.)
        if share == "/" or not share:
            environ["PATH_INFO"] = path
        else:
            environ["SCRIPT_NAME"] += share
            environ["PATH_INFO"] = path[len(share) :]

        # assert isinstance(path, str)
        assert compat.is_native(path)
        # See http://mail.python.org/pipermail/web-sig/2007-January/002475.html
        # for some clarification about SCRIPT_NAME/PATH_INFO format
        # SCRIPT_NAME starts with '/' or is empty
        assert environ["SCRIPT_NAME"] == "" or environ["SCRIPT_NAME"].startswith("/")
        # SCRIPT_NAME must not have a trailing '/'
        assert environ["SCRIPT_NAME"] in ("", "/") or not environ[
            "SCRIPT_NAME"
        ].endswith("/")
        # PATH_INFO starts with '/'
        assert environ["PATH_INFO"] == "" or environ["PATH_INFO"].startswith("/")

        start_time = time.time()

        def _start_response_wrapper(status, response_headers, exc_info=None):
            # Postprocess response headers
            headerDict = {}
            for header, value in response_headers:
                if header.lower() in headerDict:
                    _logger.error("Duplicate header in response: {}".format(header))
                headerDict[header.lower()] = value

            # Check if we should close the connection after this request.
            # http://www.w3.org/Protocols/rfc2616/rfc2616-sec4.html#sec4.4
            forceCloseConnection = False
            currentContentLength = headerDict.get("content-length")
            statusCode = int(status.split(" ", 1)[0])
            contentLengthRequired = (
                environ["REQUEST_METHOD"] != "HEAD"
                and statusCode >= 200
                and statusCode not in (204, 304)
            )
            #            _logger.info(environ["REQUEST_METHOD"], statusCode, contentLengthRequired)
            if contentLengthRequired and currentContentLength in (None, ""):
                # A typical case: a GET request on a virtual resource, for which
                # the provider doesn't know the length
                _logger.error(
                    "Missing required Content-Length header in {}-response: closing connection".format(
                        statusCode
                    )
                )
                forceCloseConnection = True
            elif not type(currentContentLength) is str:
                _logger.error(
                    "Invalid Content-Length header in response ({!r}): closing connection".format(
                        headerDict.get("content-length")
                    )
                )
                forceCloseConnection = True

            # HOTFIX for Vista and Windows 7 (GC issue 13, issue 23)
            # It seems that we must read *all* of the request body, otherwise
            # clients may miss the response.
            # For example Vista MiniRedir didn't understand a 401 response,
            # when trying an anonymous PUT of big files. As a consequence, it
            # doesn't retry with credentials and the file copy fails.
            # (XP is fine however).
            util.read_and_discard_input(environ)

            # Make sure the socket is not reused, unless we are 100% sure all
            # current input was consumed
            if util.get_content_length(environ) != 0 and not environ.get(
                "wsgidav.all_input_read"
            ):
                _logger.warning(
                    "Input stream not completely consumed: closing connection"
                )
                forceCloseConnection = True

            if forceCloseConnection and headerDict.get("connection") != "close":
                _logger.warning("Adding 'Connection: close' header")
                response_headers.append(("Connection", "close"))

            # Log request
            if self.verbose >= 3:
                userInfo = environ.get("http_authenticator.user_name")
                if not userInfo:
                    userInfo = "(anonymous)"
                extra = []
                if "HTTP_DESTINATION" in environ:
                    extra.append('dest="{}"'.format(environ.get("HTTP_DESTINATION")))
                if environ.get("CONTENT_LENGTH", "") != "":
                    extra.append("length={}".format(environ.get("CONTENT_LENGTH")))
                if "HTTP_DEPTH" in environ:
                    extra.append("depth={}".format(environ.get("HTTP_DEPTH")))
                if "HTTP_RANGE" in environ:
                    extra.append("range={}".format(environ.get("HTTP_RANGE")))
                if "HTTP_OVERWRITE" in environ:
                    extra.append("overwrite={}".format(environ.get("HTTP_OVERWRITE")))
                if self.verbose >= 3 and "HTTP_EXPECT" in environ:
                    extra.append('expect="{}"'.format(environ.get("HTTP_EXPECT")))
                if self.verbose >= 4 and "HTTP_CONNECTION" in environ:
                    extra.append(
                        'connection="{}"'.format(environ.get("HTTP_CONNECTION"))
                    )
                if self.verbose >= 4 and "HTTP_USER_AGENT" in environ:
                    extra.append('agent="{}"'.format(environ.get("HTTP_USER_AGENT")))
                if self.verbose >= 4 and "HTTP_TRANSFER_ENCODING" in environ:
                    extra.append(
                        "transfer-enc={}".format(environ.get("HTTP_TRANSFER_ENCODING"))
                    )
                if self.verbose >= 3:
                    extra.append("elap={:.3f}sec".format(time.time() - start_time))
                extra = ", ".join(extra)

                #               This is the CherryPy format:
                #                127.0.0.1 - - [08/Jul/2009:17:25:23] "GET /loginPrompt?redirect=/renderActionList%3Frelation%3Dpersonal%26key%3D%26filter%3DprivateSchedule&reason=0 HTTP/1.1" 200 1944 "http://127.0.0.1:8002/command?id=CMD_Schedule" "Mozilla/5.0 (Windows; U; Windows NT 6.0; de; rv:1.9.1) Gecko/20090624 Firefox/3.5"  # noqa
                _logger.info(
                    '{addr} - {user} - [{time}] "{method} {path}" {extra} -> {status}'.format(
                        addr=environ.get("REMOTE_ADDR", ""),
                        user=userInfo,
                        time=util.get_log_time(),
                        method=environ.get("REQUEST_METHOD"),
                        path=safe_re_encode(
                            environ.get("PATH_INFO", ""),
                            sys.stdout.encoding if sys.stdout.encoding else "utf-8",
                        ),
                        extra=extra,
                        status=status,
                        # response_headers.get(""), # response Content-Length
                        # referer
                    )
                )
            return start_response(status, response_headers, exc_info)

        # Call first middleware
        app_iter = self.application(environ, _start_response_wrapper)
        try:
            for v in app_iter:
                yield v
        finally:
            if hasattr(app_iter, "close"):
                app_iter.close()

        return
