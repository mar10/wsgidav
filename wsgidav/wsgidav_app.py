# -*- coding: iso-8859-1 -*-

"""
wsgidav_app
===========

:Author: Ho Chun Wei, fuzzybr80(at)gmail.com (author of original PyFileServer)
:Author: Martin Wendt, moogle(at)wwwendt.de 
:Copyright: Lesser GNU Public License, see LICENSE file attached with package


WSGI container, that handles the HTTP requests. This object is passed to the 
WSGI server and represents our WsgiDAV application to the outside. 

See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
"""
from fs_dav_provider import FilesystemProvider
from wsgidav.dir_browser import WsgiDavDirBrowser
from wsgidav.dav_provider import DAVProvider
import threading
import urllib
import util
import os
from error_printer import ErrorPrinter
from debug_filter import WsgiDavDebugFilter
from http_authenticator import HTTPAuthenticator
from request_resolver import RequestResolver
from domain_controller import WsgiDAVDomainController
from property_manager import PropertyManager
from lock_manager import LockManager

__docformat__ = "reStructuredText"


_defaultOpts = {}

def _checkConfig(config):
    mandatoryFields = ["provider_mapping",
                       ]
    for field in mandatoryFields:
        if not field in config:
            raise ValueError("Invalid configuration: missing required field '%s'" % field)


class WsgiDAVApp(object):

    def __init__(self, config):
        self.config = config

        # Evaluate configuration and set defaults
        _checkConfig(config)
        provider_mapping = self.config["provider_mapping"]
        response_trailer = config.get("response_trailer", "")
        self._verbose = config.get("verbose", 2)

        locksmanager = config.get("locksmanager") 
        if not locksmanager:
            locksfile = config.get("locksfile") or "wsgidav-locks.shelve"
            locksfile = os.path.abspath(locksfile)
            locksmanager = LockManager(locksfile)
            
        propsmanager = config.get("propsmanager")     
        if not propsmanager:
            propsfile = config.get("propsfile") or "wsgidav-props.shelve"
            propsfile = os.path.abspath(propsfile)
            propsmanager = PropertyManager(propsfile)     

        user_mapping = self.config.get("user_mapping", {})
        domaincontrollerobj = config.get("domaincontroller") or WsgiDAVDomainController(user_mapping)

        # authentication fields
        authacceptbasic = config.get("acceptbasic", False)
        authacceptdigest = config.get("acceptdigest", True)
        authdefaultdigest = config.get("defaultdigest", True)

        # Instantiate DAV resource provider objects for every share
        self.providerMap = {}
        for (share, provider) in provider_mapping.items():
            # Make sure share starts with, or is, '/' 
            share = "/" + share.strip("/")

            # We allow a simple string a 'provider'. In this case we interpret 
            # it as a file system root folder that is published. 
            if isinstance(provider, basestring):
                provider = FilesystemProvider(provider)

            assert isinstance(provider, DAVProvider)

            provider.setSharePath(share)
            # TODO: someday we may want to configure different lock/prop managers per provider
            provider.setLockManager(locksmanager)
            provider.setPropManager(propsmanager)
            
            self.providerMap[share] = provider
            

        if self._verbose >= 2:
            print "Registered DAV providers:"
            for k, v in self.providerMap.items():
                hint = ""
                if not user_mapping.get(share):
                    hint = "Anonymous!"
                print "  Share '%s': %s%s" % (k, v, hint)
        if self._verbose >= 1:
            for share in self.providerMap:
                if not user_mapping.get(share):
                    print "WARNING: share '%s' will allow anonymous access." % share

        # Define WSGI application stack
        application = RequestResolver()
        application = WsgiDavDirBrowser(application)
        application = HTTPAuthenticator(application, 
                                        domaincontrollerobj, 
                                        authacceptbasic, 
                                        authacceptdigest, 
                                        authdefaultdigest)      
        application = ErrorPrinter(application, 
                                   server_descriptor=response_trailer,
                                   catchall=False)

        application = WsgiDavDebugFilter(application)
        
        self._application = application


    def __call__(self, environ, start_response):

        print >> environ["wsgi.errors"], "%s SCRIPT_NAME:'%s', PATH_INFO:'%s', %s\n    %s" % (
                   environ.get("REQUEST_METHOD"),
                   environ.get("SCRIPT_NAME"),
                   environ.get("PATH_INFO"),
                   environ.get("REMOTE_USER"),
                   environ.get("HTTP_AUTHORIZATION"),
                   )
        # We unquote PATH_INFO here, although this should already be done by
        # the server.
        path = urllib.unquote(environ["PATH_INFO"])

        # Always adding these values to environ:
        environ["wsgidav.config"] = self.config
        environ["wsgidav.provider"] = None
        environ["wsgidav.verbose"] = self._verbose

        ## Find DAV provider that matches the share

        # sorting share list by reverse length
        shareList = self.providerMap.keys()
        shareList.sort(key=len, reverse=True)

        share = None 
        for r in shareList:
            # @@: Case sensitivity should be an option of some sort here; 
            #     os.path.normpath might give the preferred case for a filename.
            if r == "/":
                share = r
                break
            elif path.upper() == r.upper() or path.upper().startswith(r.upper()+"/"):
#                print path, ":->" , r
                share = r
                break
        
        provider = self.providerMap.get(share)
        
        # Note: we call the next app, even if provider is None, because OPTIONS 
        # must still be handled 
        environ["wsgidav.provider"] = provider

        # TODO: test with multi-level realms: 'aa/bb'
        # TODO: test security: url contains '..'
        # TODO: SCRIPT_NAME could already contain <approot>
        #       See @@
        
        # Transform SCRIPT_NAME and PATH_INFO
        # (Since path and share are unquoted, this also fixes quoted values.) 
        if share == "/" or not share:
            environ["SCRIPT_NAME"] = ""
            environ["PATH_INFO"] = path
        else:
            environ["SCRIPT_NAME"] = share
            environ["PATH_INFO"] = path[len(share):]

        # See http://mail.python.org/pipermail/web-sig/2007-January/002475.html
        # for some clarification about SCRIPT_NAME/PATH_INFO format
        # SCRIPT_NAME starts with '/' or is empty
        assert environ["SCRIPT_NAME"] == "" or environ["SCRIPT_NAME"].startswith("/")
        # SCRIPT_NAME must not have a trailing '/'
        assert environ["SCRIPT_NAME"] in ("", "/") or not environ["SCRIPT_NAME"].endswith("/")
        # PATH_INFO starts with '/'
        assert environ["PATH_INFO"] == "" or environ["PATH_INFO"].startswith("/")
   
        # Log HTTP request
        if self._verbose >= 1:
            threadInfo = ""
            userInfo = ""
            if self._verbose >= 2:
                threadInfo = "<%s>" % threading._get_ident() #.currentThread())
                if not environ.get("HTTP_AUTHORIZATION"):
                    userInfo = "(anonymous)"

            print >> environ["wsgi.errors"], "[", util.getRfc1123Time(),"] from ", environ.get("REMOTE_ADDR","unknown"), " ", threadInfo, environ.get("REQUEST_METHOD","unknown"), " ", environ.get("PATH_INFO","unknown"), " ", environ.get("HTTP_DESTINATION", ""), userInfo

        # Call next middleware
        for v in self._application(environ, start_response):
            util.debug("sc", "WsgiDAVApp: yield start")
            yield v
            util.debug("sc", "WsgiDAVApp: yield end")
        return
