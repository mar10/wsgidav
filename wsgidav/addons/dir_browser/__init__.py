# -*- coding: utf-8 -*-
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

        dav_res = None
        if environ["wsgidav.provider"]:
            dav_res = environ["wsgidav.provider"].get_resource_inst(path, environ)

        if (
            environ["REQUEST_METHOD"] in ("GET", "HEAD")
            and dav_res
            and dav_res.is_collection
        ):

            if util.get_content_length(environ) != 0:
                self._fail(
                    HTTP_MEDIATYPE_NOT_SUPPORTED,
                    "The server does not handle any body content.",
                )

            if environ["REQUEST_METHOD"] == "HEAD":
                return util.send_status_response(
                    environ, start_response, HTTP_OK, is_head=True
                )

            # Support DAV mount (http://www.ietf.org/rfc/rfc4709.txt)
            dirConfig = environ["wsgidav.config"].get("dir_browser", {})
            if dirConfig.get("davmount") and "davmount" in environ.get(
                "QUERY_STRING", ""
            ):
                collectionUrl = util.make_complete_url(environ)
                collectionUrl = collectionUrl.split("?", 1)[0]
                res = compat.to_bytes(DAVMOUNT_TEMPLATE.format(collectionUrl))
                # TODO: support <dm:open>%s</dm:open>

                start_response(
                    "200 OK",
                    [
                        ("Content-Type", "application/davmount+xml"),
                        ("Content-Length", str(len(res))),
                        ("Cache-Control", "private"),
                        ("Date", util.get_rfc1123_time()),
                    ],
                )
                return [res]

            context = self._get_context(environ, dav_res)

            res = self.template.render(**context)
            res = compat.to_bytes(res)
            start_response(
                "200 OK",
                [
                    ("Content-Type", "text/html"),
                    ("Content-Length", str(len(res))),
                    ("Cache-Control", "private"),
                    ("Date", util.get_rfc1123_time()),
                ],
            )
            return [res]

        return self.next_app(environ, start_response)

    def _fail(self, value, context_info=None, src_exception=None, err_condition=None):
        """Wrapper to raise (and log) DAVError."""
        e = DAVError(value, context_info, src_exception, err_condition)
        if self.verbose >= 4:
            _logger.warn(
                "Raising DAVError {}".format(
                    safe_re_encode(e.get_user_info(), sys.stdout.encoding)
                )
            )
        raise e

    def _get_context(self, environ, dav_res):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#rfc.section.9.4
        """
        assert dav_res.is_collection

        dirConfig = environ["wsgidav.config"].get("dir_browser", {})
        is_readonly = environ["wsgidav.provider"].is_readonly()

        context = {
            "htdocs": (self.config.get("mount_path") or "") + ASSET_SHARE,
            "rows": [],
            "version": __version__,
            "display_path": compat.unquote(dav_res.get_href()),
            "url": dav_res.get_href(),  # util.make_complete_url(environ),
            "parent_url": util.get_uri_parent(dav_res.get_href()),
            "config": dirConfig,
            "is_readonly": is_readonly,
        }

        trailer = dirConfig.get("response_trailer")
        if trailer is True:
            trailer = "${version} - ${time}"

        if trailer:
            trailer = trailer.replace(
                "${version}",
                "<a href='https://github.com/mar10/wsgidav/'>WsgiDAV/{}</a>".format(
                    __version__
                ),
            )
            trailer = trailer.replace("${time}", util.get_rfc1123_time())

        context["trailer"] = trailer

        rows = context["rows"]

        # Ask collection for member info list
        dirInfoList = dav_res.get_directory_info()

        if dirInfoList is None:
            # No pre-build info: traverse members
            dirInfoList = []
            childList = dav_res.get_descendants(depth="1", add_self=False)
            for res in childList:
                di = res.get_display_info()
                href = res.get_href()
                ofe_prefix = None
                tr_classes = []
                a_classes = []
                if res.is_collection:
                    tr_classes.append("directory")

                if not is_readonly and not res.is_collection:
                    ext = os.path.splitext(href)[1].lstrip(".").lower()
                    officeType = msOfficeExtToTypeMap.get(ext)
                    if officeType:
                        if dirConfig.get("ms_sharepoint_support"):
                            ofe_prefix = "ms-{}:ofe|u|".format(officeType)
                            a_classes.append("msoffice")
                        # elif dirConfig.get("ms_sharepoint_plugin"):
                        #     a_classes.append("msoffice")
                        # elif dirConfig.get("ms_sharepoint_urls"):
                        #     href = "ms-{}:ofe|u|{}".format(officeType, href)

                entry = {
                    "href": href,
                    "ofe_prefix": ofe_prefix,
                    "a_class": " ".join(a_classes),
                    "tr_class": " ".join(tr_classes),
                    "display_name": res.get_display_name(),
                    "last_modified": res.get_last_modified(),
                    "is_collection": res.is_collection,
                    "content_length": res.get_content_length(),
                    "display_type": di.get("type"),
                    "display_type_comment": di.get("typeComment"),
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
                if fnmatch(entry["display_name"], pat):
                    _logger.debug("Ignore {}".format(entry["display_name"]))
                    ignore = True
                    break
            if ignore:
                continue
            #
            last_modified = entry.get("last_modified")
            if last_modified is None:
                entry["str_modified"] = ""
            else:
                entry["str_modified"] = util.get_rfc1123_time(last_modified)

            entry["str_size"] = "-"
            if not entry.get("is_collection"):
                content_length = entry.get("content_length")
                if content_length is not None:
                    entry["str_size"] = util.byte_number_string(content_length)

            rows.append(entry)

        # sort
        sort = "name"
        if sort == "name":
            rows.sort(
                key=lambda v: "{}{}".format(
                    not v["is_collection"], v["display_name"].lower()
                )
            )

        if "http_authenticator.user_name" in environ:
            context["user_name"] = (
                environ.get("http_authenticator.user_name") or "anonymous"
            )
            context["realm"] = environ.get("http_authenticator.realm")

        return context
