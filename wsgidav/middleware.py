# -*- coding: utf-8 -*-
"""
Abstract base middleware class (optional use).
"""

__docformat__ = "reStructuredText"


class BaseMiddleware(object):
    """Abstract base middleware class (optional).

    Note: this is a convenience class, that *may* be used to implement WsgiDAV
    middlewares. However it is not a reqiuement: any object that implements
    the WSGI specification can be added to the stack.

    Derived classes in WsgiDAV include::

        wsgidav.dir_browser.WsgiDavDirBrowser
        wsgidav.debug_filter.WsgiDavDebugFilter
        wsgidav.error_printer.ErrorPrinter
        wsgidav.http_authenticator.HTTPAuthenticator
        wsgidav.request_resolver.RequestResolver
    """

    def __init__(self, wsgidav_app, next_app, config):
        self.wsgidav_app = wsgidav_app
        self.next_app = next_app
        self.config = config
        self.verbose = config.get("verbose", 3)

    def __call__(self, environ, start_response):
        raise NotImplementedError

    def __str__(self):
        return "{}.{}".format(self.__module__, self.__class__.__name__)

    def is_disabled(self):
        """Optionally return False to skip this module on startup."""
        return False
