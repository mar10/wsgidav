# -*- coding: utf-8 -*-
# (c) 2009-2018 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
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

   environ["http_authenticator.realm"] = realm name
   environ["http_authenticator.user_name"] = user_name


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
import inspect
import random
import re
import time
from hashlib import md5

from wsgidav import compat, util
from wsgidav.dc.simple_dc import SimpleDomainController
from wsgidav.middleware import BaseMiddleware
from wsgidav.util import calc_base64, calc_hexdigest, dynamic_import_class

__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)

# HOTFIX for Windows XP (Microsoft-WebDAV-MiniRedir/5.1.2600):
# When accessing a share '/dav/', XP sometimes sends digests for '/'.
# With this fix turned on, we allow '/' digests, when a matching '/dav' account
# is present.
HOTFIX_WINXP_AcceptRootShareLogin = True

# HOTFIX for Windows
# MW 2013-12-31: DON'T set this (will MS office to use anonymous always in
# some scenarios)
HOTFIX_WIN_AcceptAnonymousOptions = False


def make_domain_controller(config):
    dc = config.get("http_authenticator", {}).get("domain_controller")
    if dc is True or not dc:
        # True or null:
        dc = SimpleDomainController

    if compat.is_basestring(dc):
        # If a plain string is passed, try to import it as class
        dc = dynamic_import_class(dc)

    if inspect.isclass(dc):
        # If a class is passed, instantiate that
        dc = dc(config)

    # print("make_domain_controller", dc)
    return dc


# ========================================================================
# HTTPAuthenticator
# ========================================================================
class HTTPAuthenticator(BaseMiddleware):
    """WSGI Middleware for basic and digest authenticator."""

    def __init__(self, wsgidav_app, next_app, config):
        super(HTTPAuthenticator, self).__init__(wsgidav_app, next_app, config)
        self._verbose = config.get("verbose", 3)
        self.config = config
        auth_conf = config.get("http_authenticator", {})

        self.domain_controller = make_domain_controller(config)
        # self.domain_controller = dc = auth_conf.get("domain_controller")
        # if not dc or not callable(getattr(dc, "auth_domain_user")):
        #     raise RuntimeError("Invalid domain controller {}".format(dc))
        # self._user_mapping = config.get("user_mapping", {})
        # self.domain_controller = config.get(
        #     "domain_controller"
        # ) or SimpleDomainController(self._user_mapping)
        self._accept_basic = auth_conf.get("accept_basic", True)
        self._accept_digest = auth_conf.get("accept_digest", True)
        self._default_digest = auth_conf.get("default_to_digest", True)
        self._trusted_auth_header = auth_conf.get("trusted_auth_header", None)

        self._nonce_dict = dict([])

        self._header_parser = re.compile(r"([\w]+)=([^,]*),")
        # Note: extra parser to handle digest auth requests from certain
        # clients, that leave commas un-encoded to interfere with the above.
        self._header_fix_parser = re.compile(r'([\w]+)=("[^"]*,[^"]*"),')
        self._header_method = re.compile(r"^([\w]+)")

    def get_domain_controller(self):
        return self.domain_controller

    def allow_anonymous_access(self, share):
        # FIXME: use DC
        # return self.domain_controller.require_authentication(share)
        return isinstance(
            self.domain_controller, SimpleDomainController
        ) and not self.config["user_mapping"].get(share)

    def __call__(self, environ, start_response):
        realm_name = self.domain_controller.get_domain_realm(
            environ["PATH_INFO"], environ
        )

        _logger.debug("realm '{}'".format(realm_name))
        # _logger.debug("{}".format(environ))

        force_allow = False
        if HOTFIX_WIN_AcceptAnonymousOptions and environ["REQUEST_METHOD"] == "OPTIONS":
            _logger.warning("No authorization required for OPTIONS method")
            force_allow = True

        if force_allow or not self.domain_controller.require_authentication(
            realm_name, environ
        ):
            # no authentication needed
            _logger.debug("No authorization required for realm '{}'".format(realm_name))
            environ["http_authenticator.realm"] = realm_name
            environ["http_authenticator.user_name"] = ""
            return self.next_app(environ, start_response)

        if self._trusted_auth_header and environ.get(self._trusted_auth_header):
            # accept a user_name that was injected by a trusted upstream server
            _logger.debug(
                "Accept trusted user_name {}='{}'for realm '{}'".format(
                    self._trusted_auth_header,
                    environ.get(self._trusted_auth_header),
                    realm_name,
                )
            )
            environ["http_authenticator.realm"] = realm_name
            environ["http_authenticator.user_name"] = environ.get(
                self._trusted_auth_header
            )
            return self.next_app(environ, start_response)

        if "HTTP_AUTHORIZATION" in environ:
            authheader = environ["HTTP_AUTHORIZATION"]
            authmatch = self._header_method.search(authheader)
            authmethod = "None"
            if authmatch:
                authmethod = authmatch.group(1).lower()

            if authmethod == "digest" and self._accept_digest:
                return self.auth_digest_auth_request(environ, start_response)
            elif authmethod == "digest" and self._accept_basic:
                return self.send_basic_auth_response(environ, start_response)
            elif authmethod == "basic" and self._accept_basic:
                return self.auth_basic_auth_request(environ, start_response)

            # The requested auth method is not supported.
            elif self._default_digest and self._accept_digest:
                return self.send_digest_auth_response(environ, start_response)
            elif self._accept_basic:
                return self.send_basic_auth_response(environ, start_response)

            _logger.warn(
                "HTTPAuthenticator: respond with 400 Bad request; Auth-Method: {}".format(
                    authmethod
                )
            )

            start_response(
                "400 Bad Request",
                [("Content-Length", "0"), ("Date", util.get_rfc1123_time())],
            )
            return [""]

        if self._default_digest:
            return self.send_digest_auth_response(environ, start_response)
        return self.send_basic_auth_response(environ, start_response)

    def send_basic_auth_response(self, environ, start_response):
        realm_name = self.domain_controller.get_domain_realm(
            environ["PATH_INFO"], environ
        )
        _logger.debug("401 Not Authorized for realm '{}' (basic)".format(realm_name))
        wwwauthheaders = 'Basic realm="' + realm_name + '"'

        body = compat.to_bytes(self.get_error_message())
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

    def auth_basic_auth_request(self, environ, start_response):
        realm_name = self.domain_controller.get_domain_realm(
            environ["PATH_INFO"], environ
        )
        authheader = environ["HTTP_AUTHORIZATION"]
        authvalue = ""
        try:
            authvalue = authheader[len("Basic ") :].strip()
        except Exception:
            authvalue = ""
        # authvalue = authvalue.strip().decode("base64")
        authvalue = compat.base64_decodebytes(compat.to_bytes(authvalue))
        authvalue = compat.to_native(authvalue)
        user_name, password = authvalue.split(":", 1)

        if self.domain_controller.auth_domain_user(
            realm_name, user_name, password, environ
        ):
            environ["http_authenticator.realm"] = realm_name
            environ["http_authenticator.user_name"] = user_name
            return self.next_app(environ, start_response)
        return self.send_basic_auth_response(environ, start_response)

    def send_digest_auth_response(self, environ, start_response):
        realm_name = self.domain_controller.get_domain_realm(
            environ["PATH_INFO"], environ
        )
        random.seed()
        serverkey = hex(random.getrandbits(32))[2:]
        etagkey = calc_hexdigest(environ["PATH_INFO"])
        timekey = str(time.time())
        nonce_source = timekey + calc_hexdigest(
            timekey + ":" + etagkey + ":" + serverkey
        )
        nonce = calc_base64(nonce_source)
        wwwauthheaders = 'Digest realm="{}", nonce="{}", algorithm=MD5, qop="auth"'.format(
            realm_name, nonce
        )

        _logger.debug(
            "401 Not Authorized for realm '{}' (digest): {}".format(
                realm_name, wwwauthheaders
            )
        )

        body = compat.to_bytes(self.get_error_message())
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

    def auth_digest_auth_request(self, environ, start_response):

        realm_name = self.domain_controller.get_domain_realm(
            environ["PATH_INFO"], environ
        )

        isinvalidreq = False

        authheaderdict = dict([])
        authheaders = environ["HTTP_AUTHORIZATION"] + ","
        if not authheaders.lower().strip().startswith("digest"):
            isinvalidreq = True
        # Hotfix for Windows file manager and OSX Finder:
        # Some clients don't urlencode paths in auth header, so uri value may
        # contain commas, which break the usual regex headerparser. Example:
        # Digest user_name="user",realm="/",uri="a,b.txt",nc=00000001, ...
        # -> [..., ('uri', '"a'), ('nc', '00000001'), ...]
        # Override any such values with carefully extracted ones.
        authheaderlist = self._header_parser.findall(authheaders)
        authheaderfixlist = self._header_fix_parser.findall(authheaders)
        if authheaderfixlist:
            _logger.info(
                "Fixing authheader comma-parsing: extend {} with {}".format(
                    authheaderlist, authheaderfixlist
                )
            )
            authheaderlist += authheaderfixlist
        for authheader in authheaderlist:
            authheaderkey = authheader[0]
            authheadervalue = authheader[1].strip().strip('"')
            authheaderdict[authheaderkey] = authheadervalue

        _logger.debug(
            "auth_digest_auth_request: {}".format(environ["HTTP_AUTHORIZATION"])
        )
        _logger.debug("  -> {}".format(authheaderdict))

        if "user_name" in authheaderdict:
            req_username = authheaderdict["user_name"]
            req_username_org = req_username
            # Hotfix for Windows XP:
            #   net use W: http://127.0.0.1/dav /USER:DOMAIN\tester tester
            # will send the name with double backslashes ('DOMAIN\\tester')
            # but send the digest for the simple name ('DOMAIN\tester').
            if r"\\" in req_username:
                req_username = req_username.replace("\\\\", "\\")
                _logger.info(
                    "Fixing Windows name with double backslash: '{}' --> '{}'".format(
                        req_username_org, req_username
                    )
                )

            if not self.domain_controller.is_realm_user(
                realm_name, req_username, environ
            ):
                isinvalidreq = True
        else:
            isinvalidreq = True

        # TODO: Chun added this comments, but code was commented out
        # Do not do realm checking - a hotfix for WinXP using some other realm's
        # auth details for this realm - if user/password match
        if "realm" in authheaderdict:
            if authheaderdict["realm"].upper() != realm_name.upper():
                if HOTFIX_WINXP_AcceptRootShareLogin:
                    # Hotfix: also accept '/'
                    if authheaderdict["realm"].upper() != "/":
                        isinvalidreq = True
                else:
                    isinvalidreq = True

        if "algorithm" in authheaderdict:
            if authheaderdict["algorithm"].upper() != "MD5":
                isinvalidreq = True  # only MD5 supported

        if "uri" in authheaderdict:
            req_uri = authheaderdict["uri"]

        if "nonce" in authheaderdict:
            req_nonce = authheaderdict["nonce"]
        else:
            isinvalidreq = True

        req_hasqop = False
        if "qop" in authheaderdict:
            req_hasqop = True
            req_qop = authheaderdict["qop"]
            if req_qop.lower() != "auth":
                isinvalidreq = True  # only auth supported, auth-int not supported
        else:
            req_qop = None

        if "cnonce" in authheaderdict:
            req_cnonce = authheaderdict["cnonce"]
        else:
            req_cnonce = None
            if req_hasqop:
                isinvalidreq = True

        if "nc" in authheaderdict:  # is read but nonce-count checking not implemented
            req_nc = authheaderdict["nc"]
        else:
            req_nc = None
            if req_hasqop:
                isinvalidreq = True

        if "response" in authheaderdict:
            req_response = authheaderdict["response"]
        else:
            isinvalidreq = True

        if not isinvalidreq:
            req_password = self.domain_controller.get_realm_user_password(
                realm_name, req_username, environ
            )

            req_method = environ["REQUEST_METHOD"]

            required_digest = self.compute_digest_response(
                req_username,
                realm_name,
                req_password,
                req_method,
                req_uri,
                req_nonce,
                req_cnonce,
                req_qop,
                req_nc,
            )

            if required_digest != req_response:
                _logger.warning(
                    "compute_digest_response('{}', '{}', ...): {} != {}".format(
                        realm_name, req_username, required_digest, req_response
                    )
                )
                if HOTFIX_WINXP_AcceptRootShareLogin:
                    # Hotfix: also accept '/' digest
                    root_digest = self.compute_digest_response(
                        req_username,
                        "/",
                        req_password,
                        req_method,
                        req_uri,
                        req_nonce,
                        req_cnonce,
                        req_qop,
                        req_nc,
                    )
                    if root_digest == req_response:
                        _logger.warn(
                            "auth_digest_auth_request: HOTFIX: accepting '/' login for '{}'.".format(
                                realm_name
                            )
                        )
                    else:
                        isinvalidreq = True
                else:
                    isinvalidreq = True
            else:
                # _logger.debug("digest succeeded for realm '{}', user '{}'"
                #               .format(realm_name, req_username))
                pass

        if isinvalidreq:
            _logger.warn(
                "Authentication failed for user '{}', realm '{}'".format(
                    req_username, realm_name
                )
            )
            return self.send_digest_auth_response(environ, start_response)

        environ["http_authenticator.realm"] = realm_name
        environ["http_authenticator.user_name"] = req_username
        return self.next_app(environ, start_response)

    def compute_digest_response(
        self, user_name, realm, password, method, uri, nonce, cnonce, qop, nc
    ):
        A1 = user_name + ":" + realm + ":" + password
        A2 = method + ":" + uri
        if qop:
            digestresp = self.md5kd(
                self.md5h(A1),
                nonce + ":" + nc + ":" + cnonce + ":" + qop + ":" + self.md5h(A2),
            )
        else:
            digestresp = self.md5kd(self.md5h(A1), nonce + ":" + self.md5h(A2))
        return digestresp

    def md5h(self, data):
        return md5(compat.to_bytes(data)).hexdigest()

    def md5kd(self, secret, data):
        return self.md5h(secret + ":" + data)

    def get_error_message(self):
        message = """
<html><head><title>401 Access not authorized</title></head>
<body>
<h1>401 Access not authorized</h1>
</body>
</html>
"""
        return message
