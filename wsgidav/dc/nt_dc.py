# -*- coding: utf-8 -*-
# (c) 2009-2020 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Implementation of a domain controller that allows users to authenticate against
a Windows NT domain or a local computer.

Used by HTTPAuthenticator. Only available on linux and macOS.

See also https://wsgidav.readthedocs.io/en/latest/user_guide_configure.html

Purpose
-------

Usage::

   from wsgidav.dc.nt_dc import NTDomainController
   domain_controller = NTDomainController(wsgidav_app, config)

where:

+ domain_controller object corresponds to that in ``wsgidav.yaml`` or
  as input into ``wsgidav.http_authenticator.HTTPAuthenticator``.

+ preset_domain allows the admin to specify a domain to be used (instead of any domain that
  may come as part of the user_name in domain\\user). This is useful only if there
  is one domain to be authenticated against and you want to spare users from typing the
  domain name

+ preset_server allows the admin to specify the NETBIOS name of the domain controller to
  be used (complete with the preceding \\\\). if absent, it will look for trusted
  domain controllers on the localhost.

This class allows the user to authenticate against a Windows NT domain or a local computer,
requires NT or beyond (2000, XP, 2003, etc).

This class requires Mark Hammond's Win32 extensions for Python at here_ or sourceforge_

.. _here : http://starship.python.net/crew/mhammond/win32/Downloads.html
.. _sourceforge : http://sourceforge.net/projects/pywin32/

Information on Win32 network authentication was from the following resources:

+ http://ejabberd.jabber.ru/node/55

+ http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/81402


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
from wsgidav.dc.base_dc import BaseDomainController

import win32net
import win32netcon
import win32security


__docformat__ = "reStructuredText"
_logger = util.get_module_logger(__name__)


class NTDomainController(BaseDomainController):
    def __init__(self, wsgidav_app, config):
        super(NTDomainController, self).__init__(wsgidav_app, config)
        # auth_conf = config["http_authenticator"]
        dc_conf = config.get("nt_dc", {})

        self.preset_domain = dc_conf.get("preset_domain")
        self.preset_server = dc_conf.get("preset_server")

    def __str__(self):
        return "{}({!r}, {!r})".format(
            self.__class__.__name__, self.preset_domain, self.preset_server
        )

    def get_domain_realm(self, path_info, environ):
        return "Windows Domain Authentication"

    def require_authentication(self, realm, environ):
        return True

    def basic_auth_user(self, realm, user_name, password, environ):
        domain, user = self._get_domain_username(user_name)
        dc_name = self._get_domain_controller_name(domain)
        return self._auth_user(user, password, domain, dc_name)

    def supports_http_digest_auth(self):
        # We don't have access to a plaintext password (or stored hash)
        return False

    # def is_realm_user(self, realm, user_name, environ):
    #     (domain, usern) = self._get_domain_username(user_name)
    #     dc_name = self._get_domain_controller_name(domain)
    #     return self._is_user(usern, domain, dc_name)

    # def digest_auth_user(self, realm, user_name, environ):
    #     """Computes digest hash A1 part."""
    #     password = self._get_realm_user_password(realm, user_name)
    #     return self._compute_http_digest_a1(realm, user_name, password)

    # def _get_realm_user_password(self, realm, user_name):
    #     (domain, user) = self._get_domain_username(user_name)
    #     dc_name = self._get_domain_controller_name(domain)

    #     try:
    #         userdata = win32net.NetUserGetInfo(dc_name, user, 1)
    #     except Exception:
    #         _logger.exception("NetUserGetInfo")
    #         userdata = {}
    #     return userdata.get("password")

    def _get_domain_username(self, user_name):
        user_data = user_name.split("\\", 1)
        if len(user_data) == 1:
            domain = None
            user = user_data[0]
        else:
            domain = user_data[0]
            user = user_data[1]

        if self.preset_domain is not None:
            domain = self.preset_domain

        return (domain, user)

    def _get_domain_controller_name(self, domain):
        if self.preset_server is not None:
            return self.preset_server

        try:
            # execute this on the localhost
            pdc = win32net.NetGetAnyDCName(None, domain)
        except Exception:
            pdc = None

        return pdc

    def _is_user(self, user_name, domain, server):
        # TODO: implement some kind of caching here?
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
                _logger.exception("NetUserEnum: {}".format(e))
                return False
        _logger.info("User {!r} not found on server {!r}".format(user_name, server))
        return False

    def _auth_user(self, user_name, password, domain, server):

        # TODO: implement caching?

        # TODO: is this pre-test efficient, or should we simply try LogonUser()?
        #       (Could this trigger account locking?)
        if not self._is_user(user_name, domain, server):
            return False

        htoken = None
        try:
            htoken = win32security.LogonUser(
                user_name,
                domain,
                password,
                win32security.LOGON32_LOGON_NETWORK,
                win32security.LOGON32_PROVIDER_DEFAULT,
            )
            if not htoken:
                _logger.warning(
                    "LogonUser('{}', '{}', '***') failed.".format(user_name, domain)
                )
                return False
        except win32security.error as err:
            _logger.warning(
                "LogonUser('{}', '{}', '***') failed: {}".format(user_name, domain, err)
            )
            return False
        finally:
            if htoken:
                htoken.Close()

        _logger.debug("User '{}' logged on.".format(user_name))
        return True
