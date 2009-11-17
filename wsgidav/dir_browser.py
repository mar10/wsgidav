# -*- coding: iso-8859-1 -*-
"""
request_server
==============

:Author: Martin Wendt, moogle(at)wwwendt.de 
:Author: Ho Chun Wei, fuzzybr80(at)gmail.com (author of original PyFileServer)
:Copyright: Lesser GNU Public License, see LICENSE file attached with package


WSGI middleware that handles GET requests on collections to display directories.

See DEVELOPERS.txt_ for more information about the WsgiDAV architecture.

.. _DEVELOPERS.txt: http://wiki.wsgidav-dev.googlecode.com/hg/DEVELOPERS.html  
"""
from wsgidav.dav_error import DAVError, HTTP_OK, HTTP_MEDIATYPE_NOT_SUPPORTED
#from wsgidav.dav_provider import DAVResource
import sys
import urllib
import util

__docformat__ = "reStructuredText"


class WsgiDavDirBrowser(object):
    """WSGI middleware that handles GET requests on collections to display directories."""

    def __init__(self, application):
        self._application = application
        self._verbose = 2


    def __call__(self, environ, start_response):
        path = environ["PATH_INFO"]
        dav = environ["wsgidav.provider"]
        
        if environ["REQUEST_METHOD"] in ("GET", "HEAD" ) and dav and dav.isCollection(path):
            # TODO: do we need to handle IF headers?
#            self._evaluateIfHeaders(path, environ)
            if environ["REQUEST_METHOD"] =="HEAD":
                return util.sendSimpleResponse(environ, start_response, HTTP_OK)
            
#            if True:
#                from cProfile import Profile
#                profile = Profile()
#                profile.runcall(self._listDirectory, environ, start_response)
#                # sort: 0:"calls",1:"time", 2: "cumulative"
#                profile.print_stats(sort=2)
            return self._listDirectory(environ, start_response)
        
        return self._application(environ, start_response)


    def _fail(self, value, contextinfo=None, srcexception=None, preconditionCode=None):
        """Wrapper to raise (and log) DAVError."""
        e = DAVError(value, contextinfo, srcexception, preconditionCode)
        if self._verbose >= 2:
            print >>sys.stderr, "Raising DAVError %s" % e.getUserInfo()
        raise e

    
    def _listDirectory(self, environ, start_response):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#rfc.section.9.4
        """
        path = environ["PATH_INFO"]
        dav = environ["wsgidav.provider"]

        if util.getContentLength(environ) != 0:
            self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
                       "The server does not handle any body content.")
        
        # (Dispatcher already made sure, that path is an existing collection)
        displaypath = urllib.unquote(dav.getHref(path))
        trailer = environ.get("wsgidav.config", {}).get("response_trailer")
        
        o_list = []
        o_list.append("<html><head>")
        o_list.append("<meta http-equiv='Content-Type' content='text/html; charset=UTF-8' />")
        o_list.append("<title>WsgiDAV - Index of %s </title>" % displaypath)
        o_list.append("""\
<style type="text/css">
    img { border: 0; padding: 0 2px; vertical-align: text-bottom; }
    td  { font-family: monospace; padding: 2px 3px; text-align: right; vertical-align: bottom; white-space: pre; }
    td:first-child { text-align: left; padding: 2px 10px 2px 3px; }
    table { border: 0; }
    a.symlink { font-style: italic; }
</style>        
</head>        
<body>
""")
        o_list.append("<H1>%s</H1>" % displaypath)
        o_list.append("<hr/><table>")

        if path in ("", "/"):
            o_list.append("<tr><td colspan='4'>Top level share</td></tr>")
        else:
            o_list.append("<tr><td colspan='4'><a href='" + dav.getHref(dav.getParent(path)) + "'>Up to higher level</a></td></tr>")

        for name in dav.getMemberNames(path):
            childPath = path.rstrip("/") + "/" + name
            res = dav.getResourceInst(childPath)

            if not res.exists():
                print >>sys.stderr, "WARNING: WsgiDavDirBrowser could not get resource instance for '%s'" % childPath
                continue

            infoDict = {"url": dav.getHref(path).rstrip("/") + "/" + urllib.quote(name),
                        "displayName": res.displayName(),
                        "displayType": res.displayType(),
                        "strModified": "",
                        "strSize": "",
                        }
            if res.isCollection():
                infoDict["url"] = infoDict["url"] + "/"
            if res.modified() is not None:
                infoDict["strModified"] = util.getRfc1123Time(res.modified())
            if res.contentLength() is not None and not res.isCollection():
                infoDict["strSize"] = util.byteNumberString(res.contentLength())
                
 
            o_list.append("""\
            <tr><td><a href="%(url)s">%(displayName)s</a></td>
            <td>%(displayType)s</td>
            <td>%(strSize)s</td>
            <td>%(strModified)s</td></tr>\n""" % infoDict)
            
        o_list.append("</table>\n")

        if "http_authenticator.username" in environ:
            o_list.append("<p>Authenticated user: '%s', realm: '%s'.</p>" % (environ.get("http_authenticator.username"),
                                                                             environ.get("http_authenticator.realm")))

        if trailer:
            o_list.append("%s\n" % trailer)
        o_list.append("<hr/>\n<a href='http://wsgidav.googlecode.com/'>WsgiDAV server</a> - %s\n" % util.getRfc1123Time())
        o_list.append("</body></html>")


        start_response("200 OK", [("Content-Type", "text/html"), 
                                  ("Date", util.getRfc1123Time()),
                                  ])
        return [ "\n".join(o_list) ] 
