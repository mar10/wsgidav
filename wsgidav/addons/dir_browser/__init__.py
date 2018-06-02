# (c) 2009-2018 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
WSGI middleware that handles GET requests on collections to display directories.
"""
import os
import sys

from fnmatch import fnmatch
from jinja2 import Environment, FileSystemLoader

from wsgidav import __version__, compat, util
from wsgidav.dav_error import HTTP_MEDIATYPE_NOT_SUPPORTED, HTTP_OK, DAVError
from wsgidav.middleware import BaseMiddleware
from wsgidav.util import safe_re_encode

__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)

ASSET_SHARE = "/:dir_browser"

DAVMOUNT_TEMPLATE = """
<dm:mount xmlns:dm="http://purl.org/NET/webdav/mount">
  <dm:url>{}</dm:url>
</dm:mount>
""".strip()

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


class WsgiDavDirBrowser(BaseMiddleware):
    """WSGI middleware that handles GET requests on collections to display directories."""

    def __init__(self, wsgidav_app, next_app, config):
        super(WsgiDavDirBrowser, self).__init__(wsgidav_app, next_app, config)
        self.htdocs_path = os.path.join(os.path.dirname(__file__), "htdocs")

        # Add an additional read-only FS provider that serves the dir_browser assets
        self.wsgidav_app.add_provider(ASSET_SHARE, self.htdocs_path, readonly=True)

        # Prepare a Jinja2 template
        templateLoader = FileSystemLoader(searchpath=self.htdocs_path)
        templateEnv = Environment(loader=templateLoader)
        self.template = templateEnv.get_template("template.html")

    def __call__(self, environ, start_response):
        path = environ["PATH_INFO"]

        davres = None
        if environ["wsgidav.provider"]:
            davres = environ["wsgidav.provider"].get_resource_inst(path, environ)

        if environ["REQUEST_METHOD"] in ("GET", "HEAD") and davres and davres.is_collection:

            if util.get_content_length(environ) != 0:
                self._fail(HTTP_MEDIATYPE_NOT_SUPPORTED,
                           "The server does not handle any body content.")

            if environ["REQUEST_METHOD"] == "HEAD":
                return util.send_status_response(environ, start_response, HTTP_OK)

            # Support DAV mount (http://www.ietf.org/rfc/rfc4709.txt)
            dirConfig = environ["wsgidav.config"].get("dir_browser", {})
            if dirConfig.get("davmount") and "davmount" in environ.get("QUERY_STRING", ""):
                collectionUrl = util.make_complete_url(environ)
                collectionUrl = collectionUrl.split("?", 1)[0]
                res = compat.to_bytes(DAVMOUNT_TEMPLATE.format(collectionUrl))
                # TODO: support <dm:open>%s</dm:open>

                start_response("200 OK", [("Content-Type", "application/davmount+xml"),
                                          ("Content-Length", str(len(res))),
                                          ("Cache-Control", "private"),
                                          ("Date", util.get_rfc1123_time()),
                                          ])
                return [res]

            context = self._get_context(environ, davres)

            res = self.template.render(**context)
            res = compat.to_bytes(res)
            start_response("200 OK", [("Content-Type", "text/html"),
                                      ("Content-Length", str(len(res))),
                                      ("Cache-Control", "private"),
                                      ("Date", util.get_rfc1123_time()),
                                      ])
            return [res]

        return self.next_app(environ, start_response)

    def _fail(self, value, contextinfo=None, srcexception=None, errcondition=None):
        """Wrapper to raise (and log) DAVError."""
        e = DAVError(value, contextinfo, srcexception, errcondition)
        if self.verbose >= 4:
            _logger.warn("Raising DAVError {}".format(
                    safe_re_encode(e.get_user_info(), sys.stdout.encoding)))
        raise e

    def _get_context(self, environ, davres):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#rfc.section.9.4
        """
        assert davres.is_collection

        dirConfig = environ["wsgidav.config"].get("dir_browser", {})
        isReadOnly = environ["wsgidav.provider"].is_readonly()

        context = {
            "htdocs": (self.config.get("mount_path") or "") + ASSET_SHARE,
            "rows": [],
            "version": __version__,
            "displaypath": compat.unquote(davres.get_href()),
            "url": davres.get_href(),  # util.make_complete_url(environ),
            "parentUrl": util.get_uri_parent(davres.get_href()),
            "config": dirConfig,
            "is_readonly": isReadOnly,
            }

        trailer = dirConfig.get("response_trailer")
        if trailer is True:
            trailer = "${version} - ${time}"

        if trailer:
            trailer = trailer.replace(
                "${version}",
                "<a href='https://github.com/mar10/wsgidav/'>WsgiDAV/{}</a>".format(__version__))
            trailer = trailer.replace("${time}", util.get_rfc1123_time())

        context["trailer"] = trailer

        rows = context["rows"]

        # Ask collection for member info list
        dirInfoList = davres.get_directory_info()

        if dirInfoList is None:
            # No pre-build info: traverse members
            dirInfoList = []
            childList = davres.get_descendants(depth="1", addSelf=False)
            for res in childList:
                di = res.get_display_info()
                href = res.get_href()
                classes = []
                if res.is_collection:
                    classes.append("directory")

                if not isReadOnly and not res.is_collection:
                    ext = os.path.splitext(href)[1].lstrip(".").lower()
                    officeType = msOfficeExtToTypeMap.get(ext)
                    if officeType:
                        if dirConfig.get("ms_sharepoint_plugin"):
                            classes.append("msoffice")
                        elif dirConfig.get("ms_sharepoint_urls"):
                            href = "ms-{}:ofe|u|{}".format(officeType, href)

                entry = {
                    "href": href,
                    "class": " ".join(classes),
                    "displayName": res.get_display_name(),
                    "lastModified": res.get_last_modified(),
                    "is_collection": res.is_collection,
                    "contentLength": res.get_content_length(),
                    "displayType": di.get("type"),
                    "displayTypeComment": di.get("typeComment"),
                    }

                dirInfoList.append(entry)
        #
        ignore_patterns = dirConfig.get("ignore", [])
        if compat.is_basestring(ignore_patterns):
            ignore_patterns = ignore_patterns.split(",")

        for entry in dirInfoList:
            # Skip ignore patterns
            ignore = False
            for pat in ignore_patterns:
                if fnmatch(entry["displayName"], pat):
                    _logger.debug("Ignore {}".format(entry["displayName"]))
                    ignore = True
                    break
            if ignore:
                continue
            #
            lastModified = entry.get("lastModified")
            if lastModified is None:
                entry["strModified"] = ""
            else:
                entry["strModified"] = util.get_rfc1123_time(lastModified)

            entry["strSize"] = "-"
            if not entry.get("is_collection"):
                contentLength = entry.get("contentLength")
                if contentLength is not None:
                    entry["strSize"] = util.byte_number_string(contentLength)

            rows.append(entry)

        # sort
        sort = "name"
        if sort == "name":
            rows.sort(key=lambda v:
                      "{}{}".format(not v["is_collection"], v["displayName"].lower()))

        if "http_authenticator.username" in environ:
            context["username"] = environ.get("http_authenticator.username") or "anonymous"
            context["realm"] = environ.get("http_authenticator.realm")

        return context
