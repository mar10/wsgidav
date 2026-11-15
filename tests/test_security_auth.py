"""
Security regression tests for HTTP Digest Authentication in WsgiDAV.

Tests cover:
  - CWE-338: Weak PRNG for nonce generation (fixed: secrets.token_hex)
  - CWE-208: Timing side-channel in digest comparison (fixed: hmac.compare_digest)
  - CWE-294: Digest `uri` not bound to the request target (RFC 7616, 3.4.6)
  - CWE-294: Digest nonce not validated (replay of a captured header)
  - Malformed Basic credentials must be answered with 401, not 500
"""

import re
import unittest
from unittest.mock import MagicMock, patch

from wsgidav.http_authenticator import HTTPAuthenticator


class MockDomainController:
    """Minimal domain controller stub for testing."""

    def get_domain_realm(self, path, environ):
        return "test_realm"

    def require_authentication(self, realm, environ):
        return True

    def supports_http_digest_auth(self):
        return True

    def basic_auth_user(self, realm, user_name, password, environ):
        return user_name == "user" and password == "pass"

    def digest_auth_user(self, realm, user_name, environ):
        if user_name == "user":
            # Return HA1 = MD5(user:realm:pass)
            from hashlib import md5

            return md5(f"{user_name}:{realm}:pass".encode()).hexdigest()
        return False


def make_auth(config=None):
    app = MagicMock(return_value=[b"OK"])
    cfg = config or {}
    cfg.setdefault(
        "http_authenticator",
        {
            "accept_basic": True,
            "accept_digest": True,
            "default_to_digest": False,
        },
    )
    dc = MockDomainController()
    # Patch make_domain_controller to return our stub directly
    with patch("wsgidav.http_authenticator.make_domain_controller", return_value=dc):
        auth = HTTPAuthenticator(app, dc, cfg)
    return auth


class TestNonceStrength(unittest.TestCase):
    """CWE-338: Verify nonce is generated with a CSPRNG."""

    def _capture_nonce(self, auth):
        """Helper: call send_digest_auth_response and capture the WWW-Authenticate nonce."""
        environ = {
            "PATH_INFO": "/",
            "REQUEST_METHOD": "GET",
            "SERVER_NAME": "localhost",
            "SERVER_PORT": "80",
            "wsgi.input": b"",
            "wsgidav.config": {"verbose": 0},
            "wsgidav.verbose": 0,
        }
        captured = {}

        def start_response(status, headers):
            for name, value in headers:
                if name == "WWW-Authenticate":
                    captured["www_auth"] = value

        auth.send_digest_auth_response(environ, start_response)
        www_auth = captured.get("www_auth", "")
        m = re.search(r'nonce="([^"]+)"', www_auth)
        return m.group(1) if m else None

    def test_nonces_are_unique(self):
        """Each call must produce a unique nonce (CSPRNG)."""
        auth = make_auth()
        nonces = {self._capture_nonce(auth) for _ in range(50)}
        self.assertEqual(
            len(nonces), 50, "CSPRNG nonces must be unique across 50 calls"
        )

    def test_nonce_has_adequate_entropy(self):
        """Nonces must be non-empty and at least 16 base64 chars long."""
        auth = make_auth()
        nonce = self._capture_nonce(auth)
        self.assertIsNotNone(nonce)
        # base64 of (timekey + hexdigest) is well over 16 chars
        self.assertGreater(len(nonce), 16)


class TestTimingSafeDigestComparison(unittest.TestCase):
    """CWE-208: Verify digest comparison uses hmac.compare_digest."""

    def test_hmac_compare_digest_is_used(self):
        """Source code must reference hmac.compare_digest (not bare ==)."""
        import inspect

        from wsgidav import http_authenticator as mod

        src = inspect.getsource(mod.HTTPAuthenticator.handle_digest_auth_request)
        self.assertIn(
            "hmac.compare_digest",
            src,
            "Digest comparison must use hmac.compare_digest for constant-time safety",
        )
        # Ensure the old bare != comparison is gone from the digest comparison path
        # (it may still appear in unrelated parts, so we check the specific pattern)
        self.assertNotIn(
            "required_digest != req_response",
            src,
            "Non-constant-time bare != comparison must not be used for digest values",
        )

    def test_random_not_imported(self):
        """The `random` module must not be imported (only secrets for CSPRNG)."""
        import wsgidav.http_authenticator as mod

        # Check module-level names — random should not be present
        self.assertFalse(
            hasattr(mod, "random"),
            "Module `random` must not be imported; use `secrets` instead",
        )

    def test_secrets_is_imported(self):
        """The `secrets` module must be imported."""
        import wsgidav.http_authenticator as mod

        self.assertTrue(
            hasattr(mod, "secrets"),
            "Module `secrets` must be imported for CSPRNG nonce generation",
        )

    def test_hmac_is_imported(self):
        """The `hmac` module must be imported."""
        import wsgidav.http_authenticator as mod

        self.assertTrue(
            hasattr(mod, "hmac"),
            "Module `hmac` must be imported for constant-time comparison",
        )

    def test_rejected_root_digest_returns_401(self):
        """A rejected Windows XP root-realm fallback must not raise TypeError."""
        auth = make_auth(
            {
                "hotfixes": {"winxp_accept_root_share_login": True},
                "http_authenticator": {
                    "accept_basic": True,
                    "accept_digest": True,
                    "default_to_digest": False,
                },
            }
        )
        auth._compute_digest_response = MagicMock(
            side_effect=["expected-digest", False]
        )
        environ = {
            "PATH_INFO": "/share",
            "REQUEST_METHOD": "GET",
            "SERVER_NAME": "localhost",
            "SERVER_PORT": "80",
            "HTTP_AUTHORIZATION": (
                'Digest username="user", realm="test_realm", nonce="nonce", '
                'uri="/share", response="wrong-digest",'
            ),
        }
        response = {}

        def start_response(status, headers):
            response["status"] = status

        auth.handle_digest_auth_request(environ, start_response)

        self.assertEqual(auth._compute_digest_response.call_count, 2)
        self.assertEqual(response["status"], "401 Not Authorized")


def digest_header(
    user, realm, password, method, uri, nonce="nonce", cnonce="cnonce", nc="00000001"
):
    """Build the Authorization header a conforming client would send."""
    from hashlib import md5

    h = lambda s: md5(s.encode()).hexdigest()  # noqa: E731
    a1 = h(f"{user}:{realm}:{password}")
    a2 = h(f"{method}:{uri}")
    response = h(f"{a1}:{nonce}:{nc}:{cnonce}:auth:{a2}")
    return (
        f'Digest username="{user}", realm="{realm}", nonce="{nonce}", '
        f'uri="{uri}", cnonce="{cnonce}", nc={nc}, qop=auth, '
        f'response="{response}", algorithm=MD5'
    )


class TestDigestUriBinding(unittest.TestCase):
    """CWE-294: the header's `uri` must designate the requested resource.

    RFC 7616, section 3.4.6. Without this, an `Authorization: Digest ...`
    header captured for one resource authenticates requests for any other
    resource in the same realm, using the captured method.
    """

    def _environ(self, method="GET", script_name="", path_info="/secret.txt", **kw):
        environ = {
            "REQUEST_METHOD": method,
            "SCRIPT_NAME": script_name,
            "PATH_INFO": path_info,
            "QUERY_STRING": "",
            "SERVER_NAME": "localhost",
            "SERVER_PORT": "80",
            "wsgidav.config": {"verbose": 0},
            "wsgidav.verbose": 0,
        }
        environ.update(kw)
        return environ

    # -- unit level -------------------------------------------------------

    def test_matching_uri_is_accepted(self):
        auth = make_auth()
        self.assertTrue(auth._is_digest_uri_valid("/secret.txt", self._environ()))

    def test_other_resource_is_rejected(self):
        auth = make_auth()
        self.assertFalse(
            auth._is_digest_uri_valid(
                "/secret.txt", self._environ(path_info="/other.txt")
            )
        )

    def test_missing_uri_is_rejected(self):
        auth = make_auth()
        self.assertFalse(auth._is_digest_uri_valid(None, self._environ()))
        self.assertFalse(auth._is_digest_uri_valid("", self._environ()))

    def test_percent_encoded_uri_is_accepted(self):
        auth = make_auth()
        self.assertTrue(
            auth._is_digest_uri_valid(
                "/sub/deep%20file.txt", self._environ(path_info="/sub/deep file.txt")
            )
        )

    def test_absolute_uri_form_is_accepted(self):
        auth = make_auth()
        self.assertTrue(
            auth._is_digest_uri_valid("http://localhost/secret.txt", self._environ())
        )

    def test_uri_below_a_mounted_share_is_accepted(self):
        auth = make_auth()
        self.assertTrue(
            auth._is_digest_uri_valid(
                "/dav/files/f.txt",
                self._environ(script_name="/dav/files", path_info="/f.txt"),
            )
        )

    def test_sibling_below_a_mounted_share_is_rejected(self):
        auth = make_auth()
        self.assertFalse(
            auth._is_digest_uri_valid(
                "/dav/files/f.txt",
                self._environ(script_name="/dav/files", path_info="/g.txt"),
            )
        )

    def test_trailing_slash_is_significant(self):
        auth = make_auth()
        self.assertTrue(
            auth._is_digest_uri_valid("/sub/", self._environ(path_info="/sub/"))
        )

    def test_query_string_must_match(self):
        auth = make_auth()
        self.assertTrue(
            auth._is_digest_uri_valid(
                "/secret.txt?a=1", self._environ(QUERY_STRING="a=1")
            )
        )
        self.assertFalse(
            auth._is_digest_uri_valid(
                "/secret.txt?a=1", self._environ(QUERY_STRING="a=2")
            )
        )

    def test_dot_segments_escaping_the_root_are_rejected(self):
        auth = make_auth()
        self.assertFalse(
            auth._is_digest_uri_valid("/../../etc/passwd", self._environ())
        )

    def test_options_asterisk_form_is_accepted(self):
        """'OPTIONS *' does not address a resource; clients send '*' or '/'."""
        auth = make_auth()
        for uri in ("*", "/"):
            environ = self._environ(method="OPTIONS", path_info="/*", REQUEST_URI="*")
            self.assertTrue(auth._is_digest_uri_valid(uri, environ), f"uri={uri!r}")

    def test_asterisk_uri_does_not_bypass_a_normal_request(self):
        auth = make_auth()
        self.assertFalse(auth._is_digest_uri_valid("*", self._environ()))

    def test_hotfix_restores_previous_behavior(self):
        auth = make_auth(
            {
                "hotfixes": {"digest_skip_uri_check": True},
                "http_authenticator": {
                    "accept_basic": True,
                    "accept_digest": True,
                    "default_to_digest": False,
                },
            }
        )
        self.assertTrue(
            auth._is_digest_uri_valid(
                "/secret.txt", self._environ(path_info="/other.txt")
            )
        )

    # -- request level ----------------------------------------------------

    def _run(self, header, environ):
        environ["HTTP_AUTHORIZATION"] = header
        captured = {}

        def start_response(status, headers):
            captured["status"] = status

        body = self.auth.handle_digest_auth_request(environ, start_response)
        return captured.get("status"), body

    def setUp(self):
        self.auth = make_auth()
        # `make_auth()` passes the domain controller as `next_app`; replace it
        # so that an accepted request can be distinguished from a rejected one.
        self.next_app = MagicMock(return_value=[b"OK"])
        self.auth.next_app = self.next_app
        self.nonce = self.auth._make_nonce()

    def test_captured_header_does_not_authenticate_another_resource(self):
        header = digest_header(
            "user", "test_realm", "pass", "GET", "/secret.txt", nonce=self.nonce
        )
        # Same resource: accepted
        status, _ = self._run(header, self._environ(path_info="/secret.txt"))
        self.assertIsNone(status, "the legitimate request must reach next_app")
        self.assertEqual(self.next_app.call_count, 1)
        # Different resource, header unchanged: rejected
        status, _ = self._run(header, self._environ(path_info="/other.txt"))
        self.assertEqual(status, "401 Not Authorized")
        self.assertEqual(self.next_app.call_count, 1, "no further call to next_app")

    def test_captured_put_header_cannot_overwrite_another_resource(self):
        header = digest_header(
            "user", "test_realm", "pass", "PUT", "/put_canary.txt", nonce=self.nonce
        )
        status, _ = self._run(
            header, self._environ(method="PUT", path_info="/put_canary.txt")
        )
        self.assertIsNone(status)
        self.assertEqual(self.next_app.call_count, 1)
        status, _ = self._run(
            header, self._environ(method="PUT", path_info="/other.txt")
        )
        self.assertEqual(status, "401 Not Authorized")
        self.assertEqual(self.next_app.call_count, 1, "no further call to next_app")


class TestDigestNonceValidation(unittest.TestCase):
    """CWE-294: only fresh nonces that were issued by this server are accepted.

    Otherwise a captured `Authorization: Digest ...` header could be replayed
    forever for the same method and resource.
    """

    def setUp(self):
        self.auth = make_auth()
        self.next_app = MagicMock(return_value=[b"OK"])
        self.auth.next_app = self.next_app

    def _run(self, nonce, *, auth=None, password="pass"):
        environ = {
            "REQUEST_METHOD": "DELETE",
            "SCRIPT_NAME": "",
            "PATH_INFO": "/secret.txt",
            "QUERY_STRING": "",
            "HTTP_AUTHORIZATION": digest_header(
                "user", "test_realm", password, "DELETE", "/secret.txt", nonce=nonce
            ),
        }
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["www_auth"] = dict(headers).get("WWW-Authenticate")

        (auth or self.auth).handle_digest_auth_request(environ, start_response)
        return captured.get("status"), captured.get("www_auth")

    def test_server_nonce_is_accepted(self):
        status, _ = self._run(self.auth._make_nonce())
        self.assertIsNone(status, "the request must reach next_app")
        self.assertEqual(self.next_app.call_count, 1)

    def test_forged_nonce_is_rejected(self):
        for nonce in ("nonce", "", "1:2:3", "a:b", f"{2**40}:00:00"):
            status, www_auth = self._run(nonce)
            self.assertEqual(status, "401 Not Authorized", nonce)
            self.assertIn("stale=true", www_auth)
        self.assertEqual(self.next_app.call_count, 0)

    def test_tampered_timestamp_is_rejected(self):
        timestamp, salt, signature = self.auth._make_nonce().split(":")
        status, _ = self._run(f"{int(timestamp) + 1000}:{salt}:{signature}")
        self.assertEqual(status, "401 Not Authorized")
        self.assertEqual(self.next_app.call_count, 0)

    def test_expired_nonce_is_rejected_as_stale(self):
        nonce = self.auth._make_nonce()
        lifetime = self.auth.digest_nonce_lifetime
        with patch("wsgidav.http_authenticator.time.time") as now:
            now.return_value = int(nonce.split(":")[0]) + lifetime - 1
            status, _ = self._run(nonce)
            self.assertIsNone(status, "still valid")
            now.return_value += 10
            status, www_auth = self._run(nonce)
        self.assertEqual(status, "401 Not Authorized")
        self.assertIn("stale=true", www_auth)
        self.assertEqual(self.next_app.call_count, 1)

    def test_wrong_password_is_not_reported_as_stale(self):
        status, www_auth = self._run("nonce", password="wrong")
        self.assertEqual(status, "401 Not Authorized")
        self.assertNotIn("stale", www_auth)

    def test_nonce_of_another_server_is_rejected(self):
        status, _ = self._run(make_auth()._make_nonce())
        self.assertEqual(status, "401 Not Authorized")

    def test_shared_secret_accepts_nonce_of_another_process(self):
        def conf():
            return {
                "http_authenticator": {
                    "accept_basic": True,
                    "accept_digest": True,
                    "default_to_digest": False,
                    "digest_nonce_secret": "s3cret",
                }
            }

        auth = make_auth(conf())
        auth.next_app = self.next_app
        status, _ = self._run(make_auth(conf())._make_nonce(), auth=auth)
        self.assertIsNone(status)
        self.assertEqual(self.next_app.call_count, 1)


class TestMalformedBasicHeader(unittest.TestCase):
    """Malformed credentials must be answered with 401 (not raise -> 500)."""

    def _run(self, header, query_string=""):
        auth = make_auth()
        auth.next_app = MagicMock(return_value=[b"OK"])
        environ = {
            "REQUEST_METHOD": "GET",
            "SCRIPT_NAME": "",
            "PATH_INFO": "/",
            "QUERY_STRING": query_string,
            "HTTP_AUTHORIZATION": header,
        }
        captured = {}

        def start_response(status, headers):
            captured["status"] = status

        auth(environ, start_response)
        return captured.get("status"), auth.next_app.call_count

    def test_valid_credentials_are_accepted(self):
        self.assertEqual(self._run("Basic dXNlcjpwYXNz"), (None, 1))  # user:pass

    def test_malformed_credentials_return_401(self):
        for header in (
            "Basic",
            "Basic !!!not-base64!!!",
            "Basic dXNlcg==",  # 'user' (no colon)
            "Basic /w==",  # b'\xff' (not UTF-8)
        ):
            self.assertEqual(self._run(header), ("401 Not Authorized", 0), header)

    def test_logout_is_a_query_parameter(self):
        """Only `?logout` forces a new login, not any query containing the word."""
        header = "Basic dXNlcjpwYXNz"
        self.assertEqual(self._run(header, "logout"), ("401 Not Authorized", 0))
        self.assertEqual(self._run(header, "name=logout.txt"), (None, 1))


class TestPamAllowUsers(unittest.TestCase):
    """`allow_users: current` must not be evaluated as a substring test."""

    def _make_dc(self, allow_users, deny_users=None):
        import importlib
        import sys

        # python-pam is an optional dependency: stub it
        with patch.dict(sys.modules, {"pam": MagicMock()}):
            sys.modules.pop("wsgidav.dc.pam_dc", None)
            pam_dc = importlib.import_module("wsgidav.dc.pam_dc")
        self.addCleanup(sys.modules.pop, "wsgidav.dc.pam_dc", None)
        config = {"pam_dc": {"allow_users": allow_users}}
        if deny_users is not None:
            config["pam_dc"]["deny_users"] = deny_users
        return pam_dc.PAMDomainController(None, config)

    def test_current(self):
        dc = self._make_dc("current")
        with patch("os.getlogin", return_value="joe"):
            self.assertTrue(dc._validate_user("joe"))
            for name in ("", "c", "rent", "current", "jo"):
                self.assertFalse(dc._validate_user(name), name)

    def test_all(self):
        dc = self._make_dc("all", deny_users=["root"])
        self.assertTrue(dc._validate_user("joe"))
        self.assertFalse(dc._validate_user("root"))

    def test_list(self):
        dc = self._make_dc(["joe", "current"])
        self.assertTrue(dc._validate_user("joe"))
        self.assertFalse(dc._validate_user("jo"))
        self.assertFalse(dc._validate_user("rent"))


class TestSimpleDcBasicAuth(unittest.TestCase):
    def test_basic_auth_user(self):
        from wsgidav.dc.simple_dc import SimpleDomainController

        config = {
            "simple_dc": {
                "user_mapping": {
                    "/": {"joe": {"password": "s\u00e4cret", "roles": ["editor"]}},
                    "/nopw": {"joe": {"roles": []}},
                }
            }
        }
        dc = SimpleDomainController(None, config)
        environ = {}
        self.assertTrue(dc.basic_auth_user("/", "joe", "s\u00e4cret", environ))
        self.assertEqual(environ["wsgidav.auth.roles"], ["editor"])
        environ = {}
        self.assertFalse(dc.basic_auth_user("/", "joe", "secret", environ))
        self.assertFalse(dc.basic_auth_user("/", "jane", "s\u00e4cret", environ))
        self.assertFalse(dc.basic_auth_user("/nopw", "joe", "", environ))
        self.assertEqual(environ, {})


if __name__ == "__main__":
    unittest.main()
