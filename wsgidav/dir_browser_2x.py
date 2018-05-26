# (c) 2009-2018 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
WSGI middleware that handles GET requests on collections to display directories.
"""
import os
import sys

from wsgidav import __version__, compat, util
from wsgidav.dav_error import HTTP_MEDIATYPE_NOT_SUPPORTED, HTTP_OK, DAVError
from wsgidav.middleware import BaseMiddleware
from wsgidav.util import safeReEncode

__docformat__ = "reStructuredText"

_logger = util.getModuleLogger(__name__)


msOfficeTypeToExtMap = {
    "excel": ("xls", "xlt", "xlm", "xlsm", "xlsx", "xltm", "xltx"),
    "powerpoint": ("pps", "ppt", "pptm", "pptx", "potm", "potx", "ppsm", "ppsx"),
    "word": ("doc", "dot", "docm", "docx", "dotm", "dotx"),
    "visio": ("vsd", "vsdm", "vsdx", "vstm", "vstx"),
    }
msOfficeExtToTypeMap = {}
for t, el in msOfficeTypeToExtMap.items():
    for e in el:
        msOfficeExtToTypeMap[e] = t


PAGE_CSS = """\
    img { border: 0; padding: 0 2px; vertical-align: text-bottom; }
    th, td { padding: 2px 20px 2px 2px; }
    th { text-align: left; }
    th.right { text-align: right; }
    td  { font-family: monospace; vertical-align: bottom; white-space: pre; }
    td.right { text-align: right; }
    table { border: 0; }
    a.symlink { font-style: italic; }
    p.trailer { font-size: smaller; }
"""

PAGE_SCRIPT = """\
function onLoad() {
//    console.log("loaded.");
}

/* Event delegation handler for clicks on a-tags with class 'msoffice'. */
function onClickTable(event) {
    var target = event.target || event.srcElement,
        href = target.href;

    if( href && target.className === "msoffice" ){
        if( openWithSharePointPlugin(href) ){
            // prevent default processing
            return false;
        }
    }
}

function openWithSharePointPlugin(url) {
    var res = false,
        control = null,
        isFF = false;

    // Get the most recent version of the SharePoint plugin
    if( window.ActiveXObject ){
        try {
            control = new ActiveXObject("SharePoint.OpenDocuments.3"); // Office 2007
        } catch(e) {
            try {
                control = new ActiveXObject("SharePoint.OpenDocuments.2"); // Office 2003
            } catch(e2) {
                try {
                    control = new ActiveXObject("SharePoint.OpenDocuments.1"); // Office 2000/XP
                } catch(e3) {
                    window.console && console.warn("Could not create ActiveXObject('SharePoint.OpenDocuments'). Check your browsers security settings.");
                    return false;
                }
            }
        }
        if( !control ){
            window.console && console.warn("Cannot instantiate the required ActiveX control to open the document. This is most likely because you do not have Office installed or you have an older version of Office.");
        }
    } else {
        window.console && console.log("Non-IE: using FFWinPlugin Plug-in...");
        control = document.getElementById("winFirefoxPlugin");
        isFF = true;
    }

    try {
//      window.console && console.log("SharePoint.OpenDocuments.EditDocument('" + url + "')...");
        res = control.EditDocument(url);
//      window.console && console.log("SharePoint.OpenDocuments.EditDocument('" + url + "')... res = ", res);
        if( !res ){
            window.console && console.warn("SharePoint.OpenDocuments.EditDocument('" + url + "') returned false.");
        }
    } catch (e){
        window.console && console.warn("SharePoint.OpenDocuments.EditDocument('" + url + "') failed.", e);
    }
    return res;
}
"""  # noqa


class WsgiDavDirBrowser(BaseMiddleware):
    """WSGI middleware that handles GET requests on collections to display directories."""

    def __init__(self, wsgidav_app, next_app, config):
        super(WsgiDavDirBrowser, self).__init__(wsgidav_app, next_app, config)
        self._verbose = 2

    def __call__(self, environ, start_response):
        path = environ["PATH_INFO"]

        davres = None
        if environ["wsgidav.provider"]:
            davres = environ["wsgidav.provider"].getResourceInst(path, environ)

        if environ["REQUEST_METHOD"] in ("GET", "HEAD") and davres and davres.isCollection:

            # if "mozilla" not in environ.get("HTTP_USER_AGENT").lower():
            #     # issue 14: Nautilus sends GET on collections
            #     # http://code.google.com/p/wsgidav/issues/detail?id=14
            #     util.status("Directory browsing disabled for agent '{}'"
            #                 .format(environ.get("HTTP_USER_AGENT")))
            #     self._fail(HTTP_NOT_IMPLEMENTED)
            #     return self.next_app(environ, start_response)

            if util.getContentLength(environ) != 0:
                self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
                           "The server does not handle any body content.")

            if environ["REQUEST_METHOD"] == "HEAD":
                return util.sendStatusResponse(environ, start_response, HTTP_OK)

            # Support DAV mount (http://www.ietf.org/rfc/rfc4709.txt)
            dirConfig = environ["wsgidav.config"].get("dir_browser", {})
            if dirConfig.get("davmount") and "davmount" in environ.get("QUERY_STRING", ""):
                #                collectionUrl = davres.getHref()
                collectionUrl = util.makeCompleteUrl(environ)
                collectionUrl = collectionUrl.split("?")[0]
                res = """
                    <dm:mount xmlns:dm="http://purl.org/NET/webdav/mount">
                        <dm:url>{}</dm:url>
                    </dm:mount>""".format(collectionUrl)
                # TODO: support <dm:open>%s</dm:open>

                start_response("200 OK", [("Content-Type", "application/davmount+xml"),
                                          ("Content-Length", str(len(res))),
                                          ("Cache-Control", "private"),
                                          ("Date", util.getRfc1123Time()),
                                          ])
                return [res]

            # Profile calls
#            if True:
#                from cProfile import Profile
#                profile = Profile()
#                profile.runcall(self._listDirectory, environ, start_response)
#                # sort: 0:"calls",1:"time", 2: "cumulative"
#                profile.print_stats(sort=2)
            return self._listDirectory(davres, environ, start_response)

        return self.next_app(environ, start_response)

    # @staticmethod
    # def isSuitable(config):
    #     return config.get("dir_browser") and config["dir_browser"].get("enable", True)

    def _fail(self, value, contextinfo=None, srcexception=None, errcondition=None):
        """Wrapper to raise (and log) DAVError."""
        e = DAVError(value, contextinfo, srcexception, errcondition)
        if self._verbose >= 4:
            _logger.error("Raising DAVError {}".format(
                    safeReEncode(e.getUserInfo(), sys.stdout.encoding)))
        raise e

    def _listDirectory(self, davres, environ, start_response):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#rfc.section.9.4
        """
        assert davres.isCollection

        dirConfig = environ["wsgidav.config"].get("dir_browser", {})
        displaypath = compat.unquote(davres.getHref())
        isReadOnly = environ["wsgidav.provider"].isReadOnly()

        trailer = dirConfig.get("response_trailer")
        if trailer:
            trailer = trailer.replace(
                "${version}",
                "<a href='https://github.com/mar10/wsgidav/'>WsgiDAV/{}</a>".format(__version__))
            trailer = trailer.replace("${time}", util.getRfc1123Time())
        else:
            trailer = ("<a href='https://github.com/mar10/wsgidav/'>WsgiDAV/{}</a> - {}"
                       .format(__version__, util.getRfc1123Time()))

        html = []
        html.append(
            "<!DOCTYPE HTML PUBLIC '-//W3C//DTD HTML 4.01//EN' "
            "'http://www.w3.org/TR/html4/strict.dtd'>")
        html.append("<html>")
        html.append("<head>")
        html.append("<meta http-equiv='Content-Type' content='text/html; charset=UTF-8'>")
        html.append("<meta name='generator' content='WsgiDAV {}'>".format(__version__))
        html.append("<title>WsgiDAV - Index of {} </title>".format(displaypath))
        html.append("<script type='text/javascript'>{}</script>".format(PAGE_SCRIPT))
        html.append("<style type='text/css'>{}</style>".format(PAGE_CSS))

        # Special CSS to enable MS Internet Explorer behaviour
        if dirConfig.get("ms_mount"):
            html.append(
                "<style type='text/css'> A {behavior: url(#default#AnchorClick);} </style>")

        if dirConfig.get("ms_sharepoint_plugin"):
            html.append(
                "<object id='winFirefoxPlugin' type='application/x-sharepoint' width='0' "
                "height='0' style=''visibility: hidden;'></object>")

        html.append("</head>")
        html.append("<body onload='onLoad()'>")

        # Title
        html.append("<h1>Index of {}</h1>".format(displaypath))
        # Add DAV-Mount link and Web-Folder link
        links = []
        if dirConfig.get("davmount"):
            links.append("<a title='Open this folder in a WebDAV client.' "
                         "href='{}?davmount'>Mount</a>".format(util.makeCompleteUrl(environ)))
        if dirConfig.get("ms_mount"):
            links.append("<a title='Open as Web Folder (requires Microsoft Internet Explorer)' "
                         "href='' FOLDER='{}'>Open as Web Folder</a>"
                         .format(util.makeCompleteUrl(environ)))
#                html.append("<a href='' FOLDER='{}setup.py'>Open setup.py as WebDAV</a>"
#                            .format(util.makeCompleteUrl(environ)))
        if links:
            html.append("<p>{}</p>".format(" &#8211; ".join(links)))

        html.append("<hr>")
        # Listing
        html.append("<table onclick='return onClickTable(event)'>")

        html.append("<thead>")
        html.append(
            "<tr><th>Name</th> <th>Type</th> <th class='right'>Size</th> "
            "<th class='right'>Last modified</th> </tr>")
        html.append("</thead>")

        html.append("<tbody>")
        if davres.path in ("", "/"):
            html.append(
                "<tr><td>Top level share</td> <td></td> <td></td> <td></td> </tr>")
        else:
            parentUrl = util.getUriParent(davres.getHref())
            html.append("<tr><td><a href='" + parentUrl +
                        "'>Parent Directory</a></td> <td></td> <td></td> <td></td> </tr>")

        # Ask collection for member info list
        dirInfoList = davres.getDirectoryInfo()

        if dirInfoList is None:
            # No pre-build info: traverse members
            dirInfoList = []
            childList = davres.getDescendants(depth="1", addSelf=False)
            for res in childList:
                di = res.getDisplayInfo()
                href = res.getHref()
                infoDict = {"href": href,
                            "class": "",
                            "displayName": res.getDisplayName(),
                            "lastModified": res.getLastModified(),
                            "isCollection": res.isCollection,
                            "contentLength": res.getContentLength(),
                            "displayType": di.get("type"),
                            "displayTypeComment": di.get("typeComment"),
                            }

                if not isReadOnly and not res.isCollection:
                    ext = os.path.splitext(href)[1].lstrip(".").lower()
                    officeType = msOfficeExtToTypeMap.get(ext)
                    if officeType:
                        if dirConfig.get("ms_sharepoint_plugin"):
                            infoDict["class"] = "msoffice"
                        elif dirConfig.get("ms_sharepoint_urls"):
                            infoDict[
                                "href"] = "ms-{}:ofe|u|{}".format(officeType, href)

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
            <tr><td><a href="{href}" class="{class}">{displayName}</a></td>
            <td>{displayType}</td>
            <td class='right'>{strSize}</td>
            <td class='right'>{strModified}</td></tr>""".format(**infoDict))

            # html.append("""\
            # <tr><td><a href="%(href)s" class="%(class)s">%(displayName)s</a></td>
            # <td>%(displayType)s</td>
            # <td class='right'>%(strSize)s</td>
            # <td class='right'>%(strModified)s</td></tr>""" % infoDict)

        html.append("</tbody>")
        html.append("</table>")

        html.append("<hr>")

        if "http_authenticator.username" in environ:
            if environ.get("http_authenticator.username"):
                html.append("<p>Authenticated user: '{}', realm: '{}'.</p>"
                            .format(environ.get("http_authenticator.username"),
                                    environ.get("http_authenticator.realm")))
#            else:
#                html.append("<p>Anonymous</p>")

        if trailer:
            html.append("<p class='trailer'>{}</p>".format(trailer))

        html.append("</body></html>")

        body = "\n".join(html)
        body = compat.to_bytes(body)

        start_response("200 OK", [("Content-Type", "text/html"),
                                  ("Content-Length", str(len(body))),
                                  ("Date", util.getRfc1123Time()),
                                  ])
        return [body]
