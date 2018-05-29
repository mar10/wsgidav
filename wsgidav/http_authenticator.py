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
   environ["http_authenticator.username"] = username


**Domain Controllers**

The HTTP basic and digest authentication schemes are based on the following
concept:

Each requested relative URI can be resolved to a realm for authentication,
for example:
/fac_eng/courses/ee5903/timetable.pdf -> might resolve to realm 'Engineering General'
/fac_eng/examsolns/ee5903/thisyearssolns.pdf -> might resolve to realm 'Engineering Lecturers'
/med_sci/courses/m500/surgery.htm -> might resolve to realm 'Medical Sciences General'
and each realm would have a set of username and password pairs that would
allow access to the resource.

A domain controller provides this information to the HTTPAuthenticator.
This allows developers to write their own domain controllers, that might,
for example, interface with their own user database.

for simple applications, a SimpleDomainController is provided that will take
in a single realm name (for display) and a single dictionary of username (key)
and password (value) string pairs

Usage::

   from http_authenticator import SimpleDomainController
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
import random
import re
import time

from wsgidav import compat, util
from wsgidav.domain_controller import WsgiDAVDomainController
from wsgidav.middleware import BaseMiddleware
from wsgidav.util import calc_base64, calc_hexdigest

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


class SimpleDomainController(object):
    """SimpleDomainController : Simple domain controller for HTTPAuthenticator."""

    def __init__(self, dictusers=None, realmname="SimpleDomain"):
        if dictusers is None:
            self._users = dict({"John Smith": "YouNeverGuessMe"})
        else:
            self._users = dictusers
        self._realmname = realmname

    def get_domain_realm(self, inputRelativeURL, environ):
        return self._realmname

    def require_authentication(self, realmname, environ):
        return True

    def is_realm_user(self, realmname, username, environ):
        return username in self._users

    def get_realm_user_password(self, realmname, username, environ):
        if username in self._users:
            return self._users[username]
        return None

    def auth_domain_user(self, realmname, username, password, environ):
        if username in self._users:
            return self._users[username] == password
        return False


# ========================================================================
# HTTPAuthenticator
# ========================================================================
class HTTPAuthenticator(BaseMiddleware):
    """WSGI Middleware for basic and digest authenticator."""

    def __init__(self, wsgidav_app, next_app, config):
        super(HTTPAuthenticator, self).__init__(wsgidav_app, next_app, config)
        self._verbose = config.get("verbose", 3)
        self._user_mapping = config.get("user_mapping", {})
        self._domaincontroller = config.get(
            "domain_controller") or WsgiDAVDomainController(self._user_mapping)
        auth_conf = config.get("http_authenticator", {})
        self._acceptbasic = auth_conf.get("accept_basic", True)
        self._acceptdigest = auth_conf.get("accept_digest", True)
        self._defaultdigest = auth_conf.get("default_to_digest", True)
        self._trusted_auth_header = auth_conf.get("trusted_auth_header", None)
        self._noncedict = dict([])

        self._headerparser = re.compile(r"([\w]+)=([^,]*),")
        # Note: extra parser to handle digest auth requests from certain
        # clients, that leave commas un-encoded to interfere with the above.
        self._headerfixparser = re.compile(r'([\w]+)=("[^"]*,[^"]*"),')
        self._headermethod = re.compile(r"^([\w]+)")

        wdcName = "NTDomainController"
        if self._domaincontroller.__class__.__name__ == wdcName:
            if self._authacceptdigest or self._authdefaultdigest or not self._authacceptbasic:
                _logger.warn(
                    "{} requires basic authentication.\n\tSet accept_basic=True, "
                    "accept_digest=False, default_to_digest=False".format(wdcName))

    def get_domain_controller(self):
        return self._domaincontroller

    def allow_anonymous_access(self, share):
        return (isinstance(self._domaincontroller, WsgiDAVDomainController)
                and not self._user_mapping.get(share))

    def __call__(self, environ, start_response):
        realmname = self._domaincontroller.get_domain_realm(environ["PATH_INFO"], environ)

        _logger.debug("realm '{}'".format(realmname))
        # _logger.debug("{}".format(environ))

        force_allow = False
        if HOTFIX_WIN_AcceptAnonymousOptions and environ["REQUEST_METHOD"] == "OPTIONS":
            _logger.warning("No authorization required for OPTIONS method")
            force_allow = True

        if force_allow or not self._domaincontroller.require_authentication(realmname, environ):
            # no authentication needed
            _logger.debug("No authorization required for realm '{}'".format(realmname))
            environ["http_authenticator.realm"] = realmname
            environ["http_authenticator.username"] = ""
            return self.next_app(environ, start_response)

        if self._trusted_auth_header and environ.get(self._trusted_auth_header):
            # accept a username that was injected by a trusted upstream server
            _logger.debug("Accept trusted username {}='{}'for realm '{}'".format(
                    self._trusted_auth_header, environ.get(self._trusted_auth_header), realmname))
            environ["http_authenticator.realm"] = realmname
            environ["http_authenticator.username"] = environ.get(self._trusted_auth_header)
            return self.next_app(environ, start_response)

        if "HTTP_AUTHORIZATION" in environ:
            authheader = environ["HTTP_AUTHORIZATION"]
            authmatch = self._headermethod.search(authheader)
            authmethod = "None"
            if authmatch:
                authmethod = authmatch.group(1).lower()

            if authmethod == "digest" and self._acceptdigest:
                return self.auth_digest_auth_request(environ, start_response)
            elif authmethod == "digest" and self._acceptbasic:
                return self.send_basic_auth_response(environ, start_response)
            elif authmethod == "basic" and self._acceptbasic:
                return self.auth_basic_auth_request(environ, start_response)

            # The requested auth method is not supported.
            elif self._defaultdigest and self._acceptdigest:
                return self.send_digest_auth_response(environ, start_response)
            elif self._acceptbasic:
                return self.send_basic_auth_response(environ, start_response)

            _logger.warn("HTTPAuthenticator: respond with 400 Bad request; Auth-Method: {}"
                         .format(authmethod))

            start_response("400 Bad Request", [("Content-Length", "0"),
                                               ("Date", util.get_rfc1123_time()),
                                               ])
            return [""]

        if self._defaultdigest:
            return self.send_digest_auth_response(environ, start_response)
        return self.send_basic_auth_response(environ, start_response)

    def send_basic_auth_response(self, environ, start_response):
        realmname = self._domaincontroller.get_domain_realm(
            environ["PATH_INFO"], environ)
        _logger.debug("401 Not Authorized for realm '{}' (basic)".format(realmname))
        wwwauthheaders = "Basic realm=\"" + realmname + "\""

        body = compat.to_bytes(self.get_error_message())
        start_response("401 Not Authorized", [("WWW-Authenticate", wwwauthheaders),
                                              ("Content-Type", "text/html"),
                                              ("Content-Length", str(len(body))),
                                              ("Date", util.get_rfc1123_time()),
                                              ])
        return [body]

    def auth_basic_auth_request(self, environ, start_response):
        realmname = self._domaincontroller.get_domain_realm(
            environ["PATH_INFO"], environ)
        authheader = environ["HTTP_AUTHORIZATION"]
        authvalue = ""
        try:
            authvalue = authheader[len("Basic "):].strip()
        except Exception:
            authvalue = ""
        # authvalue = authvalue.strip().decode("base64")
        authvalue = compat.base64_decodebytes(compat.to_bytes(authvalue))
        authvalue = compat.to_native(authvalue)
        username, password = authvalue.split(":", 1)

        if self._domaincontroller.auth_domain_user(realmname, username, password, environ):
            environ["http_authenticator.realm"] = realmname
            environ["http_authenticator.username"] = username
            return self.next_app(environ, start_response)
        return self.send_basic_auth_response(environ, start_response)

    def send_digest_auth_response(self, environ, start_response):
        realmname = self._domaincontroller.get_domain_realm(
            environ["PATH_INFO"], environ)
        random.seed()
        serverkey = hex(random.getrandbits(32))[2:]
        etagkey = calc_hexdigest(environ["PATH_INFO"])
        timekey = str(time.time())
        nonce_source = timekey + \
            calc_hexdigest(timekey + ":" + etagkey + ":" + serverkey)
        nonce = calc_base64(nonce_source)
        wwwauthheaders = ('Digest realm="{}", nonce="{}", algorithm=MD5, qop="auth"'
                          .format(realmname, nonce))

        _logger.debug("401 Not Authorized for realm '{}' (digest): {}"
                      .format(realmname, wwwauthheaders))

        body = compat.to_bytes(self.get_error_message())
        start_response("401 Not Authorized", [("WWW-Authenticate", wwwauthheaders),
                                              ("Content-Type", "text/html"),
                                              ("Content-Length", str(len(body))),
                                              ("Date", util.get_rfc1123_time()),
                                              ])
        return [body]

    def auth_digest_auth_request(self, environ, start_response):

        realmname = self._domaincontroller.get_domain_realm(
            environ["PATH_INFO"], environ)

        isinvalidreq = False

        authheaderdict = dict([])
        authheaders = environ["HTTP_AUTHORIZATION"] + ","
        if not authheaders.lower().strip().startswith("digest"):
            isinvalidreq = True
        # Hotfix for Windows file manager and OSX Finder:
        # Some clients don't urlencode paths in auth header, so uri value may
        # contain commas, which break the usual regex headerparser. Example:
        # Digest username="user",realm="/",uri="a,b.txt",nc=00000001, ...
        # -> [..., ('uri', '"a'), ('nc', '00000001'), ...]
        # Override any such values with carefully extracted ones.
        authheaderlist = self._headerparser.findall(authheaders)
        authheaderfixlist = self._headerfixparser.findall(authheaders)
        if authheaderfixlist:
            _logger.info("Fixing authheader comma-parsing: extend {} with {}"
                         .format(authheaderlist, authheaderfixlist))
            authheaderlist += authheaderfixlist
        for authheader in authheaderlist:
            authheaderkey = authheader[0]
            authheadervalue = authheader[1].strip().strip("\"")
            authheaderdict[authheaderkey] = authheadervalue

        _logger.debug("auth_digest_auth_request: {}".format(environ["HTTP_AUTHORIZATION"]))
        _logger.debug("  -> {}".format(authheaderdict))

        if "username" in authheaderdict:
            req_username = authheaderdict["username"]
            req_username_org = req_username
            # Hotfix for Windows XP:
            #   net use W: http://127.0.0.1/dav /USER:DOMAIN\tester tester
            # will send the name with double backslashes ('DOMAIN\\tester')
            # but send the digest for the simple name ('DOMAIN\tester').
            if r"\\" in req_username:
                req_username = req_username.replace("\\\\", "\\")
                _logger.info("Fixing Windows name with double backslash: '{}' --> '{}'"
                             .format(req_username_org, req_username))

            if not self._domaincontroller.is_realm_user(realmname, req_username, environ):
                isinvalidreq = True
        else:
            isinvalidreq = True

        # TODO: Chun added this comments, but code was commented out
        # Do not do realm checking - a hotfix for WinXP using some other realm's
        # auth details for this realm - if user/password match
        if "realm" in authheaderdict:
            if authheaderdict["realm"].upper() != realmname.upper():
                if HOTFIX_WINXP_AcceptRootShareLogin:
                    # Hotfix: also accept '/'
                    if authheaderdict["realm"].upper() != "/":
                        isinvalidreq = True
                else:
                    isinvalidreq = True

        if "algorithm" in authheaderdict:
            if authheaderdict["algorithm"].upper() != "MD5":
                isinvalidreq = True         # only MD5 supported

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
                isinvalidreq = True   # only auth supported, auth-int not supported
        else:
            req_qop = None

        if "cnonce" in authheaderdict:
            req_cnonce = authheaderdict["cnonce"]
        else:
            req_cnonce = None
            if req_hasqop:
                isinvalidreq = True

        if "nc" in authheaderdict:    # is read but nonce-count checking not implemented
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
            req_password = self._domaincontroller.get_realm_user_password(
                realmname, req_username, environ)

            req_method = environ["REQUEST_METHOD"]

            required_digest = self.compute_digest_response(
                req_username, realmname, req_password, req_method, req_uri, req_nonce, req_cnonce,
                req_qop, req_nc)

            if required_digest != req_response:
                _logger.warning("compute_digest_response('{}', '{}', ...): {} != {}".format(
                    realmname, req_username, required_digest, req_response))
                if HOTFIX_WINXP_AcceptRootShareLogin:
                    # Hotfix: also accept '/' digest
                    root_digest = self.compute_digest_response(
                        req_username, "/", req_password, req_method, req_uri, req_nonce,
                        req_cnonce, req_qop, req_nc)
                    if root_digest == req_response:
                        _logger.warn(
                            "auth_digest_auth_request: HOTFIX: accepting '/' login for '{}'."
                            .format(realmname))
                    else:
                        isinvalidreq = True
                else:
                    isinvalidreq = True
            else:
                # _logger.debug("digest succeeded for realm '{}', user '{}'"
                #               .format(realmname, req_username))
                pass

        if isinvalidreq:
            _logger.warn("Authentication failed for user '{}', realm '{}'"
                         .format(req_username, realmname))
            return self.send_digest_auth_response(environ, start_response)

        environ["http_authenticator.realm"] = realmname
        environ["http_authenticator.username"] = req_username
        return self.next_app(environ, start_response)

    def compute_digest_response(
            self, username, realm, password, method, uri, nonce, cnonce, qop, nc):
        A1 = username + ":" + realm + ":" + password
        A2 = method + ":" + uri
        if qop:
            digestresp = self.md5kd(self.md5h(
                A1), nonce + ":" + nc + ":" + cnonce + ":" + qop + ":" + self.md5h(A2))
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
