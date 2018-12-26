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
        # auth_conf = config["http_authenticator"]
        dc_conf = config["simple_dc"]

        self.user_map = dc_conf.get("user_mapping")
        if self.user_map is None:
            raise RuntimeError("Missing option: simple_dc.user_mapping")
        # self.allowAnonymous = allowAnonymous

    def __str__(self):
        return "{}()".format(self.__class__.__name__)

    def get_domain_realm(self, path_info, environ):
        """Resolve a relative url to the  appropriate realm name."""
        realm = self._calc_realm_from_path(path_info, environ)
        # we don't get the realm here, it was already resolved in the request_resolver
        # dav_provider = ["wsgidav.provider"]
        # dav_provider = environ["wsgidav.provider"]
        # if not dav_provider:
        #     _logger.warn(
        #         "get_domain_realm('{}'): '{}'".format(
        #             util.safe_re_encode(path_info, sys.stdout.encoding), None
        #         )
        #     )
        #     return None
        # realm = dav_provider.share_path
        # if realm == "":
        #     realm = "/"
        # _logger.debug(
        #     "get_domain_realm('{}'): '{}'".format(
        #         util.safe_re_encode(path_info, sys.stdout.encoding), realm
        #     )
        # )
        return realm

    def require_authentication(self, realm, environ):
        """Return True if this realm requires authentication or False if it is
        available for general access."""

        # TODO: Should check for --allow-anonymous?
        #        assert realm in environ["wsgidav.config"]["user_mapping"], (
        #            "Currently there must be at least on user mapping for this realm")
        # Or better: only return False if user map contains a special entry for that share!!
        return realm in self.user_map

    def basic_auth_user(self, realm, user_name, password, environ):
        """Returns True if this user_name/password pair is valid for the realm,
        False otherwise. Used for basic authentication."""
        user = self.user_map.get(realm, {}).get(user_name)
        return user is not None and password == user.get("password")

    def supports_http_digest_auth(self):
        # We have access to a plaintext password (or stored hash)
        return True

    # def is_realm_user(self, realm, user_name, environ):
    #     """Return True if this user_name is valid for the realm.

    #     Called by http_authenticator for digest authentication.
    #     """
    #     return realm in self.user_map and user_name in self.user_map[realm]

    def digest_auth_user(self, realm, user_name, environ):
        """Computes digest hash A1 part."""
        password = self.user_map.get(realm, {}).get(user_name, {}).get("password")
        return self._compute_http_digest_a1(realm, user_name, password)
