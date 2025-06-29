# (c) 2009-2024 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
WSGI middleware that handles GET requests on collections to display directories.
"""

import os
import sys
from urllib.parse import unquote

from jinja2 import Environment, FileSystemLoader, select_autoescape

from wsgidav import __version__, util
from wsgidav.dav_error import HTTP_MEDIATYPE_NOT_SUPPORTED, HTTP_OK, DAVError
from wsgidav.mw.base_mw import BaseMiddleware
from wsgidav.util import safe_re_encode, send_redirect_response

__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)

ASSET_SHARE = "/:dir_browser"


class WsgiDavExplorer(BaseMiddleware):
    """WSGI middleware that handles GET requests on collections to display directories."""

    def __init__(self, wsgidav_app, next_app, config):
        super().__init__(wsgidav_app, next_app, config)

        self.dir_config = util.get_dict_value(config, "dav_explorer", as_dict=True)

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
        self.template = templateEnv.get_template("app.html")

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

    def _get_context(self, environ, dav_res) -> dict:
        assert dav_res.is_collection

        is_readonly = bool(
            self.dir_config.get("force_readonly")
            or environ["wsgidav.provider"].is_readonly()
        )

        is_top_dir = dav_res.path in ("", "/")

        js_config = {
            k: v
            for k, v in self.dir_config.items()
            if k
            in [
                "ignore_list",
                "max_preview_size",
                "office_support",
            ]
        }
        js_config.update(
            {
                "readonly": is_readonly,
            }
        )

        jinja_context = {
            "htdocs": self.mount_path + ASSET_SHARE,
            "version": __version__,
            "display_path": unquote(dav_res.get_href()),
            "url": dav_res.get_href(),  # util.make_complete_url(environ),
            # "parent_url": util.get_uri_parent(dav_res.get_href()),
            "is_top_dir": is_top_dir,
            "js_config": js_config,
            "is_readonly": is_readonly,
            "access": "read-only" if is_readonly else "read-write",
            "is_authenticated": False,
        }

        trailer = self.dir_config.get("page_trailer")
        if trailer is True:
            trailer = "${version} &mdash; ${copy}"

        if trailer:
            trailer = (
                trailer.replace(
                    "${version}",
                    f"<a href='https://github.com/mar10/wsgidav/' target=_blank>{util.public_wsgidav_info}</a>",
                )
                .replace("${time}", util.get_rfc1123_time())
                .replace(
                    "${copy}",
                    f"&copy; 2009-{util.get_current_year()} Martin Wendt",
                )
            )

        jinja_context["trailer"] = trailer

        if "wsgidav.auth.user_name" in environ:
            jinja_context.update(
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

        return jinja_context
