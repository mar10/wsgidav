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
        
        davres = None
        if environ["wsgidav.provider"]:
            davres = environ["wsgidav.provider"].getResourceInst(path)

        if environ["REQUEST_METHOD"] in ("GET", "HEAD") and davres and davres.isCollection():

            if util.getContentLength(environ) != 0:
                self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
                           "The server does not handle any body content.")
            
            if environ["REQUEST_METHOD"] == "HEAD":
                return util.sendSimpleResponse(environ, start_response, HTTP_OK)
            
#            if True:
#                from cProfile import Profile
#                profile = Profile()
#                profile.runcall(self._listDirectory, environ, start_response)
#                # sort: 0:"calls",1:"time", 2: "cumulative"
#                profile.print_stats(sort=2)
            return self._listDirectory(davres, environ, start_response)
        
        return self._application(environ, start_response)


    def _fail(self, value, contextinfo=None, srcexception=None, preconditionCode=None):
        """Wrapper to raise (and log) DAVError."""
        e = DAVError(value, contextinfo, srcexception, preconditionCode)
        if self._verbose >= 2:
            print >>sys.stderr, "Raising DAVError %s" % e.getUserInfo()
        raise e

    
    def _listDirectory(self, davres, environ, start_response):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#rfc.section.9.4
        """
        assert davres.isCollection()
        
        displaypath = urllib.unquote(davres.getHref())
        trailer = environ.get("wsgidav.config", {}).get("response_trailer")
        
        o_list = []
        o_list.append("<html><head>")
        o_list.append("<meta http-equiv='Content-Type' content='text/html; charset=UTF-8' />")
        o_list.append("<title>WsgiDAV - Index of %s </title>" % displaypath)
        o_list.append("""\
<style type="text/css">
    img { border: 0; padding: 0 2px; vertical-align: text-bottom; }
    td  { font-family: monospace; padding: 2px 3px; vertical-align: bottom; white-space: pre; }
    td.right { text-align: right; padding: 2px 10px 2px 3px; }
    table { border: 0; }
    a.symlink { font-style: italic; }
</style>""")        
        o_list.append("</head><body>")
        o_list.append("<h1>%s</h1>" % displaypath)
        o_list.append("<hr/><table>")

        if davres.path in ("", "/"):
            o_list.append("<tr><td colspan='4'>Top level share</td></tr>")
        else:
            parentUrl = util.getUriParent(davres.getHref())
            o_list.append("<tr><td colspan='4'><a href='" + parentUrl + "'>Up to higher level</a></td></tr>")

        for res in davres.getDescendants(depth="1", addSelf=False):

            infoDict = {"url": res.getHref(),
                        "displayName": res.displayName(),
                        "displayType": res.displayType(),
                        "strModified": "",
                        "strSize": "",
                        }

            if res.modified() is not None:
                infoDict["strModified"] = util.getRfc1123Time(res.modified())
            if res.contentLength() is not None and not res.isCollection():
                infoDict["strSize"] = util.byteNumberString(res.contentLength())
 
            o_list.append("""\
            <tr><td><a href="%(url)s">%(displayName)s</a></td>
            <td>%(displayType)s</td>
            <td class='right'>%(strSize)s</td>
            <td class='right'>%(strModified)s</td></tr>\n""" % infoDict)
            
        o_list.append("</table>\n")

        if "http_authenticator.username" in environ:
            o_list.append("<p>Authenticated user: '%s', realm: '%s'.</p>" 
                          % (environ.get("http_authenticator.username"),
                             environ.get("http_authenticator.realm")))

        if trailer:
            o_list.append("%s\n" % trailer)
        o_list.append("<hr/>\n<a href='http://wsgidav.googlecode.com/'>WsgiDAV server</a> - %s\n" % util.getRfc1123Time())
        o_list.append("</body></html>")

        start_response("200 OK", [("Content-Type", "text/html"), 
                                  ("Date", util.getRfc1123Time()),
                                  ])
        return [ "\n".join(o_list) ] 
