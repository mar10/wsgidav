"""
Abstract base middleware class 

See `Developers info`_ for more information about the WsgiDAV architecture.

.. _`Developers info`: http://wsgidav.readthedocs.org/en/latest/develop.html  
"""
from __future__ import print_function

__docformat__ = "reStructuredText"


class BaseMiddleware(object):
    """Abstract base middleware class.

    Implementations in WsgiDAV include::
        
        wsgidav.dir_browser.WsgiDavDirBrowser
        wsgidav.error_printer.ErrorPrinter
        wsgidav.debug_filter.WsgiDavDebugFilter
        wsgidav.http_authenticator.HTTPAuthenticator
    """
    def __init__(self, application, config):
        pass

    def __call__(self, environ, start_response):
        pass

    @staticmethod
    def isSuitable(config):
        """
        Is this middleware class is suitable for current configuration?

        Checking when initialize WsgiDAVApp and NOT on each request
        """
        return True