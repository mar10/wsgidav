# (c) 2009-2024 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Unit tests for the CORS middleware (wsgidav.mw.cors).

Uses webtest.TestApp to send fake requests through the WSGI stack.
"""

import unittest

import pytest

from tests.util import create_test_folder
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.wsgidav_app import WsgiDAVApp

try:
    import webtest
except ImportError:
    raise pytest.skip(
        "Skip tests that require WebTest", allow_module_level=True
    ) from None

ORIGIN = "https://example.org"


class CorsTest(unittest.TestCase):
    """Test the CORS middleware header placement."""

    def setUp(self):
        self.root_path = create_test_folder("wsgidav-cors-test")
        provider = FilesystemProvider(self.root_path)
        config = {
            "provider_mapping": {"/": provider},
            "http_authenticator": {"domain_controller": None},
            "simple_dc": {"user_mapping": {"*": True}},  # anonymous access
            # "verbose": 1,  # changing the log level may break subsequent logger tests
            "logging": {"enable_loggers": []},
            "property_manager": None,
            "lock_storage": True,
            "cors": {
                "allow_origin": "*",
                "allow_methods": "GET, HEAD, OPTIONS, PROPFIND",
                "allow_headers": "Authorization, Content-Type, Depth",
                "expose_headers": "WWW-Authenticate",
                "allow_credentials": True,
            },
        }
        self.app = webtest.TestApp(WsgiDAVApp(config))

    def tearDown(self):
        del self.app

    def test_expose_headers_on_actual_response(self):
        """`Access-Control-Expose-Headers` must be sent on the actual response.

        Per the Fetch standard it applies to a CORS request that is *not* a
        preflight request, so cross-origin script can read the listed header.
        """
        res = self.app.get("/", headers={"Origin": ORIGIN}, status=200)
        self.assertEqual(res.headers.get("Access-Control-Allow-Origin"), "*")
        self.assertEqual(
            res.headers.get("Access-Control-Expose-Headers"),
            "WWW-Authenticate",
            "Access-Control-Expose-Headers must be present on the actual response",
        )

    def test_expose_headers_not_on_preflight(self):
        """`Access-Control-Expose-Headers` is meaningless on the preflight.

        The preflight only carries Allow-Methods / Allow-Headers / Max-Age.
        """
        res = self.app.options(
            "/",
            headers={
                "Origin": ORIGIN,
                "Access-Control-Request-Method": "PROPFIND",
            },
            status="*",
        )
        # Sanity: this really is a handled preflight.
        self.assertIsNotNone(res.headers.get("Access-Control-Allow-Methods"))
        self.assertIsNone(
            res.headers.get("Access-Control-Expose-Headers"),
            "Access-Control-Expose-Headers must not be sent on the preflight",
        )
