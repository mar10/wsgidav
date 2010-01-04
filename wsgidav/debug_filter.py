# -*- coding: iso-8859-1 -*-

"""
debug_filter
============

:Author: Martin Wendt, moogle(at)wwwendt.de 
:Copyright: Licensed under the MIT license, see LICENSE file in this package.

WSGI middleware used for debugging (optional).

See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
"""
from wsgidav import util
import sys
import threading

__docformat__ = "reStructuredText"


#class StartResponseWrapper(object):
#    def __init__(self, environ):
#        self.environ = environ
#    def __call__(self, status, response_headers, exc_info=None):
        

class WsgiDavDebugFilter(object):

    def __init__(self, application):

        self._application = application
        self.out = sys.stderr
        self.passedLitmus = {}
        
        # These methods boost verbose=2 to verbose=3
        self._debugmethods = [
#                              "PROPPATCH",
##                              "PROPFIND",
##                              "GET",
#                              "HEAD",
#                              "DELETE",
#                              "PUT",
#                              "COPY",
#                              "MOVE",
#                              "LOCK",
#                              "UNLOCK",
                              ]

        # Litmus tests containing these string boost verbose=2 to verbose=3
        self._debuglitmus = [
#                             "lock_excl",
#                             "notowner_modify",
#                             "cond_put_corrupt_token",
#                             "copy_coll",
#                             "fail_cond_put_unlocked",
#                             "fail_complex_cond_put",
#                             "basic: 9",
#                             "basic: 14",
#                             "props: 16",
#                             "props: 18",
#                             "locks: 9",
#                             "locks: 12",
#                             "locks: 13",
#                             "locks: 14",
#                             "locks: 15",
#                             "locks: 16",
#                             "locks: 18",
#                             "locks: 27",
#                             "locks: 34",
#                             "locks: 36",
#                             "http: 2",
                            ]

        # Exit server, as soon as this litmus test has finished
        self._break_after_litmus = [
#                             "locks: 15",
                            ]



    def __call__(self, environ, start_response):
        """"""
        # TODO: pass srvcfg with constructor instead?
        srvcfg = environ["wsgidav.config"]
        verbose = srvcfg.get("verbose", 2)
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
            for litmusSubstring in self._debuglitmus:
                if litmusSubstring in litmusTag:
                    verbose = 3
                    debugBreak = True
                    dumpRequest = True
                    dumpResponse = True
                    break
            for litmusSubstring in self._break_after_litmus:
                if litmusSubstring in self.passedLitmus and litmusSubstring not in litmusTag:
                    print >> self.out, " *** break after litmus %s" % litmusTag
                    sys.exit(-1)
                if litmusSubstring in litmusTag:
                    self.passedLitmus[litmusSubstring] = True
                
        # Turn on max. debugging for selected request methods
        if verbose >= 2 and method in self._debugmethods:
            verbose = 3
            debugBreak = True
            dumpRequest = True
            dumpResponse = True

        # Set debug options to environment
        environ["wsgidav.verbose"] = verbose
        environ["wsgidav.debug_methods"] = self._debugmethods
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
