# -*- coding: utf-8 -*-
# (c) 2009-2018 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Implementation of a domain controller that allows users to authenticate against
a Windows NT domain or a local computer (used by HTTPAuthenticator).

Purpose
-------

Usage::

   from wsgidav.dc.pam_dc import PamDomainController
   dc = PamDomainController(config)

"""
from __future__ import print_function
from wsgidav import util
from wsgidav.dc.dc_base import DomainControllerBase

import pam


__docformat__ = "reStructuredText"
_logger = util.get_module_logger(__name__)


class PamDomainController(DomainControllerBase):
    def __init__(self, config):

        self.pam = pam.pam()

        # auth_conf = config["http_authenticator"]
        dc_conf = config["pam_dc"]

        self.pam_service = dc_conf.get("service", "login")
        self.pam_encoding = dc_conf.get("encoding", "utf-8")
        self.pam_resetcreds = dc_conf.get("resetcreds", True)

    def __str__(self):
        return "{}('{}')".format(self.__class__.__name__, self.pam_service)

    def get_domain_realm(self, path_info, environ):
        return "PAM({})".format(self.pam_service)

    def require_authentication(self, realm, environ):
        return True

    def basic_auth_user(self, realm, user_name, password, environ):
        pam = self.pam

        is_ok = pam.authenticate(
            user_name,
            password,
            service=self.pam_service,
            resetcreds=self.pam_resetcreds,
            encoding=self.pam_encoding,
        )

        if is_ok:
            _logger.debug("User '{}' logged on.".format(user_name))
            return True

        _logger.warning(
            "pam.authenticate('{}', '***', '{}') failed with code {}: {}".format(
                user_name, self.pam_service, pam.code, pam.reason
            )
        )
        return False

    def supports_http_digest_auth(self):
        # We don't have access to a plaintext password (or stored hash)
        return False

    # def is_realm_user(self, realm, user_name, environ):
    #     # Don't know:
    #     return None

    # def get_realm_user_password(self, realm, user_name, environ):
    #     # We can't access the user's stored password for good reason.
    #     # Use Basic-Authentication over SSL instead
    #     raise NotImplementedError
