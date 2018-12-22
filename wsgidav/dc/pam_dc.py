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
   domain_controller = PamDomainController(config)


Testability and caveats
-----------------------

**Digest Authentication**
   Digest authentication requires the password to be retrieve from the system to compute
   the correct digest for comparison. This is so far impossible (and indeed would be a
   big security loophole if it was allowed), so digest authentication WILL not work
   with this class.

   Highly recommend basic authentication over SSL support.

**User Login**
   Authentication will count as a user login attempt, so any security in place for
   invalid password attempts may be triggered.

   Also note that, even though the user is logged in, the application does not impersonate
   the user - the application will continue to run under the account and permissions it
   started with. The user has the read/write permissions to the share of the running account
   and not his own account.

**Using on a local computer**
   This class has been tested on a local computer (Windows XP). Leave domain as None and
   do not specify domain when entering user_name in this case.

**Using for a network domain**
   This class is being tested for a network domain (I'm setting one up to test).

"""
from __future__ import print_function
from wsgidav import compat, util
from wsgidav.dc.dc_base import DomainControllerBase, logger

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

    # def __repr__(self):
    #     return self.__class__.__name__

    def get_domain_realm(self, input_url, environ):
        return "PAM Authentication"

    def require_authentication(self, realm_name, environ):
        return True

    def is_realm_user(self, realm_name, user_name, environ):
        (domain, usern) = self._get_domain_username(user_name)
        dcname = self._get_domain_controller_name(domain)
        return self._is_user(usern, domain, dcname)

    def get_realm_user_password(self, realm_name, user_name, environ):
        # We can't access the user's stored password for good reason.
        # Use Basic-Authentication over SSL instead
        raise NotImplementedError

    def auth_domain_user(self, realm_name, user_name, password, environ):
        raise NotImplementedError
        # (domain, usern) = self._get_domain_username(user_name)
        # dcname = self._get_domain_controller_name(domain)
        # return self._auth_user(usern, password, domain, dcname)

    def _get_domain_controller_name(self, domain):
        if self._preset_server is not None:
            return self._preset_server

        try:
            # execute this on the localhost
            pdc = win32net.NetGetAnyDCName(None, domain)
        except Exception:
            pdc = None

        return pdc

    def _is_user(self, user_name, domain, server):
        resume = "init"
        while resume:
            if resume == "init":
                resume = 0
            try:
                users, _total, resume = win32net.NetUserEnum(
                    server, 0, win32netcon.FILTER_NORMAL_ACCOUNT, 0
                )
                # Make sure, we compare unicode
                un = compat.to_unicode(user_name).lower()
                for userinfo in users:
                    uiname = userinfo.get("name")
                    assert uiname
                    assert compat.is_unicode(uiname)
                    if un == userinfo["name"].lower():
                        return True
            except win32net.error as e:
                _logger.exception("NetUserEnum: %s" % e)
                return False
        _logger.info("User '%s' not found on server '%s'" % (user_name, server))
        return False

    def _auth_user(self, user_name, password, domain, server):
        pam = self.pam
        # if not self._is_user(user_name, domain, server):
        #     return False

        is_ok = pam.authenticate(
            user_name,
            password,
            service=self.pam_service,
            resetcreds=self.pam_resetcreds,
            encoding=self.pam_encoding,
        )

        if is_ok:
            _logger.debug("User {!r} logged on.".format(user_name))
            return True

        _logger.warning(
            "LogonUser failed for user {!r}: #{} {!r}".format(
                user_name, pam.code, pam.reason
            )
        )
        return False
