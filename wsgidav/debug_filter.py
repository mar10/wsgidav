# -*- coding: iso-8859-1 -*-

"""
debug_filter
============

:Author: Martin Wendt, moogle(at)wwwendt.de 
:Copyright: Lesser GNU Public License, see LICENSE file attached with package

WSGI middleware used for debugging (optional).

See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
"""
from wsgidav import util
import sys
import threading

__docformat__ = 'reStructuredText'


class WsgiDavDebugFilter(object):

    def __init__(self, application):

        self._application = application

        self.passedLitmus = {}
        
        self._dumpheaders = [
#                              "HTTP_IF",
#                              "HTTP_IF_MODIFIED_SINCE",
#                              "HTTP_IF_UNMODIFIED_SINCE",
#                              "HTTP_IF_MATCH",
#                              "HTTP_IF_NONE_MATCH",
#                              "HTTP_LOCK_TOKEN",
#                              "HTTP_DEPTH",
#                              "HTTP_DESTINATION",
#                              "HTTP_AUTHORIZATION",
                              ]

        self._debugmethods = [
#                              "PROPPATCH",
#                              "PROPFIND",
#                              "GET",
#                              "HEAD",
#                              "DELETE",
#                              "PUT",
#                              "COPY",
#                              "MOVE",
#                              "LOCK",
#                              "UNLOCK",
                              ]

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

        self._break_after_litmus = [
#                             "locks: 15",
                            ]



    def __call__(self, environ, start_response):
        """"""
        # TODO: pass srvcfg with constructor instead?
        srvcfg = environ['wsgidav.config']
        verbose = srvcfg.get('verbose', 2)
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
            print >> environ['wsgi.errors'], "----\nRunning litmus test '%s'..." % litmusTag
            for litmusSubstring in self._debuglitmus:
                if litmusSubstring in litmusTag:
                    verbose = 3
                    debugBreak = True
                    dumpRequest = True
                    dumpResponse = True
                    break
            for litmusSubstring in self._break_after_litmus:
                if litmusSubstring in self.passedLitmus and litmusSubstring not in litmusTag:
                    print >> environ['wsgi.errors'], " *** break after litmus %s" % litmusTag
                    sys.exit(-1)
                if litmusSubstring in litmusTag:
                    self.passedLitmus[litmusSubstring] = True
                
        # Turn on max. debugging for selected request methods
        if verbose >= 2 and environ["REQUEST_METHOD"] in self._debugmethods:
            verbose = 3
            debugBreak = True
            dumpRequest = True
            dumpResponse = True

        if dumpRequest:      
            print >> environ['wsgi.errors'], "<======== Request from <%s> %s" % (threading._get_ident(), threading.currentThread())
            for k, v in environ.items():
                if k == k.upper():
                    print >> environ['wsgi.errors'], "%20s: »%s«" % (k, v)
            print >> environ['wsgi.errors'], "\n"
        elif verbose >= 2:
            # Dump selected headers
            printedHeader = False
            for k, v in environ.items():
                if k in self._dumpheaders:
                    if not printedHeader:
                        printedHeader = True
                        print >> environ['wsgi.errors'], "<======== Request from <%s> %s" % (threading._get_ident(), threading.currentThread())
                    print >> environ['wsgi.errors'], "%20s: »%s«" % (k, v)

        # Set debug options to environment
        environ['wsgidav.verbose'] = verbose
        environ['wsgidav.debug_methods'] = self._debugmethods
        environ['wsgidav.debug_break'] = debugBreak

        # TODO: add timings and byte/request conters 
         
        # Call parent application and return it's response
        def start_response_wrapper(respcode, headers, exc_info=None):
            # TODO: not fully understood: 
#            assert exc_info is None   
            if exc_info is not None:
                util.log("DebugFilter got exception arg", exc_info)
#                raise exc_info
            if dumpResponse:
                print >> environ['wsgi.errors'], "=========> Response from <%s> %s" % (threading._get_ident(), threading.currentThread())

                print >> environ['wsgi.errors'], 'Response code:', respcode
                headersdict = dict(headers)
                for envitem in headersdict.keys():
                    print >> environ['wsgi.errors'], "\t", envitem, ":\t", repr(headersdict[envitem]) 
                print >> environ['wsgi.errors'], "\n"
            return start_response(respcode, headers, exc_info)

        for v in iter(self._application(environ, start_response_wrapper)):
            util.debug("sc", "debug_filter: yield response chunk (%s bytes)" % len(v))
            if dumpResponse and environ['REQUEST_METHOD'] != 'GET':
                print >> environ['wsgi.errors'], v
            yield v

        return 
