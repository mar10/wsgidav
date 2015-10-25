# (c) 2009-2015 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
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

See `Developers info`_ for more information about the WsgiDAV architecture.

.. _`Developers info`: http://wsgidav.readthedocs.org/en/latest/develop.html  
"""
from __future__ import print_function

import time
import sys
import threading
import urllib

from wsgidav import compat
from wsgidav.dav_provider import DAVProvider
from wsgidav.dir_browser import WsgiDavDirBrowser
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.lock_storage import LockStorageDict
from wsgidav.debug_filter import WsgiDavDebugFilter
from wsgidav.error_printer import ErrorPrinter
from wsgidav.http_authenticator import HTTPAuthenticator
from wsgidav.lock_manager import LockManager
from wsgidav.property_manager import PropertyManager
from wsgidav.request_resolver import RequestResolver
from wsgidav import util

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
                   "cherrypy-bundled",
                   "wsgidav",
                   ],

    "add_header_MS_Author_Via": True,
    "unquote_path_info": False, # See #8
#    "use_text_files": False,

    "propsmanager": None,  # True: use property_manager.PropertyManager                  
    "locksmanager": True,  # True: use lock_manager.LockManager    
    
    # HTTP Authentication Options
    "user_mapping": {},       # dictionary of dictionaries 
    "domaincontroller": None, # None: domain_controller.WsgiDAVDomainController(user_mapping)
    "acceptbasic": True,      # Allow basic authentication, True or False
    "acceptdigest": True,     # Allow digest authentication, True or False
    "defaultdigest": True,    # True (default digest) or False (default basic)

    # Error printer options
    "catchall": False,
    
    "enable_loggers": [
                      ],

    # Verbose Output
    "verbose": 1,        # 0 - no output (excepting application exceptions)         
                         # 1 - show single line request summaries (for HTTP logging)
                         # 2 - show additional events
                         # 3 - show full request/response header info (HTTP Logging)
                         #     request body and GET response bodies not shown
    
    "dir_browser": {
        "enable": True,               # Render HTML listing for GET requests on collections
        "response_trailer": "",       # Raw HTML code, appended as footer
        "davmount": False,            # Send <dm:mount> response if request URL contains '?davmount'
        "ms_mount": False,            # Add an 'open as webfolder' link (requires Windows)
        "ms_sharepoint_plugin": True, # Invoke MS Offce documents for editing using WebDAV
        "ms_sharepoint_urls": False,  # Prepend 'ms-word:ofe|u|' to URL for MS Offce documents
    },
    "middleware_stack": [
        WsgiDavDirBrowser,
        HTTPAuthenticator,
        ErrorPrinter,
        WsgiDavDebugFilter,
    ]
}



def _checkConfig(config):
    mandatoryFields = ["provider_mapping",
                       ]
    for field in mandatoryFields:
        if not field in config:
            raise ValueError("Invalid configuration: missing required field '%s'" % field)




#===============================================================================
# WsgiDAVApp
#===============================================================================
class WsgiDAVApp(object):

    def __init__(self, config):
        self.config = config

        util.initLogging(config["verbose"], config.get("enable_loggers", []))
        
        util.log("Default encoding: %s (file system: %s)" % (sys.getdefaultencoding(), sys.getfilesystemencoding()))
        
        # Evaluate configuration and set defaults
        _checkConfig(config)
        provider_mapping = self.config["provider_mapping"]
#        response_trailer = config.get("response_trailer", "")
        self._verbose = config.get("verbose", 2)

        lockStorage = config.get("locksmanager") 
        if lockStorage is True:
            lockStorage = LockStorageDict()
            
        if not lockStorage:
            locksManager = None
        else:
            locksManager = LockManager(lockStorage)

        propsManager = config.get("propsmanager")     
        if not propsManager:
            # Normalize False, 0 to None
            propsManager = None
        elif propsManager is True:
            propsManager = PropertyManager()     

        mount_path = config.get("mount_path")
         
        # Instantiate DAV resource provider objects for every share
        self.providerMap = {}
        for (share, provider) in provider_mapping.items():
            # Make sure share starts with, or is, '/' 
            share = "/" + share.strip("/")

            # We allow a simple string as 'provider'. In this case we interpret 
            # it as a file system root folder that is published. 
            if compat.is_basestring(provider):
                provider = FilesystemProvider(provider)

            assert isinstance(provider, DAVProvider)

            provider.setSharePath(share)
            if mount_path:
                provider.setMountPath(mount_path)
            
            # TODO: someday we may want to configure different lock/prop managers per provider
            provider.setLockManager(locksManager)
            provider.setPropManager(propsManager)
            
            self.providerMap[share] = {"provider": provider, "allow_anonymous": False}
            

        
        # Define WSGI application stack
        application = RequestResolver()
        
        domain_controller = None
        dir_browser = config.get("dir_browser", {})
        middleware_stack = config.get("middleware_stack", [])

        # Replace WsgiDavDirBrowser to custom class for backward compatibility only
        # In normal way you should insert it into middleware_stack
        if dir_browser.get("enable", True) and "app_class" in dir_browser.keys():
            config["middleware_stack"] = [m if m != WsgiDavDirBrowser else dir_browser['app_class'] for m in middleware_stack]

        for mw in middleware_stack:
            if mw.isSuitable(config):
                if self._verbose >= 2:
                    print("Middleware %s is suitable" % mw)
                application = mw(application, config)
                
                if issubclass(mw, HTTPAuthenticator):
                    domain_controller = application.getDomainController()
                    # check anonymous access
                    for share, data in self.providerMap.items():
                        if application.allowAnonymousAccess(share):
                            data['allow_anonymous'] = True
            else:
                if self._verbose >= 2:
                    print("Middleware %s is not suitable" % mw)
                    
        # Print info
        if self._verbose >= 2:
            print("Using lock manager: %r" % locksManager)
            print("Using property manager: %r" % propsManager)
            print("Using domain controller: %s" % domain_controller)
            print("Registered DAV providers:")
            for share, data in self.providerMap.items():
                hint = " (anonymous)" if data['allow_anonymous'] else ""
                print("  Share '%s': %s%s" % (share, provider, hint))
        if self._verbose >= 1:
            for share, data in self.providerMap.items():
                if data['allow_anonymous']:
                    # TODO: we should only warn here, if --no-auth is not given
                    print("WARNING: share '%s' will allow anonymous access." % share)

        self._application = application


    def __call__(self, environ, start_response):

#        util.log("SCRIPT_NAME='%s', PATH_INFO='%s'" % (environ.get("SCRIPT_NAME"), environ.get("PATH_INFO")))
        
        # We optionall unquote PATH_INFO here, although this should already be 
        # done by the server (#8).
        path = environ["PATH_INFO"]
        if self.config.get("unquote_path_info", False):
            path = compat.unquote(environ["PATH_INFO"])
        # GC issue 22: Pylons sends root as u'/' 
        # if isinstance(path, unicode):
        if not compat.is_native(path):
            util.log("Got non-native PATH_INFO: %r" % path)
            # path = path.encode("utf8")
            path = compat.to_native(path)

        # Always adding these values to environ:
        environ["wsgidav.config"] = self.config
        environ["wsgidav.provider"] = None
        environ["wsgidav.verbose"] = self._verbose

        ## Find DAV provider that matches the share

        # sorting share list by reverse length
#        shareList = self.providerMap.keys()
#        shareList.sort(key=len, reverse=True)
        shareList = sorted(self.providerMap.keys(), key=len, reverse=True)

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
        
        share_data = self.providerMap.get(share)
        
        # Note: we call the next app, even if provider is None, because OPTIONS 
        #       must still be handled.
        #       All other requests will result in '404 Not Found'  
        environ["wsgidav.provider"] = share_data['provider']
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

        # assert isinstance(path, str)
        assert compat.is_native(path)
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
            # Postprocess response headers
            headerDict = {}
            for header, value in response_headers:
                if header.lower() in headerDict:
                    util.warn("Duplicate header in response: %s" % header)
                headerDict[header.lower()] = value

            # Check if we should close the connection after this request. 
            # http://www.w3.org/Protocols/rfc2616/rfc2616-sec4.html#sec4.4
            forceCloseConnection = False
            currentContentLength = headerDict.get("content-length") 
            statusCode = int(status.split(" ", 1)[0]) 
            contentLengthRequired = (environ["REQUEST_METHOD"] != "HEAD" 
                                     and statusCode >= 200
                                     and not statusCode in (204, 304))  
#            print(environ["REQUEST_METHOD"], statusCode, contentLengthRequired)
            if contentLengthRequired and currentContentLength in (None, ""):
                # A typical case: a GET request on a virtual resource, for which  
                # the provider doesn't know the length 
                util.warn("Missing required Content-Length header in %s-response: closing connection" % statusCode)
                forceCloseConnection = True
            elif not type(currentContentLength) is str:
                util.warn("Invalid Content-Length header in response (%r): closing connection" % headerDict.get("content-length"))
                forceCloseConnection = True
            
            # HOTFIX for Vista and Windows 7 (GC issue 13, issue 23)
            # It seems that we must read *all* of the request body, otherwise
            # clients may miss the response.
            # For example Vista MiniRedir didn't understand a 401 response, 
            # when trying an anonymous PUT of big files. As a consequence, it
            # doesn't retry with credentials and the file copy fails. 
            # (XP is fine however).
            util.readAndDiscardInput(environ)

            # Make sure the socket is not reused, unless we are 100% sure all 
            # current input was consumed
            if(util.getContentLength(environ) != 0 
               and not environ.get("wsgidav.all_input_read")):
                util.warn("Input stream not completely consumed: closing connection")
                forceCloseConnection = True
                
            if forceCloseConnection and headerDict.get("connection") != "close":    
                util.warn("Adding 'Connection: close' header")
                response_headers.append(("Connection", "close"))
            
            # Log request
            if self._verbose >= 1:
                userInfo = environ.get("http_authenticator.username")
                if not userInfo:
                    userInfo = "(anonymous)"
                threadInfo = ""
                if self._verbose >= 1:
                    threadInfo = "<%s> " % threading.currentThread().ident
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
                if self._verbose >= 1 and "HTTP_EXPECT" in environ:
                    extra.append('expect="%s"' % environ.get("HTTP_EXPECT"))
                if self._verbose >= 2 and "HTTP_CONNECTION" in environ:
                    extra.append('connection="%s"' % environ.get("HTTP_CONNECTION"))
                if self._verbose >= 2 and "HTTP_USER_AGENT" in environ:
                    extra.append('agent="%s"' % environ.get("HTTP_USER_AGENT"))
                if self._verbose >= 2 and "HTTP_TRANSFER_ENCODING" in environ:
                    extra.append('transfer-enc=%s' % environ.get("HTTP_TRANSFER_ENCODING"))
                if self._verbose >= 1:
                    extra.append('elap=%.3fsec' % (time.time() - start_time))
                extra = ", ".join(extra)
                        
#               This is the CherryPy format:     
#                127.0.0.1 - - [08/Jul/2009:17:25:23] "GET /loginPrompt?redirect=/renderActionList%3Frelation%3Dpersonal%26key%3D%26filter%3DprivateSchedule&reason=0 HTTP/1.1" 200 1944 "http://127.0.0.1:8002/command?id=CMD_Schedule" "Mozilla/5.0 (Windows; U; Windows NT 6.0; de; rv:1.9.1) Gecko/20090624 Firefox/3.5"
#                print >>sys.stderr, '%s - %s - [%s] "%s" %s -> %s' % (
                print('%s - %s - [%s] "%s" %s -> %s' % (
                        threadInfo + environ.get("REMOTE_ADDR",""),                                                         
                        userInfo,
                        util.getLogTime(), 
                        environ.get("REQUEST_METHOD") + " " + environ.get("PATH_INFO", ""),
                        extra, 
                        status,
#                                        response_headers.get(""), # response Content-Length
                        # referer
                     ), file=sys.stdout)
 
            return start_response(status, response_headers, exc_info)
            
        # Call next middleware
        app_iter = self._application(environ, _start_response_wrapper)
        for v in app_iter:
            yield v
        if hasattr(app_iter, "close"):
            app_iter.close()
        
        return
