# (c) 2009-2011 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
WSGI middleware used for debugging (optional).

This module dumps request and response information to the console, depending
on current debug configuration.

On init:
    Define HTTP methods and litmus tests, that should turn on the verbose mode
    (currently hard coded).              
For every request:
    Increase value of ``environ['verbose']``, if the request should be debugged.
    Also dump request and response headers and body.
    
    Then pass the request to the next middleware.  

These configuration settings are evaluated:

*verbose*
    This is also used by other modules. This filter adds additional information
    depending on the value.

    =======  ===================================================================
    verbose  Effect  
    =======  ===================================================================
     0        No additional output.
     1        No additional output (only standard request logging).
     2        Dump headers of all requests and responses.
     3        Dump headers and bodies of all requests and responses. 
    =======  ===================================================================

*debug_methods*
    Boost verbosity to 3 while processing certain request methods. This option 
    is ignored, when ``verbose < 2``.

    Configured like::

        debug_methods = ["PROPPATCH", "PROPFIND", "GET", "HEAD","DELETE",
                         "PUT", "COPY", "MOVE", "LOCK", "UNLOCK",
                         ]
 
*debug_litmus*
    Boost verbosity to 3 while processing litmus tests that contain certain 
    substrings. This option is ignored, when ``verbose < 2``.

    Configured like::
    
        debug_litmus = ["notowner_modify", "props: 16", ]

 
See `Developers info`_ for more information about the WsgiDAV architecture.

.. _`Developers info`: http://docs.wsgidav.googlecode.com/hg/html/develop.html  
"""
from wsgidav import util
import sys
import threading

__docformat__ = "reStructuredText"



class WsgiDavDebugFilter(object):

    def __init__(self, application, config):
        self._application = application
        self._config = config
#        self.out = sys.stderr
        self.out = sys.stdout
        self.passedLitmus = {}
        # These methods boost verbose=2 to verbose=3
        self.debug_methods = config.get("debug_methods", [])
        # Litmus tests containing these string boost verbose=2 to verbose=3
        self.debug_litmus = config.get("debug_litmus", [])
        # Exit server, as soon as this litmus test has finished
        self.break_after_litmus = [
#                                   "locks: 15",
                                   ]


    def __call__(self, environ, start_response):
        """"""
#        srvcfg = environ["wsgidav.config"]
        verbose = self._config.get("verbose", 2)

        method = environ["REQUEST_METHOD"]

        debugBreak = False
        dumpRequest = False
        dumpResponse = False
        
        if verbose >= 3:
            dumpRequest = dumpResponse = True

        # Process URL commands
        if "dump_storage" in environ.get("QUERY_STRING"):
            dav = environ.get("wsgidav.provider")
            if dav.lockManager:
                dav.lockManager._dump()
            if dav.propManager:
                dav.propManager._dump()

        # Turn on max. debugging for selected litmus tests
        litmusTag = environ.get("HTTP_X_LITMUS", environ.get("HTTP_X_LITMUS_SECOND"))
        if litmusTag and verbose >= 2:
            print >> self.out, "----\nRunning litmus test '%s'..." % litmusTag
            for litmusSubstring in self.debug_litmus: 
                if litmusSubstring in litmusTag:
                    verbose = 3
                    debugBreak = True
                    dumpRequest = True
                    dumpResponse = True
                    break
            for litmusSubstring in self.break_after_litmus:
                if litmusSubstring in self.passedLitmus and litmusSubstring not in litmusTag:
                    print >> self.out, " *** break after litmus %s" % litmusTag
                    sys.exit(-1)
                if litmusSubstring in litmusTag:
                    self.passedLitmus[litmusSubstring] = True
                
        # Turn on max. debugging for selected request methods
        if verbose >= 2 and method in self.debug_methods:
            verbose = 3
            debugBreak = True
            dumpRequest = True
            dumpResponse = True

        # Set debug options to environment
        environ["wsgidav.verbose"] = verbose
#        environ["wsgidav.debug_methods"] = self.debug_methods
        environ["wsgidav.debug_break"] = debugBreak
        environ["wsgidav.dump_request_body"] = dumpRequest
        environ["wsgidav.dump_response_body"] = dumpResponse

        # Dump request headers
        if dumpRequest:      
            print >> self.out, "<%s> --- %s Request ---" % (threading._get_ident(), method)
            for k, v in environ.items():
                if k == k.upper():
                    print >> self.out, "%20s: '%s'" % (k, v)
            print >> self.out, "\n"

        # Call parent application and return it's response
        def start_response_wrapper(status, response_headers, exc_info=None):
            # TODO: not fully understood: 
            if exc_info is not None:
                util.log("DebugFilter got exc_info", exc_info)

#            # Dump response headers
#            if dumpResponse:
#                print >> self.out, "<%s> --- %s Response(%s): ---" % (threading._get_ident(), method, status)
#                headersdict = dict(response_headers)
#                for envitem in headersdict.keys():
#                    print >> self.out, "\t%s:\t'%s'" % (envitem, repr(headersdict[envitem])) 
#                print >> self.out, "\n"
            # Store response headers
            environ["wsgidav.response_status"] = status
            environ["wsgidav.response_headers"] = response_headers
            return start_response(status, response_headers, exc_info)

        nbytes = 0
        firstyield = True
        for v in iter(self._application(environ, start_response_wrapper)):
            # Dump response headers
            if firstyield and dumpResponse:
                print >> self.out, "<%s> --- %s Response(%s): ---" % (threading._get_ident(), 
                                                                      method, 
                                                                      environ.get("wsgidav.response_status"))
                headersdict = dict(environ.get("wsgidav.response_headers"))
                for envitem in headersdict.keys():
                    print >> self.out, "%s: %s" % (envitem, repr(headersdict[envitem])) 
                print >> self.out, ""

            # Check, if response is a binary string, otherwise we probably have 
            # calculated a wrong content-length
            assert type(v) is str
            
            # Dump response body
            drb = environ.get("wsgidav.dump_response_body")
            if type(drb) is str:
                # Middleware provided a formatted body representation 
                print >> self.out, drb
                drb = environ["wsgidav.dump_response_body"] = None
            elif drb is True:
                # Else dump what we get, (except for long GET responses) 
                if method == "GET":
                    if firstyield:
                        print >> self.out, v[:50], "..."
                elif len(v) > 0:
                    print >> self.out, v

            nbytes += len(v) 
            firstyield = False
            yield v

        if dumpResponse:
            print >> self.out, "\n<%s> --- End of %s Response (%i bytes) ---" % (threading._get_ident(), method, nbytes)
        return 
