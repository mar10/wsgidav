# -*- coding: utf-8 -*-
# (c) 2009-2020 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
WSGI middleware to catch application thrown DAVErrors and return proper
responses.
"""
from wsgidav import util
from wsgidav.dav_error import (
    as_DAVError,
    DAVError,
    get_http_status_string,
    HTTP_INTERNAL_ERROR,
    HTTP_NO_CONTENT,
    HTTP_NOT_MODIFIED,
)
from wsgidav.middleware import BaseMiddleware

import traceback


__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)


# ========================================================================
# ErrorPrinter
# ========================================================================
class ErrorPrinter(BaseMiddleware):
    def __init__(self, wsgidav_app, next_app, config):
        super(ErrorPrinter, self).__init__(wsgidav_app, next_app, config)
        self.err_config = config.get("error_printer", {})
        self.catch_all_exceptions = self.err_config.get("catch_all", False)

    def is_disabled(self):
        return self.err_config.get("enable") is False

    def __call__(self, environ, start_response):
        # Intercept start_response
        sub_app_start_response = util.SubAppStartResponse()

        try:
            try:
                # request_server app may be a generator (for example the GET handler)
                # So we must iterate - not return self.next_app(..)!
                # Otherwise the we could not catch exceptions here.
                response_started = False
                app_iter = self.next_app(environ, sub_app_start_response)
                for v in app_iter:
                    # Start response (the first time)
                    if not response_started:
                        # Success!
                        start_response(
                            sub_app_start_response.status,
                            sub_app_start_response.response_headers,
                            sub_app_start_response.exc_info,
                        )
                    response_started = True

                    yield v

                # Close out iterator
                if hasattr(app_iter, "close"):
                    app_iter.close()

                # Start response (if it hasn't been done yet)
                if not response_started:
                    # Success!
                    start_response(
                        sub_app_start_response.status,
                        sub_app_start_response.response_headers,
                        sub_app_start_response.exc_info,
                    )

                return
            except DAVError as e:
                _logger.debug("re-raising {}".format(e))
                raise
            except Exception as e:
                # Caught a non-DAVError
                if self.catch_all_exceptions:
                    # Catch all exceptions to return as 500 Internal Error
                    # traceback.print_exc(10, environ.get("wsgi.errors") or sys.stderr)
                    _logger.error("{}".format(traceback.format_exc(10)))
                    raise as_DAVError(e)
                else:
                    _logger.error(
                        "Caught Exception\n{}".format(traceback.format_exc(10))
                    )
                    # traceback.print_exc(10, sys.stderr)
                    raise
        except DAVError as e:
            _logger.debug("caught {}".format(e))

            status = get_http_status_string(e)
            # Dump internal errors to console
            if e.value == HTTP_INTERNAL_ERROR:
                tb = traceback.format_exc(10)
                _logger.error(
                    "Caught HTTPRequestException(HTTP_INTERNAL_ERROR)\n{}".format(tb)
                )
                # traceback.print_exc(10, environ.get("wsgi.errors") or sys.stdout)
                _logger.error("e.src_exception:\n{}".format(e.src_exception))
            elif e.value in (HTTP_NOT_MODIFIED, HTTP_NO_CONTENT):
                # _logger.warning("Forcing empty error response for {}".format(e.value))
                # See paste.lint: these code don't have content
                start_response(
                    status, [("Content-Length", "0"), ("Date", util.get_rfc1123_time())]
                )
                yield b""
                return

            # If exception has pre-/post-condition: return as XML response,
            # else return as HTML
            content_type, body = e.get_response_page()

            # TODO: provide exc_info=sys.exc_info()?
            start_response(
                status,
                [
                    ("Content-Type", content_type),
                    ("Content-Length", str(len(body))),
                    ("Date", util.get_rfc1123_time()),
                ],
            )
            yield body
            return
