# (c) 2009-2024 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Implementation of a domain controller that allows users to authenticate against
a Pluggable Authentication Module ('PAM').

Used by HTTPAuthenticator. Only available on linux and macOS.

See https://wsgidav.readthedocs.io/en/latest/user_guide_configure.html
"""

import os
import threading

from wsgidav import util
from wsgidav.dc.base_dc import BaseDomainController

__docformat__ = "reStructuredText"
_logger = util.get_module_logger(__name__)

try:
    import pam
except ImportError:
    _logger.error(
        "pam_dc requires the `python-pam` module. Try `pip install wsgidav[pam]`."
    )
    raise


class PAMDomainController(BaseDomainController):
    def __init__(self, wsgidav_app, config):
        super().__init__(wsgidav_app, config)

        self.lock = threading.RLock()
        self.pam = pam.pam()

        dc_conf = util.get_dict_value(config, "pam_dc", as_dict=True)

        self.pam_service = dc_conf.get("service", "login")
        self.pam_encoding = dc_conf.get("encoding", "utf-8")
        self.pam_resetcreds = dc_conf.get("resetcreds", True)
        self.allow_users = dc_conf.get("allow_users", "all")
        if not (
            self.allow_users in ("all", "current") or isinstance(self.allow_users, list)
        ):
            raise ValueError(
                f"Invalid 'allow_users' value: {self.allow_users!r}, expected 'all', 'current' or list of allowed users."
            )
        self.deny_users = dc_conf.get("deny_users", [])
        if not isinstance(self.deny_users, list):
            raise ValueError(
                f"Invalid 'deny_users' value: {self.deny_users!r}, expected list of denied users."
            )

    def __str__(self):
        return f"{self.__class__.__name__}({self.pam_service!r})"

    def get_domain_realm(self, path_info, environ):
        return f"PAM({self.pam_service})"

    def require_authentication(self, realm, environ):
        return True

    def _validate_user(self, user_name):
        if user_name in self.deny_users:
            return False
        if self.allow_users == "all":
            return True
        if self.allow_users == "current":
            if user_name == os.getlogin():
                return True
        if user_name in self.allow_users:
            return True
        return False

    def basic_auth_user(self, realm, user_name, password, environ):
        # Seems that python_pam is not threadsafe (#265)
        if not self._validate_user(user_name):
            _logger.warning(f"User {user_name!r} is not allowed.")
            return False
        with self.lock:
            is_ok = self.pam.authenticate(
                user_name,
                password,
                service=self.pam_service,
                resetcreds=self.pam_resetcreds,
                encoding=self.pam_encoding,
            )
            if not is_ok:
                _logger.warning(
                    f"pam.authenticate({user_name!r}, '<redacted>', {self.pam_service!r}) failed with code {self.pam.code}: {self.pam.reason}"
                )
                return False

        _logger.debug(f"User {user_name!r} logged on.")
        return True

    def supports_http_digest_auth(self):
        # We don't have access to a plaintext password (or stored hash)
        return False
