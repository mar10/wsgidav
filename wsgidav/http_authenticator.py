# -*- coding: utf-8 -*-
# (c) 2009-2020 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
WSGI middleware for HTTP basic and digest authentication.

Usage::

   from http_authenticator import HTTPAuthenticator

   WSGIApp = HTTPAuthenticator(ProtectedWSGIApp, domain_controller, accept_basic,
                               accept_digest, default_to_digest)

   where:
     ProtectedWSGIApp is the application requiring authenticated access

     domain_controller is a domain controller object meeting specific
     requirements (below)

     accept_basic is a boolean indicating whether to accept requests using
     the basic authentication scheme (default = True)

     accept_digest is a boolean indicating whether to accept requests using
     the digest authentication scheme (default = True)

     default_to_digest is a boolean. if True, an unauthenticated request will
     be sent a digest authentication required response, else the unauthenticated
     request will be sent a basic authentication required response
     (default = True)

The HTTPAuthenticator will put the following authenticated information in the
environ dictionary::

   environ["wsgidav.auth.realm"] = realm name
   environ["wsgidav.auth.user_name"] = user_name
   environ["wsgidav.auth.roles"] = <tuple> (optional)
   environ["wsgidav.auth.permissions"] = <tuple> (optional)


**Domain Controllers**

The HTTP basic and digest authentication schemes are based on the following
concept:

Each requested relative URI can be resolved to a realm for authentication,
for example:
/fac_eng/courses/ee5903/timetable.pdf -> might resolve to realm 'Engineering General'
/fac_eng/examsolns/ee5903/thisyearssolns.pdf -> might resolve to realm 'Engineering Lecturers'
/med_sci/courses/m500/surgery.htm -> might resolve to realm 'Medical Sciences General'
and each realm would have a set of user_name and password pairs that would
allow access to the resource.

A domain controller provides this information to the HTTPAuthenticator.
This allows developers to write their own domain controllers, that might,
for example, interface with their own user database.

for simple applications, a SimpleDomainController is provided that will take
in a single realm name (for display) and a single dictionary of user_name (key)
and password (value) string pairs

Usage::

   from wsgidav.dc.simple_dc import SimpleDomainController
   users = dict(({'John Smith': 'YouNeverGuessMe', 'Dan Brown': 'DontGuessMeEither'})
   realm = 'Sample Realm'
   domain_controller = SimpleDomainController(users, realm)


Domain Controllers must provide the methods as described in
``wsgidav.interfaces.domaincontrollerinterface`` (interface_)

.. _interface : interfaces/domaincontrollerinterface.py

The environ variable here is the WSGI 'environ' dictionary. It is passed to
all methods of the domain controller as a means for developers to pass information
from previous middleware or server config (if required).
"""
from hashlib import md5
from textwrap import dedent
from wsgidav import compat, util
from wsgidav.dc.simple_dc import SimpleDomainController
from wsgidav.middleware import BaseMiddleware
from wsgidav.util import calc_base64, calc_hexdigest, dynamic_import_class

import inspect
import random
import re
import time


__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)


def make_domain_controller(wsgidav_app, config):
    dc = config.get("http_authenticator", {}).get("domain_controller")
    org_dc = dc
    if dc is True or not dc:
        # True or null:
        dc = SimpleDomainController
    elif compat.is_basestring(dc):
        # If a plain string is passed, try to import it as class
        dc = dynamic_import_class(dc)

    if inspect.isclass(dc):
        # If a class is passed, instantiate that
        dc = dc(wsgidav_app, config)
    else:
        raise RuntimeError(
            "Could not resolve domain controller class (got {})".format(org_dc)
        )
    # print("make_domain_controller", dc)
    return dc


# ========================================================================
# HTTPAuthenticator
# ========================================================================
class HTTPAuthenticator(BaseMiddleware):
    """WSGI Middleware for basic and digest authentication."""

    error_message_401 = dedent(
        """\
        <html>
            <head><title>401 Access not authorized</title></head>
            <body>
                <h1>401 Access not authorized</h1>
            </body>
        </html>
    """
    )

    def __init__(self, wsgidav_app, next_app, config):
        super(HTTPAuthenticator, self).__init__(wsgidav_app, next_app, config)
        self._verbose = config.get("verbose", 3)
        self.config = config

        dc = make_domain_controller(wsgidav_app, config)
        self.domain_controller = dc

        hotfixes = config.get("hotfixes", {})
        # HOT FIX for Windows XP (Microsoft-WebDAV-MiniRedir/5.1.2600):
        # When accessing a share '/dav/', XP sometimes sends digests for '/'.
        # With this fix turned on, we allow '/' digests, when a matching '/dav' account
        # is present.
        self.winxp_accept_root_share_login = hotfixes.get(
            "winxp_accept_root_share_login", False
        )

        # HOTFIX for Windows
        # MW 2013-12-31: DON'T set this (will MS office to use anonymous always in
        # some scenarios)
        self.win_accept_anonymous_options = hotfixes.get(
            "win_accept_anonymous_options", False
        )

        auth_conf = config.get("http_authenticator", {})

        self.accept_basic = auth_conf.get("accept_basic", True)
        self.accept_digest = auth_conf.get("accept_digest", True)
        self.default_to_digest = auth_conf.get("default_to_digest", True)
        self.trusted_auth_header = auth_conf.get("trusted_auth_header", None)

        if not dc.supports_http_digest_auth() and (
            self.accept_digest or self.default_to_digest or not self.accept_basic
        ):
            raise RuntimeError(
                "{} does not support digest authentication.\n"
                "Set accept_basic=True, accept_digest=False, default_to_digest=False".format(
                    dc.__class__.__name__
                )
            )

        self._nonce_dict = dict([])

        self._header_parser = re.compile(r"([\w]+)=([^,]*),")
        # Note: extra parser to handle digest auth requests from certain
        # clients, that leave commas un-encoded to interfere with the above.
        self._header_fix_parser = re.compile(r'([\w]+)=("[^"]*,[^"]*"),')
        self._header_method = re.compile(r"^([\w]+)")

    def get_domain_controller(self):
        return self.domain_controller

    def allow_anonymous_access(self, share):
        return not self.domain_controller.require_authentication(share, None)

    def __call__(self, environ, start_response):
        realm = self.domain_controller.get_domain_realm(environ["PATH_INFO"], environ)

        environ["wsgidav.auth.realm"] = realm
        environ["wsgidav.auth.user_name"] = ""
        # The domain controller MAY set those values depending on user's
        # authorization:
        environ["wsgidav.auth.roles"] = None
        environ["wsgidav.auth.permissions"] = None

        # _logger.debug(
        #     "HTTPAuthenticator realm({}): '{}'".format(environ["PATH_INFO"], realm)
        # )
        # _logger.debug("{}".format(environ))

        force_logout = False
        if "logout" in environ.get("QUERY_STRING", ""):
            force_logout = True
            _logger.warning("Force logout")

        force_allow = False
        if self.win_accept_anonymous_options and environ["REQUEST_METHOD"] == "OPTIONS":
            _logger.warning("No authorization required for OPTIONS method")
            force_allow = True

        if force_allow or not self.domain_controller.require_authentication(
            realm, environ
        ):
            # No authentication needed
            # _logger.debug("No authorization required for realm '{}'".format(realm))
            # environ["wsgidav.auth.realm"] = realm
            # environ["wsgidav.auth.user_name"] = ""
            return self.next_app(environ, start_response)

        if self.trusted_auth_header and environ.get(self.trusted_auth_header):
            # accept a user_name that was injected by a trusted upstream server
            _logger.debug(
                "Accept trusted user_name {}='{}'for realm '{}'".format(
                    self.trusted_auth_header,
                    environ.get(self.trusted_auth_header),
                    realm,
                )
            )
            # environ["wsgidav.auth.realm"] = realm
            environ["wsgidav.auth.user_name"] = environ.get(self.trusted_auth_header)
            return self.next_app(environ, start_response)

        if "HTTP_AUTHORIZATION" in environ and not force_logout:
            auth_header = environ["HTTP_AUTHORIZATION"]
            auth_match = self._header_method.search(auth_header)
            auth_method = "None"
            if auth_match:
                auth_method = auth_match.group(1).lower()

            if auth_method == "digest" and self.accept_digest:
                return self.handle_digest_auth_request(environ, start_response)
            elif auth_method == "digest" and self.accept_basic:
                return self.send_basic_auth_response(environ, start_response)
            elif auth_method == "basic" and self.accept_basic:
                return self.handle_basic_auth_request(environ, start_response)

            # The requested auth method is not supported.
            elif self.default_to_digest and self.accept_digest:
                return self.send_digest_auth_response(environ, start_response)
            elif self.accept_basic:
                return self.send_basic_auth_response(environ, start_response)

            _logger.warning(
                "HTTPAuthenticator: respond with 400 Bad request; Auth-Method: {}".format(
                    auth_method
                )
            )

            start_response(
                "400 Bad Request",
                [("Content-Length", "0"), ("Date", util.get_rfc1123_time())],
            )
            return [""]

        if self.default_to_digest:
            return self.send_digest_auth_response(environ, start_response)
        return self.send_basic_auth_response(environ, start_response)

    def send_basic_auth_response(self, environ, start_response):
        realm = self.domain_controller.get_domain_realm(environ["PATH_INFO"], environ)
        _logger.debug("401 Not Authorized for realm '{}' (basic)".format(realm))
        wwwauthheaders = 'Basic realm="' + realm + '"'

        body = compat.to_bytes(self.error_message_401)
        start_response(
            "401 Not Authorized",
            [
                ("WWW-Authenticate", wwwauthheaders),
                ("Content-Type", "text/html"),
                ("Content-Length", str(len(body))),
                ("Date", util.get_rfc1123_time()),
            ],
        )
        return [body]

    def handle_basic_auth_request(self, environ, start_response):
        realm = self.domain_controller.get_domain_realm(environ["PATH_INFO"], environ)
        auth_header = environ["HTTP_AUTHORIZATION"]
        auth_value = ""
        try:
            auth_value = auth_header[len("Basic ") :].strip()
        except Exception:
            auth_value = ""

        auth_value = compat.base64_decodebytes(compat.to_bytes(auth_value))
        auth_value = compat.to_native(auth_value)
        user_name, password = auth_value.split(":", 1)

        if self.domain_controller.basic_auth_user(realm, user_name, password, environ):
            environ["wsgidav.auth.realm"] = realm
            environ["wsgidav.auth.user_name"] = user_name
            return self.next_app(environ, start_response)

        _logger.warning(
            "Authentication (basic) failed for user '{}', realm '{}'.".format(
                user_name, realm
            )
        )
        return self.send_basic_auth_response(environ, start_response)

    def send_digest_auth_response(self, environ, start_response):
        realm = self.domain_controller.get_domain_realm(environ["PATH_INFO"], environ)
        random.seed()
        serverkey = hex(random.getrandbits(32))[2:]
        etagkey = calc_hexdigest(environ["PATH_INFO"])
        timekey = str(time.time())
        nonce_source = timekey + calc_hexdigest(
            timekey + ":" + etagkey + ":" + serverkey
        )
        nonce = calc_base64(nonce_source)
        wwwauthheaders = (
            'Digest realm="{}", nonce="{}", algorithm=MD5, qop="auth"'.format(
                realm, nonce
            )
        )

        _logger.debug(
            "401 Not Authorized for realm '{}' (digest): {}".format(
                realm, wwwauthheaders
            )
        )

        body = compat.to_bytes(self.error_message_401)
        start_response(
            "401 Not Authorized",
            [
                ("WWW-Authenticate", wwwauthheaders),
                ("Content-Type", "text/html"),
                ("Content-Length", str(len(body))),
                ("Date", util.get_rfc1123_time()),
            ],
        )
        return [body]

    def handle_digest_auth_request(self, environ, start_response):

        realm = self.domain_controller.get_domain_realm(environ["PATH_INFO"], environ)

        is_invalid_req = False
        invalid_req_reasons = []

        auth_header_dict = {}
        auth_headers = environ["HTTP_AUTHORIZATION"] + ","
        if not auth_headers.lower().strip().startswith("digest"):
            is_invalid_req = True
            invalid_req_reasons.append(
                "HTTP_AUTHORIZATION must start with 'digest': {}".format(auth_headers)
            )
        # Hotfix for Windows file manager and OSX Finder:
        # Some clients don't urlencode paths in auth header, so uri value may
        # contain commas, which break the usual regex headerparser. Example:
        # Digest user_name="user",realm="/",uri="a,b.txt",nc=00000001, ...
        # -> [..., ('uri', '"a'), ('nc', '00000001'), ...]
        # Override any such values with carefully extracted ones.
        auth_header_list = self._header_parser.findall(auth_headers)
        auth_header_fixlist = self._header_fix_parser.findall(auth_headers)
        if auth_header_fixlist:
            _logger.info(
                "Fixing auth_header comma-parsing: extend {} with {}".format(
                    auth_header_list, auth_header_fixlist
                )
            )
            auth_header_list += auth_header_fixlist

        for auth_header in auth_header_list:
            auth_header_key = auth_header[0]
            auth_header_value = auth_header[1].strip().strip('"')
            auth_header_dict[auth_header_key] = auth_header_value

        # _logger.debug(
        #     "handle_digest_auth_request: {}".format(environ["HTTP_AUTHORIZATION"])
        # )
        # _logger.debug("  -> {}".format(auth_header_dict))

        req_username = None
        if "username" in auth_header_dict:
            req_username = auth_header_dict["username"]
            if not req_username:
                is_invalid_req = True
                invalid_req_reasons.append(
                    "`username` is empty: {!r}".format(req_username)
                )
            elif r"\\" in req_username:
                # Hotfix for Windows XP:
                #   net use W: http://127.0.0.1/dav /USER:DOMAIN\tester tester
                # will send the name with double backslashes ('DOMAIN\\tester')
                # but send the digest for the simple name ('DOMAIN\tester').
                req_username_org = req_username
                req_username = req_username.replace("\\\\", "\\")
                _logger.info(
                    "Fixing Windows name with double backslash: '{}' --> '{}'".format(
                        req_username_org, req_username
                    )
                )

            # pre_check = self.domain_controller.is_realm_user(
            #     realm, req_username, environ
            # )
            # if pre_check is False:
            #     is_invalid_req = True
            #     invalid_req_reasons.append(
            #         "Not a realm-user: '{}'/'{}'".format(realm, req_username)
            #     )
        else:
            is_invalid_req = True
            invalid_req_reasons.append("Missing 'username' in headers")

        # TODO: Chun added this comments, but code was commented out:
        # Do not do realm checking - a hotfix for WinXP using some other realm's
        # auth details for this realm - if user/password match
        if "realm" in auth_header_dict:
            if auth_header_dict["realm"].upper() != realm.upper():
                if (
                    self.winxp_accept_root_share_login
                    and auth_header_dict["realm"] == "/"
                ):
                    # Hotfix: also accept '/'
                    _logger.info("winxp_accept_root_share_login")
                else:
                    is_invalid_req = True
                    invalid_req_reasons.append("Realm mismatch: '{}'".format(realm))

        if "algorithm" in auth_header_dict:
            if auth_header_dict["algorithm"].upper() != "MD5":
                is_invalid_req = True  # only MD5 supported
                invalid_req_reasons.append("Unsupported 'algorithm' in headers")

        req_uri = auth_header_dict.get("uri")

        if "nonce" in auth_header_dict:
            req_nonce = auth_header_dict["nonce"]
        else:
            is_invalid_req = True
            invalid_req_reasons.append("Expected 'nonce' in headers")

        req_has_qop = False
        if "qop" in auth_header_dict:
            req_has_qop = True
            req_qop = auth_header_dict["qop"]
            if req_qop.lower() != "auth":
                is_invalid_req = True  # only auth supported, auth-int not supported
                invalid_req_reasons.append("Expected 'qop' == 'auth'")
        else:
            req_qop = None

        if "cnonce" in auth_header_dict:
            req_cnonce = auth_header_dict["cnonce"]
        else:
            req_cnonce = None
            if req_has_qop:
                is_invalid_req = True
                invalid_req_reasons.append(
                    "Expected 'cnonce' in headers if qop is passed"
                )

        if "nc" in auth_header_dict:  # is read but nonce-count checking not implemented
            req_nc = auth_header_dict["nc"]
        else:
            req_nc = None
            if req_has_qop:
                is_invalid_req = True
                invalid_req_reasons.append("Expected 'nc' in headers if qop is passed")

        if "response" in auth_header_dict:
            req_response = auth_header_dict["response"]
        else:
            is_invalid_req = True
            invalid_req_reasons.append("Expected 'response' in headers")

        if not is_invalid_req:
            req_method = environ["REQUEST_METHOD"]

            required_digest = self.compute_digest_response(
                realm,
                req_username,
                req_method,
                req_uri,
                req_nonce,
                req_cnonce,
                req_qop,
                req_nc,
                environ,
            )

            if not required_digest:
                # Rejected by domain controller
                is_invalid_req = True
                invalid_req_reasons.append(
                    "Rejected by DC.digest_auth_user('{}', '{}')".format(
                        realm, req_username
                    )
                )
            elif required_digest != req_response:
                warning_msg = (
                    "compute_digest_response('{}', '{}', ...): {} != {}".format(
                        realm, req_username, required_digest, req_response
                    )
                )
                if self.winxp_accept_root_share_login and realm != "/":
                    # _logger.warning(warning_msg + " => trying '/' realm")
                    # Hotfix: also accept '/' digest
                    root_digest = self.compute_digest_response(
                        "/",
                        req_username,
                        req_method,
                        req_uri,
                        req_nonce,
                        req_cnonce,
                        req_qop,
                        req_nc,
                        environ,
                    )
                    if root_digest == req_response:
                        _logger.warning(
                            "handle_digest_auth_request: HOTFIX: accepting '/' login for '{}'.".format(
                                realm
                            )
                        )
                    else:
                        is_invalid_req = True
                        invalid_req_reasons.append(
                            warning_msg + " (also tried '/' realm)"
                        )
                else:
                    is_invalid_req = True
                    invalid_req_reasons.append(warning_msg)
            else:
                # _logger.debug("digest succeeded for realm '{}', user '{}'"
                #               .format(realm, req_username))
                pass

        if is_invalid_req:
            invalid_req_reasons.append("Headers:\n    {}".format(auth_header_dict))
            if self._verbose >= 4:
                _logger.warning(
                    "Authentication (digest) failed for user '{}', realm '{}':\n  {}".format(
                        req_username, realm, "\n  ".join(invalid_req_reasons)
                    )
                )
            else:
                _logger.warning(
                    "Authentication (digest) failed for user '{}', realm '{}'.".format(
                        req_username, realm
                    )
                )
            return self.send_digest_auth_response(environ, start_response)

        environ["wsgidav.auth.realm"] = realm
        environ["wsgidav.auth.user_name"] = req_username
        return self.next_app(environ, start_response)

    def compute_digest_response(
        self, realm, user_name, method, uri, nonce, cnonce, qop, nc, environ
    ):
        """Computes digest hash.

        Calculation of the A1 (HA1) part is delegated to the dc interface method
        `digest_auth_user()`.

        Args:
            realm (str):
            user_name (str):
            method (str): WebDAV Request Method
            uri (str):
            nonce (str): server generated nonce value
            cnonce (str): client generated cnonce value
            qop (str): quality of protection
            nc (str) (number), nonce counter incremented by client
        Returns:
            MD5 hash string
            or False if user rejected by domain controller
        """

        def md5h(data):
            return md5(compat.to_bytes(data)).hexdigest()

        def md5kd(secret, data):
            return md5h(secret + ":" + data)

        A1 = self.domain_controller.digest_auth_user(realm, user_name, environ)
        if not A1:
            return False

        A2 = method + ":" + uri

        if qop:
            res = md5kd(
                A1, nonce + ":" + nc + ":" + cnonce + ":" + qop + ":" + md5h(A2)
            )
        else:
            res = md5kd(A1, nonce + ":" + md5h(A2))

        return res
