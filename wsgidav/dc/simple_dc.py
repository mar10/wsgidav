# -*- coding: utf-8 -*-
# (c) 2009-2018 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Implementation of a domain controller that uses realm/user_name/password mappings
from the configuration file and uses the share path as realm name.

user_map is defined a follows::

    user_map = {'realm1': {
                 'John Smith': {'description': '',
                                'password': 'YouNeverGuessMe',
                                },
                 'Dan Brown': {'description': '',
                               'password': 'DontGuessMeEither',
                               },
                 }
               'realm2': {
                 ...
                 }
               }

The SimpleDomainController fulfills the requirements of a DomainController as
used for authentication with http_authenticator.HTTPAuthenticator for the
WsgiDAV application.

Domain Controllers must provide the methods as described in
DomainControllerBase_

.. _DomainControllerBase : dc/base_dc.py

"""
from wsgidav import util
from wsgidav.dc.base_dc import BaseDomainController


__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)


class SimpleDomainController(BaseDomainController):
    def __init__(self, wsgidav_app, config):
        super(SimpleDomainController, self).__init__(wsgidav_app, config)
        dc_conf = config["simple_dc"]

        self.user_map = dc_conf.get("user_mapping")
        if self.user_map is None:
            raise RuntimeError("Missing option: simple_dc.user_mapping")

    def __str__(self):
        return "{}()".format(self.__class__.__name__)

    def get_domain_realm(self, path_info, environ):
        """Resolve a relative url to the  appropriate realm name."""
        realm = self._calc_realm_from_path(path_info, environ)
        return realm

    def require_authentication(self, realm, environ):
        """Return True if this realm requires authentication or False if it is
        available for general access."""
        # TODO: The user_mapping syntax should make this more explicit!
        return realm in self.user_map

    def basic_auth_user(self, realm, user_name, password, environ):
        """Returns True if this user_name/password pair is valid for the realm,
        False otherwise. Used for basic authentication."""
        user = self.user_map.get(realm, {}).get(user_name)

        if user is not None and password == user.get("password"):
            environ["wsgidav.auth.roles"] = user.get("roles", [])
            # environ["wsgidav.auth.permissions"] = (<perm>, ...)
            return True
        return False

    def supports_http_digest_auth(self):
        # We have access to a plaintext password (or stored hash)
        return True

    def digest_auth_user(self, realm, user_name, environ):
        """Computes digest hash A1 part."""
        password = self.user_map.get(realm, {}).get(user_name, {}).get("password")
        return self._compute_http_digest_a1(realm, user_name, password)
