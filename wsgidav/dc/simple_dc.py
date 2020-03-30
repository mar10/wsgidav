# -*- coding: utf-8 -*-
# (c) 2009-2020 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Implementation of a domain controller that uses realm/user_name/password mappings
from the configuration file and uses the share path as realm name.

user_mapping is defined a follows::

    simple_dc: {
        user_mapping = {
            "realm1": {
                "John Smith": {
                    "password": "YouNeverGuessMe",
                },
                "Dan Brown": {
                    "password": "DontGuessMeEither",
                    "roles": ["editor"]
                }
            },
            "realm2": {
                ...
            }
        },
    }

The "*" pseudo-share is used to pass a default definition::

    user_mapping = {
        "*": {  // every share except for 'realm2'
            "Dan Brown": {
                "password": "DontGuessMeEither",
                "roles": ["editor"]
            }
        },
        "realm2": {
            ...
        }
    },

A share (even the "*" pseudo-share) can be set to True to allow anonymous access::

    user_mapping = {
        "*": {
            "Dan Brown": {
                "password": "DontGuessMeEither",
                "roles": ["editor"]
            },
        },
        "realm2": True
    },

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
        dc_conf = config.get("simple_dc", {})

        self.user_map = dc_conf.get("user_mapping")
        if self.user_map is None:
            raise RuntimeError("Missing option: simple_dc.user_mapping")

        for share, data in self.user_map.items():
            if type(data) not in (bool, dict) or not data:
                raise RuntimeError(
                    "Invalid option: simple_dc.user_mapping['{}']: must be True or non-empty dict.".format(
                        share
                    )
                )
        return

    def __str__(self):
        return "{}()".format(self.__class__.__name__)

    def _get_realm_entry(self, realm, user_name=None):
        """Return the matching user_map entry (falling back to default '*' if any)."""
        realm_entry = self.user_map.get(realm)
        if realm_entry is None:
            realm_entry = self.user_map.get("*")
        if user_name is None or realm_entry is None:
            return realm_entry
        return realm_entry.get(user_name)

    def get_domain_realm(self, path_info, environ):
        """Resolve a relative url to the appropriate realm name."""
        realm = self._calc_realm_from_path_provider(path_info, environ)
        return realm

    def require_authentication(self, realm, environ):
        """Return True if this realm requires authentication (grant anonymous access otherwise)."""
        realm_entry = self._get_realm_entry(realm)
        if realm_entry is None:
            _logger.error(
                'Missing configuration simple_dc.user_mapping["{}"] (or "*"): '
                "realm is not accessible!".format(realm)
            )
        return realm_entry is not True

    def basic_auth_user(self, realm, user_name, password, environ):
        """Returns True if this user_name/password pair is valid for the realm,
        False otherwise. Used for basic authentication."""
        user = self._get_realm_entry(realm, user_name)

        if user is not None and password == user.get("password"):
            environ["wsgidav.auth.roles"] = user.get("roles", [])
            return True
        return False

    def supports_http_digest_auth(self):
        # We have access to a plaintext password (or stored hash)
        return True

    def digest_auth_user(self, realm, user_name, environ):
        """Computes digest hash A1 part."""
        user = self._get_realm_entry(realm, user_name)
        if user is None:
            return False
        password = user.get("password")
        environ["wsgidav.auth.roles"] = user.get("roles", [])
        return self._compute_http_digest_a1(realm, user_name, password)
