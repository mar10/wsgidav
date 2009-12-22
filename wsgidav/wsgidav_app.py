# -*- coding: iso-8859-1 -*-

"""
wsgidav_app
===========

:Author: Martin Wendt, moogle(at)wwwendt.de 
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com (author of original PyFileServer)
:Copyright: Lesser GNU Public License, see LICENSE file attached with package


WSGI container, that handles the HTTP requests. This object is passed to the 
WSGI server and represents our WsgiDAV application to the outside. 


Configuration
-------------

provider_mapping
    Type: dictionary, default: {}
    {shareName: DAVProvider,
    }
user_mapping
    Type: dictionary, default: {}
host
    Type: str, default: 'localhost'
port
    Type: int, default: 8080 
ext_servers
    Type: string list
enable_loggers
    List
propsmanager
    Default: None (use property_manager.PropertyManager)                    
locksmanager
    Default: None (use lock_manager.LockManager)                   
domaincontroller
    Default: None (use domain_controller.WsgiDAVDomainController(user_mapping))
verbose
    Type: int, default: 2
    0 no output (excepting application exceptions)         
    1 - show single line request summaries (for HTTP logging)
    2 - show additional events
    3 - show full request/response header info (HTTP Logging) request body and GET response bodies not shown

# HTTP Authentication Options
"acceptbasic": True,    # Allow basic authentication, True or False
"acceptdigest": True,   # Allow digest authentication, True or False
"defaultdigest": True,  # True (default digest) or False (default basic)

# Organizational Information - printed as a footer on html output
"response_trailer": None,


See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
"""
from fs_dav_provider import FilesystemProvider
from wsgidav.dir_browser import WsgiDavDirBrowser
from wsgidav.dav_provider import DAVProvider
import time
import sys
import threading
import urllib
import util
from error_printer import ErrorPrinter
from debug_filter import WsgiDavDebugFilter
from http_authenticator import HTTPAuthenticator
from request_resolver import RequestResolver
from domain_controller import WsgiDAVDomainController
from property_manager import PropertyManager
from lock_manager import LockManager

__docformat__ = "reStructuredText"


# Use these settings, if config file does not define them (or is totally missing)
DEFAULT_CONFIG = {
    "mount_path": None,  # Application root, e.g. <mount_path>/<share_name>/<res_path>               
    "provider_mapping": {},
    "host": "localhost",
    "port": 8080, 
    "ext_servers": [
#                   "paste", 
#                   "cherrypy",
#                   "wsgiref",
                   "wsgidav",
                   ],

    "enable_loggers": [
                      ],

    "propsmanager": None,  # None: use property_manager.PropertyManager                    
    "locksmanager": None,  # None: use lock_manager.LockManager    
    
    # HTTP Authentication Options
    "user_mapping": {},       # dictionary of dictionaries 
    "domaincontroller": None, # None: domain_controller.WsgiDAVDomainController(user_mapping)
    "acceptbasic": True,      # Allow basic authentication, True or False
    "acceptdigest": True,     # Allow digest authentication, True or False
    "defaultdigest": True,    # True (default digest) or False (default basic)
    
    # Verbose Output
    "verbose": 2,        # 0 - no output (excepting application exceptions)         
                         # 1 - show single line request summaries (for HTTP logging)
                         # 2 - show additional events
                         # 3 - show full request/response header info (HTTP Logging)
                         #     request body and GET response bodies not shown
    
    
    # Organizational Information - printed as a footer on html output
    "response_trailer": None,
}




def _checkConfig(config):
    mandatoryFields = ["provider_mapping",
                       ]
    for field in mandatoryFields:
        if not field in config:
            raise ValueError("Invalid configuration: missing required field '%s'" % field)




class WsgiDAVApp(object):

    def __init__(self, config):
        self.config = config

        util.initLogging(config["verbose"], config.get("enable_loggers", []))
        
        util.log("Default encoding: %s (file system: %s)" % (sys.getdefaultencoding(), sys.getfilesystemencoding()))
        
        # Evaluate configuration and set defaults
        _checkConfig(config)
        provider_mapping = self.config["provider_mapping"]
        response_trailer = config.get("response_trailer", "")
        self._verbose = config.get("verbose", 2)

        locksManager = config.get("locksmanager") 
        if not locksManager:
            locksManager = LockManager()
            
        propsManager = config.get("propsmanager")     
        if not propsManager:
            propsManager = PropertyManager()     

        mount_path = config.get("mount_path")
         
        user_mapping = self.config.get("user_mapping", {})
        domainController = config.get("domaincontroller") or WsgiDAVDomainController(user_mapping)
        isDefaultDC = isinstance(domainController, WsgiDAVDomainController)

        # authentication fields
        authacceptbasic = config.get("acceptbasic", True)
        authacceptdigest = config.get("acceptdigest", True)
        authdefaultdigest = config.get("defaultdigest", True)
        
        # Check configuration for NTDomainController
        # We don't use 'isinstance', because include would fail on non-windows boxes.
        wdcName = "NTDomainController"
        if domainController.__class__.__name__ == wdcName:
            if authacceptdigest or authdefaultdigest or not authacceptbasic:
                print >>sys.stderr, "WARNING: %s requires basic authentication.\n\tSet acceptbasic=True, acceptdigest=False, defaultdigest=False" % wdcName
                
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
            if mount_path:
                provider.setMountPath(mount_path)
            
            # TODO: someday we may want to configure different lock/prop managers per provider
            provider.setLockManager(locksManager)
            provider.setPropManager(propsManager)
            
            self.providerMap[share] = provider
            

        if self._verbose >= 2:
            print "Using lock manager: %s" % locksManager
            print "Using property manager: %s" % propsManager
            print "Using domain controller: %s" % domainController
            print "Registered DAV providers:"
            for share, provider in self.providerMap.items():
                hint = ""
                if isDefaultDC and not user_mapping.get(share):
                    hint = " (anonymous)"
                print "  Share '%s': %s%s" % (share, provider, hint)

        # If the default DC is used, emit a warning for anonymous realms
        if isDefaultDC and self._verbose >= 1:
            for share in self.providerMap:
                if not user_mapping.get(share):
                    # TODO: we should only warn here, if --no-auth is not given
                    print "WARNING: share '%s' will allow anonymous access." % share

        # Define WSGI application stack
        application = RequestResolver()
        application = WsgiDavDirBrowser(application)
        application = HTTPAuthenticator(application, 
                                        domainController, 
                                        authacceptbasic, 
                                        authacceptdigest, 
                                        authdefaultdigest)      
        application = ErrorPrinter(application, 
                                   server_descriptor=response_trailer,
                                   catchall=False)

        application = WsgiDavDebugFilter(application)
        
        self._application = application


    def __call__(self, environ, start_response):

        util.log("SCRIPT_NAME='%s', PATH_INFO='%s'" % (environ.get("SCRIPT_NAME"), environ.get("PATH_INFO")))
        
        # We unquote PATH_INFO here, although this should already be done by
        # the server.
        path = urllib.unquote(environ["PATH_INFO"])
        # issue 22: Pylons sends root as u'/' 
        if isinstance(path, unicode):
            util.log("Got unicode PATH_INFO: %r" % path)
            path = path.encode("utf8")

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
                share = r
                break
        
        provider = self.providerMap.get(share)
        
        # Note: we call the next app, even if provider is None, because OPTIONS 
        #       must still be handled.
        #       All other requests will result in '404 Not Found'  
        environ["wsgidav.provider"] = provider

        # TODO: test with multi-level realms: 'aa/bb'
        # TODO: test security: url contains '..'
        
        # Transform SCRIPT_NAME and PATH_INFO
        # (Since path and share are unquoted, this also fixes quoted values.)
        if share == "/" or not share:
            environ["PATH_INFO"] = path
        else:
            environ["SCRIPT_NAME"] += share
            environ["PATH_INFO"] = path[len(share):]
#        util.log("--> SCRIPT_NAME='%s', PATH_INFO='%s'" % (environ.get("SCRIPT_NAME"), environ.get("PATH_INFO")))

        # See http://mail.python.org/pipermail/web-sig/2007-January/002475.html
        # for some clarification about SCRIPT_NAME/PATH_INFO format
        # SCRIPT_NAME starts with '/' or is empty
        assert environ["SCRIPT_NAME"] == "" or environ["SCRIPT_NAME"].startswith("/")
        # SCRIPT_NAME must not have a trailing '/'
        assert environ["SCRIPT_NAME"] in ("", "/") or not environ["SCRIPT_NAME"].endswith("/")
        # PATH_INFO starts with '/'
        assert environ["PATH_INFO"] == "" or environ["PATH_INFO"].startswith("/")

        start_time = time.time()
        def _start_response_wrapper(status, response_headers, exc_info=None):
            # Log request
            if self._verbose >= 1:
                threadInfo = ""
                userInfo = environ.get("http_authenticator.username")
                if not userInfo:
                    userInfo = "(anonymous)"
                if self._verbose >= 1:
                    threadInfo = "<%s> " % threading._get_ident()
                extra = []
                if "HTTP_DESTINATION" in environ:
                    extra.append('dest="%s"' % environ.get("HTTP_DESTINATION"))
                if environ.get("CONTENT_LENGTH", "") != "":
                    extra.append("length=%s" % environ.get("CONTENT_LENGTH"))
                if "HTTP_DEPTH" in environ:
                    extra.append("depth=%s" % environ.get("HTTP_DEPTH"))
                if "HTTP_RANGE" in environ:
                    extra.append("range=%s" % environ.get("HTTP_RANGE"))
                if "HTTP_OVERWRITE" in environ:
                    extra.append("overwrite=%s" % environ.get("HTTP_OVERWRITE"))
#                if "HTTP_EXPECT" in environ:
#                    extra.append('expect="%s"' % environ.get("HTTP_EXPECT"))
                if self._verbose >= 2 and "HTTP_USER_AGENT" in environ:
                    extra.append('agent="%s"' % environ.get("HTTP_USER_AGENT"))
                if self._verbose >= 1:
                    extra.append('elap=%.3fsec' % (time.time() - start_time))
                extra = ", ".join(extra)

#               This is the CherryPy format:     
#                127.0.0.1 - - [08/Jul/2009:17:25:23] "GET /loginPrompt?redirect=/renderActionList%3Frelation%3Dpersonal%26key%3D%26filter%3DprivateSchedule&reason=0 HTTP/1.1" 200 1944 "http://127.0.0.1:8002/command?id=CMD_Schedule" "Mozilla/5.0 (Windows; U; Windows NT 6.0; de; rv:1.9.1) Gecko/20090624 Firefox/3.5"
                print >>sys.stderr, '%s - %s - [%s] "%s" %s -> %s' % (
                                        threadInfo + environ.get("REMOTE_ADDR",""),                                                         
                                        userInfo,
                                        util.getLogTime(), 
                                        environ.get("REQUEST_METHOD") + " " + environ.get("PATH_INFO", ""),
                                        extra, 
                                        status,
                                        # response Content-Length
                                        # referer
                                     )
            return start_response(status, response_headers, exc_info)
            
        # Call next middleware
        for v in self._application(environ, _start_response_wrapper):
            yield v
        return
