# (c) 2009-2024 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
WSGI middleware that handles GET requests on collections to display directories.
"""

import os
import sys
from fnmatch import fnmatch
from urllib.parse import unquote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from wsgidav import __version__, util
from wsgidav.dav_error import HTTP_MEDIATYPE_NOT_SUPPORTED, HTTP_OK, DAVError
from wsgidav.mw.base_mw import BaseMiddleware
from wsgidav.util import get_uri_name, safe_re_encode, send_redirect_response

__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)

ASSET_SHARE = "/:dir_browser"

DAVMOUNT_TEMPLATE = """
<dm:mount xmlns:dm="http://purl.org/NET/webdav/mount">
  <dm:url>{}</dm:url>
</dm:mount>
""".strip()

MS_OFFICE_TYPE_TO_EXT_MAP = {
    "excel": ("xls", "xlt", "xlm", "xlsm", "xlsx", "xltm", "xltx"),
    "powerpoint": ("pps", "ppt", "pptm", "pptx", "potm", "potx", "ppsm", "ppsx"),
    "word": ("doc", "dot", "docm", "docx", "dotm", "dotx"),
    "visio": ("vsd", "vsdm", "vsdx", "vstm", "vstx"),
}
MS_OFFICE_EXT_TO_TYPE_MAP = {}
for t, el in MS_OFFICE_TYPE_TO_EXT_MAP.items():
    for e in el:
        MS_OFFICE_EXT_TO_TYPE_MAP[e] = t
OPEN_OFFICE_EXTENSIONS = {"odt", "odp", "odx"}


class WsgiDavDirBrowser(BaseMiddleware):
    """WSGI middleware that handles GET requests on collections to display directories."""

    def __init__(self, wsgidav_app, next_app, config):
        super().__init__(wsgidav_app, next_app, config)

        self.dir_config = util.get_dict_value(config, "dir_browser", as_dict=True)

        # mount path must be "" or start (but not end) with '/'
        self.mount_path = config.get("mount_path") or ""

        htdocs_path = self.dir_config.get("htdocs_path")
        if htdocs_path:
            self.htdocs_path = os.path.realpath(htdocs_path)
        else:
            self.htdocs_path = os.path.join(os.path.dirname(__file__), "htdocs")

        if not os.path.isdir(self.htdocs_path):
            raise ValueError(f"Invalid dir_browser htdocs_path {self.htdocs_path!r}")

        # Add an additional read-only FS provider that serves the dir_browser assets
        self.wsgidav_app.add_provider(ASSET_SHARE, self.htdocs_path, readonly=True)
        # and make sure we have anonymous access there
        config.get("simple_dc", {}).get("user_mapping", {}).setdefault(
            ASSET_SHARE, True
        )

        # Prepare a Jinja2 template
        templateLoader = FileSystemLoader(searchpath=self.htdocs_path)
        templateEnv = Environment(loader=templateLoader, autoescape=select_autoescape())
        self.template = templateEnv.get_template("template.html")

    def is_disabled(self):
        return self.dir_config.get("enable") is False

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
            if self.dir_config.get("davmount") and "davmount" in environ.get(
                "QUERY_STRING", ""
            ):
                collectionUrl = util.make_complete_url(environ)
                collectionUrl = collectionUrl.split("?", 1)[0]
                res = util.to_bytes(DAVMOUNT_TEMPLATE.format(collectionUrl))
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

            directory_slash = self.dir_config.get("directory_slash")
            requrest_uri = environ.get("REQUEST_URI")
            if directory_slash and requrest_uri and not requrest_uri.endswith("/"):
                _logger.info(f"Redirect {requrest_uri} to {requrest_uri}/")
                return send_redirect_response(
                    environ, start_response, location=requrest_uri + "/"
                )

            context = self._get_context(environ, dav_res)

            res = self.template.render(**context)
            res = util.to_bytes(res)
            start_response(
                "200 OK",
                [
                    ("Content-Type", "text/html; charset=utf-8"),
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
            _logger.warning(
                f"Raising DAVError {safe_re_encode(e.get_user_info(), sys.stdout.encoding)}"
            )
        raise e

    def _get_context(self, environ, dav_res):
        """
        @see: http://www.webdav.org/specs/rfc4918.html#rfc.section.9.4
        """
        assert dav_res.is_collection

        is_readonly = environ["wsgidav.provider"].is_readonly()
        ms_sharepoint_support = self.dir_config.get("ms_sharepoint_support")
        libre_office_support = self.dir_config.get("libre_office_support")
        is_top_dir = dav_res.path in ("", "/")

        # TODO: WebDAV URLs only on Windows?
        # TODO: WebDAV URLs only on HTTPS?
        # is_windows = "Windows NT " in environ.get("HTTP_USER_AGENT", "")

        context = {
            "htdocs": self.mount_path + ASSET_SHARE,
            "rows": [],
            "version": __version__,
            "display_path": unquote(dav_res.get_href()),
            "url": dav_res.get_href(),  # util.make_complete_url(environ),
            # "parent_url": util.get_uri_parent(dav_res.get_href()),
            "is_top_dir": is_top_dir,
            "config": self.dir_config,
            "is_readonly": is_readonly,
            "access": "read-only" if is_readonly else "read-write",
            "is_authenticated": False,
        }

        trailer = self.dir_config.get("response_trailer")
        if trailer is True:
            trailer = "${version} - ${time}"

        if trailer:
            trailer = trailer.replace(
                "${version}",
                f"<a href='https://github.com/mar10/wsgidav/'>{util.public_wsgidav_info}</a>",
            )
            trailer = trailer.replace("${time}", util.get_rfc1123_time())

        context["trailer"] = trailer

        rows = context["rows"]

        # Ask collection for member info list
        dir_info_list = dav_res.get_directory_info()

        if dir_info_list is None:
            # No pre-build info: traverse members
            dir_info_list = []
            childList = dav_res.get_descendants(depth="1", add_self=False)
            for res in childList:
                di = res.get_display_info()
                href = res.get_href()
                ofe_prefix = None
                tr_classes = []
                a_classes = []

                # #268 Use relative paths to support reverse proxies:
                rel_href = get_uri_name(href)
                if res.is_collection:
                    tr_classes.append("directory")
                    rel_href = f"./{rel_href}/"  # 274

                add_link_html = []

                if not is_readonly and not res.is_collection:
                    ext = os.path.splitext(href)[1].lstrip(".").lower()
                    ms_office_type = MS_OFFICE_EXT_TO_TYPE_MAP.get(ext)
                    if ms_office_type:
                        if ms_sharepoint_support:
                            ofe_prefix = f"ms-{ms_office_type}:ofe|u|"
                            a_classes.append("msoffice")
                            if libre_office_support:
                                add_link_html.append(
                                    f"<a class='edit2' title='Edit with Libre Office' href='vnd.libreoffice.command:ofv|u|{rel_href}'>Edit</a>"
                                )
                                # ofe_prefix_2 = "vnd.libreoffice.command:ofv|u|"
                                # a_classes.append("msoffice")
                        elif libre_office_support:
                            ofe_prefix = "vnd.libreoffice.command:ofv|u|"
                            # a_classes.append("msoffice")

                    elif ext in OPEN_OFFICE_EXTENSIONS:
                        if libre_office_support:
                            ofe_prefix = "vnd.libreoffice.command:ofv|u|"
                            a_classes.append("msoffice")

                if res.is_link():
                    a_classes.append("symlink")

                entry = {
                    "href": rel_href,
                    "ofe_prefix": ofe_prefix,
                    "a_class": " ".join(a_classes),
                    "add_link_html": "".join(add_link_html),
                    "tr_class": " ".join(tr_classes),
                    "display_name": res.get_display_name(),
                    "last_modified": res.get_last_modified(),
                    "is_collection": res.is_collection,
                    "content_length": res.get_content_length(),
                    "display_type": di.get("type"),
                    "display_type_comment": di.get("typeComment"),
                }

                dir_info_list.append(entry)
        #
        ignore_patterns = self.dir_config.get("ignore", [])
        if util.is_basestring(ignore_patterns):
            ignore_patterns = ignore_patterns.split(",")

        ignored_list = []
        for entry in dir_info_list:
            # Skip ignore patterns
            ignore = False
            for pat in ignore_patterns:
                if fnmatch(entry["display_name"], pat):
                    ignored_list.append(entry["display_name"])
                    # _logger.debug("Ignore {}".format(entry["display_name"]))
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
        if ignored_list:
            _logger.debug(
                f"Dir browser ignored {len(ignored_list)} entries: {ignored_list}"
            )

        # sort
        sort = "name"
        if sort == "name":
            rows.sort(
                key=lambda v: "{}{}".format(
                    not v["is_collection"], v["display_name"].lower()
                )
            )

        if "wsgidav.auth.user_name" in environ:
            context.update(
                {
                    "is_authenticated": bool(environ.get("wsgidav.auth.user_name")),
                    "user_name": (environ.get("wsgidav.auth.user_name") or "anonymous"),
                    "realm": environ.get("wsgidav.auth.realm"),
                    "user_roles": ", ".join(environ.get("wsgidav.auth.roles") or []),
                    "user_permissions": ", ".join(
                        environ.get("wsgidav.auth.permissions") or []
                    ),
                }
            )

        return context
