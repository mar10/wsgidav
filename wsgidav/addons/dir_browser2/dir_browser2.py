# (c) 2009-2018 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
WSGI middleware that handles GET requests on collections to display directories.
"""
import os
import sys

from jinja2 import Template

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


class WsgiDavDirBrowser2(BaseMiddleware):
    """WSGI middleware that handles GET requests on collections to display directories."""

    def __init__(self, application, config):
        self._application = application
        self._verbose = config.get("verbose", 3)
        self.template = Template("Hello {{ name }}!")

    def __call__(self, environ, start_response):
        path = environ["PATH_INFO"]

        # self.template.render(name="John")

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
            #     return self._application(environ, start_response)

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

        return self._application(environ, start_response)

    @staticmethod
    def isSuitable(config):
        return config.get("dir_browser") and config["dir_browser"].get("enable", True)

    def _fail(self, value, contextinfo=None, srcexception=None, errcondition=None):
        """Wrapper to raise (and log) DAVError."""
        e = DAVError(value, contextinfo, srcexception, errcondition)
        if self._verbose >= 2:
            _logger.error("Raising DAVError {}".format(
                          safeReEncode(e.getUserInfo(), sys.stdout.encoding)))
        raise e

    def _listDirectory(self, davres, environ, start_response):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#rfc.section.9.4
        """
        assert davres.isCollection

        dirConfig = environ["wsgidav.config"].get("dir_browser", {})
        # displaypath = compat.unquote(davres.getHref())
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

        # Ask collection for member info list
        dirInfoList = davres.getDirectoryInfo()

        if dirInfoList is None:
            # No pre-build info: traverse members
            dirInfoList = []
            childList = davres.getDescendants(depth="1", addSelf=False)
            for res in childList:
                di = res.getDisplayInfo()
                href = res.getHref()
                infoDict = {
                    "href": href,
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
