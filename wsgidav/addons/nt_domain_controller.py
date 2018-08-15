# (c) 2009-2018 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Implementation of a domain controller that allows users to authenticate against
a Windows NT domain or a local computer (used by HTTPAuthenticator).

Purpose
-------

Usage::

   from wsgidav.addons.nt_domain_controller import NTDomainController
   domain_controller = NTDomainController(presetdomain=None, presetserver=None)

where:

+ domain_controller object corresponds to that in ``wsgidav.conf`` or
  as input into ``wsgidav.http_authenticator.HTTPAuthenticator``.

+ presetdomain allows the admin to specify a domain to be used (instead of any domain that
  may come as part of the user_name in domain\\user). This is useful only if there
  is one domain to be authenticated against and you want to spare users from typing the
  domain name

+ presetserver allows the admin to specify the NETBIOS name of the domain controller to
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

ml
"""
from __future__ import print_function

import win32net  # @UnresolvedImport
import win32netcon  # @UnresolvedImport
import win32security  # @UnresolvedImport
from wsgidav import compat, util

__docformat__ = "reStructuredText"
_logger = util.get_module_logger(__name__)


class NTDomainController(object):
    def __init__(self, presetdomain=None, presetserver=None):
        self._presetdomain = presetdomain
        self._presetserver = presetserver

    def __repr__(self):
        return self.__class__.__name__

    def get_domain_realm(self, input_url, environ):
        return "Windows Domain Authentication"

    def require_authentication(self, realm_name, environ):
        return True

    def is_realm_user(self, realm_name, user_name, environ):
        (domain, usern) = self._get_domain_username(user_name)
        dcname = self._get_domain_controller_name(domain)
        return self._is_user(usern, domain, dcname)

    def get_realm_user_password(self, realm_name, user_name, environ):
        (domain, user) = self._get_domain_username(user_name)
        dcname = self._get_domain_controller_name(domain)

        try:
            userdata = win32net.NetUserGetInfo(dcname, user, 1)
        except Exception:
            _logger.exception("NetUserGetInfo")
            userdata = {}
        #        if "password" in userdata:
        #            if userdata["password"] != None:
        #                return userdata["password"]
        #        return None
        return userdata.get("password")

    def auth_domain_user(self, realm_name, user_name, password, environ):
        (domain, usern) = self._get_domain_username(user_name)
        dcname = self._get_domain_controller_name(domain)
        return self._auth_user(usern, password, domain, dcname)

    def _get_domain_username(self, inusername):
        userdata = inusername.split("\\", 1)
        if len(userdata) == 1:
            domain = None
            user_name = userdata[0]
        else:
            domain = userdata[0]
            user_name = userdata[1]

        if self._presetdomain is not None:
            domain = self._presetdomain

        return (domain, user_name)

    def _get_domain_controller_name(self, domain):
        if self._presetserver is not None:
            return self._presetserver

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
                un = user_name.decode("utf8").lower()
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
        if not self._is_user(user_name, domain, server):
            return False

        try:
            htoken = win32security.LogonUser(
                user_name,
                domain,
                password,
                win32security.LOGON32_LOGON_NETWORK,
                win32security.LOGON32_PROVIDER_DEFAULT,
            )
        except win32security.error as err:
            _logger.warning("LogonUser failed for user '%s': %s" % (user_name, err))
            return False
        else:
            if htoken:
                htoken.Close()  # guarantee's cleanup
                _logger.debug("User '%s' logged on." % user_name)
                return True
            _logger.warning("Logon failed for user '%s'." % user_name)
            return False
