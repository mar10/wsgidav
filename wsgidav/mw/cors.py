# (c) 2009-2024 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
WSGI middleware used for CORS support (optional).

Respond to CORS preflight OPTIONS request and inject CORS headers.
"""

from wsgidav import util
from wsgidav.mw.base_mw import BaseMiddleware

__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)


class Cors(BaseMiddleware):
    def __init__(self, wsgidav_app, next_app, config):
        super().__init__(wsgidav_app, next_app, config)
        opts = config.get("cors", None)
        if opts is None:
            opts = {}

        allow_origins = opts.get("allow_origin")
        if type(allow_origins) is str:
            allow_origins = allow_origins.strip()
            if allow_origins != "*":
                allow_origins = [allow_origins]
        elif allow_origins:
            allow_origins = [ao.strip() for ao in allow_origins]

        allow_headers = ",".join(util.to_set(opts.get("allow_headers")))
        allow_methods = ",".join(util.to_set(opts.get("allow_methods")))
        expose_headers = ",".join(util.to_set(opts.get("expose_headers")))
        allow_credentials = opts.get("allow_credentials", False)
        max_age = opts.get("max_age")
        always_headers = opts.get("add_always")

        add_always = []
        if allow_credentials:
            add_always.append(("Access-Control-Allow-Credentials", "true"))
        if always_headers:
            if type(always_headers) is not dict:
                raise ValueError(
                    f"cors.add_always must be a list a dict: {always_headers}"
                )
            for n, v in always_headers.items():
                add_always.append((n, v))

        add_non_preflight = add_always[:]
        if expose_headers:
            add_always.append(("Access-Control-Expose-Headers", expose_headers))

        add_preflight = add_always[:]
        if allow_headers:
            add_preflight.append(("Access-Control-Allow-Headers", allow_headers))
        if allow_methods:
            add_preflight.append(("Access-Control-Allow-Methods", allow_methods))
        if max_age:
            add_preflight.append(("Access-Control-Max-Age", str(int(max_age))))

        self.non_preflight_headers = add_non_preflight
        self.preflight_headers = add_preflight
        #: Either '*' or al list of origins
        self.allow_origins = allow_origins

    def __repr__(self):
        allow_origin = self.get_config("cors.allow_origin", None)
        return f"{self.__module__}.{self.__class__.__name__}({allow_origin})"

    def is_disabled(self):
        """Optionally return True to skip this module on startup."""
        return not self.get_config("cors.allow_origin", False)

    def __call__(self, environ, start_response):
        method = environ["REQUEST_METHOD"].upper()
        origin = environ.get("HTTP_ORIGIN")
        ac_req_meth = environ.get("HTTP_ACCESS_CONTROL_REQUEST_METHOD")
        ac_req_headers = environ.get("HTTP_ACCESS_CONTROL_REQUEST_HEADERS")

        acao_headers = None
        if self.allow_origins == "*":
            acao_headers = [("Access-Control-Allow-Origin", "*")]
        elif origin in self.allow_origins:
            acao_headers = [
                ("Access-Control-Allow-Origin", origin),
                ("Vary", "Origin"),
            ]

        if acao_headers:
            _logger.debug(
                f"Granted CORS {method} {environ['PATH_INFO']!r} "
                f"{ac_req_meth!r}, headers: {ac_req_headers}, origin: {origin!r}"
            )
        else:
            # Deny (still return 200 on preflight)
            _logger.warning(
                f"Denied CORS {method} {environ['PATH_INFO']!r} "
                f"{ac_req_meth!r}, headers: {ac_req_headers}, origin: {origin!r}"
            )

        is_preflight = method == "OPTIONS" and ac_req_meth is not None

        # Handle preflight request
        if is_preflight:
            # Always return 2xx, but only add Access-Control-Allow-Origin etc.
            # if Origin is allowed
            resp_headers = [
                ("Content-Length", "0"),
                ("Date", util.get_rfc1123_time()),
            ]
            if acao_headers:
                resp_headers += acao_headers + self.preflight_headers

            start_response("204 No Content", resp_headers)
            return [b""]

        # non_preflight CORS request
        def wrapped_start_response(status, headers, exc_info=None):
            if acao_headers:
                util.update_headers_in_place(
                    headers,
                    acao_headers + self.non_preflight_headers,
                )
            start_response(status, headers, exc_info)

        return self.next_app(environ, wrapped_start_response)
