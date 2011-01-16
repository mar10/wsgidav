# (c) 2009-2011 Martin Wendt and contributors; see WsgiDAV http://wsgidav.googlecode.com/
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
WSGI middleware that handles GET requests on collections to display directories.

See `Developers info`_ for more information about the WsgiDAV architecture.

.. _`Developers info`: http://docs.wsgidav.googlecode.com/hg/html/develop.html  
"""
from wsgidav.dav_error import DAVError, HTTP_OK, HTTP_MEDIATYPE_NOT_SUPPORTED
from wsgidav.version import __version__
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
            davres = environ["wsgidav.provider"].getResourceInst(path, environ)

        if environ["REQUEST_METHOD"] in ("GET", "HEAD") and davres and davres.isCollection:

#            if "mozilla" not in environ.get("HTTP_USER_AGENT").lower():
#                # issue 14: Nautilus sends GET on collections
#                # http://code.google.com/p/wsgidav/issues/detail?id=14
#                util.status("Directory browsing disabled for agent '%s'" % environ.get("HTTP_USER_AGENT"))
#                self._fail(HTTP_NOT_IMPLEMENTED)
#                return self._application(environ, start_response)

            if util.getContentLength(environ) != 0:
                self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
                           "The server does not handle any body content.")
            
            if environ["REQUEST_METHOD"] == "HEAD":
                return util.sendStatusResponse(environ, start_response, HTTP_OK)

            # Support DAV mount (http://www.ietf.org/rfc/rfc4709.txt)
            dirConfig = environ["wsgidav.config"].get("dir_browser", {})
            if dirConfig.get("davmount") and "davmount" in environ.get("QUERY_STRING"):
#                collectionUrl = davres.getHref()
                collectionUrl = util.makeCompleteUrl(environ)
                collectionUrl = collectionUrl.split("?")[0]
                res = """
                    <dm:mount xmlns:dm="http://purl.org/NET/webdav/mount">
                        <dm:url>%s</dm:url>
                    </dm:mount>""" % (collectionUrl)
                # TODO: support <dm:open>%s</dm:open>

                start_response("200 OK", [("Content-Type", "application/davmount+xml"), 
                                          ("Content-Length", str(len(res))),
                                          ("Cache-Control", "private"),
                                          ("Date", util.getRfc1123Time()),
                                          ])
                return [ res ]
            
            # Profile calls
#            if True:
#                from cProfile import Profile
#                profile = Profile()
#                profile.runcall(self._listDirectory, environ, start_response)
#                # sort: 0:"calls",1:"time", 2: "cumulative"
#                profile.print_stats(sort=2)
            return self._listDirectory(davres, environ, start_response)
        
        return self._application(environ, start_response)


    def _fail(self, value, contextinfo=None, srcexception=None, errcondition=None):
        """Wrapper to raise (and log) DAVError."""
        e = DAVError(value, contextinfo, srcexception, errcondition)
        if self._verbose >= 2:
            print >>sys.stdout, "Raising DAVError %s" % e.getUserInfo()
        raise e

    
    def _listDirectory(self, davres, environ, start_response):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#rfc.section.9.4
        """
        assert davres.isCollection
        
        dirConfig = environ["wsgidav.config"].get("dir_browser", {})
        displaypath = urllib.unquote(davres.getHref())

        trailer = dirConfig.get("response_trailer")
        if trailer:
            trailer = trailer.replace("${version}", 
                "<a href='http://wsgidav.googlecode.com/'>WsgiDAV/%s</a>" % __version__)
            trailer = trailer.replace("${time}", util.getRfc1123Time())
        else:
            trailer = ("<a href='http://wsgidav.googlecode.com/'>WsgiDAV/%s</a> - %s" 
                       % (__version__, util.getRfc1123Time()))

        
        html = []
        html.append("<!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01//EN' 'http://www.w3.org/TR/html4/strict.dtd'>");
        html.append("<html>")
        html.append("<head>")
        html.append("<meta http-equiv='Content-Type' content='text/html; charset=UTF-8'>")
        html.append("<meta name='generator' content='WsgiDAV %s'>" % __version__)
        html.append("<title>WsgiDAV - Index of %s </title>" % displaypath)
        
        html.append("""\
<style type="text/css">
    img { border: 0; padding: 0 2px; vertical-align: text-bottom; }
    th, td { padding: 2px 20px 2px 2px; }
    th { text-align: left; }
    th.right { text-align: right; }
    td  { font-family: monospace; vertical-align: bottom; white-space: pre; }
    td.right { text-align: right; }
    table { border: 0; }
    a.symlink { font-style: italic; }
    p.trailer { font-size: smaller; }
</style>""")        
        # Special CSS to enable MS Internet Explorer behaviour
        if dirConfig.get("msmount"):
            html.append("""\
<style type="text/css">
    A {behavior: url(#default#AnchorClick);}
</style>""")
        
        html.append("</head><body>")

        # Title
        html.append("<h1>Index of %s</h1>" % displaypath)
        # Add DAV-Mount link and Web-Folder link
        links = []
        if dirConfig.get("davmount"):
            links.append("<a title='Open this folder in a WebDAV client.' href='%s?davmount'>Mount</a>" % util.makeCompleteUrl(environ))
        if dirConfig.get("msmount"):
            links.append("<a title='Open as Web Folder (requires Microsoft Internet Explorer)' href='' FOLDER='%s'>Open as Web Folder</a>" % util.makeCompleteUrl(environ))
#                html.append("<a href='' FOLDER='%ssetup.py'>Open setup.py as WebDAV</a>" % util.makeCompleteUrl(environ))
        if links:
            html.append("<p>%s</p>" % " &#8211; ".join(links))

        html.append("<hr>")
        # Listing
        html.append("<table>")

        html.append("<thead>")
        html.append("<tr><th>Name</th> <th>Type</th> <th class='right'>Size</th> <th class='right'>Last modified</th> </tr>")
        html.append("</thead>")
            
        html.append("<tbody>")
        if davres.path in ("", "/"):
            html.append("<tr><td>Top level share</td> <td></td> <td></td> <td></td> </tr>")
        else:
            parentUrl = util.getUriParent(davres.getHref())
            html.append("<tr><td><a href='" + parentUrl + "'>Parent Directory</a></td> <td></td> <td></td> <td></td> </tr>")

        # Ask collection for member info list
        dirInfoList = davres.getDirectoryInfo()

        if dirInfoList is None:
            # No pre-build info: traverse members
            dirInfoList = []
            childList = davres.getDescendants(depth="1", addSelf=False)
            for res in childList:
                di = res.getDisplayInfo()
                infoDict = {"href": res.getHref(),
                            "displayName": res.getDisplayName(),
                            "lastModified": res.getLastModified(),
                            "isCollection": res.isCollection,
                            "contentLength": res.getContentLength(),
                            "displayType": di.get("type"),
                            "displayTypeComment": di.get("typeComment"),
                            }
                dirInfoList.append(infoDict)
        # 
        for infoDict in dirInfoList:
            lastModified = infoDict.get("lastModified")
            if lastModified is None:
                infoDict["strModified"] = ""
            else:
                infoDict["strModified"] = util.getRfc1123Time(lastModified)
            
            infoDict["strSize"] = "-"
            if not infoDict.get("isCollection"):
                contentLength = infoDict.get("contentLength")
                if contentLength is not None:
                    infoDict["strSize"] = util.byteNumberString(contentLength)

            html.append("""\
            <tr><td><a href="%(href)s">%(displayName)s</a></td>
            <td>%(displayType)s</td>
            <td class='right'>%(strSize)s</td>
            <td class='right'>%(strModified)s</td></tr>""" % infoDict)
            
        html.append("</tbody>")
        html.append("</table>")

        html.append("<hr>") 

        if "http_authenticator.username" in environ:
            if environ.get("http_authenticator.username"):
                html.append("<p>Authenticated user: '%s', realm: '%s'.</p>" 
                              % (environ.get("http_authenticator.username"),
                                 environ.get("http_authenticator.realm")))
#            else:
#                html.append("<p>Anonymous</p>")

        if trailer:
            html.append("<p class='trailer'>%s</p>" % trailer)
#            html.append("<p class='trailer'><a href='http://wsgidav.googlecode.com/'>WsgiDAV/%s</a> - %s</p>" 
#                          % (__version__, util.getRfc1123Time()))

        html.append("</body></html>")

        body = "\n".join(html) 

        start_response("200 OK", [("Content-Type", "text/html"), 
                                  ("Content-Length", str(len(body))),
                                  ("Date", util.getRfc1123Time()),
                                  ])
        return [ body ] 
