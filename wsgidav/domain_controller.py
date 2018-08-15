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

The WsgiDAVDomainController fulfills the requirements of a DomainController as
used for authentication with http_authenticator.HTTPAuthenticator for the
WsgiDAV application.

Domain Controllers must provide the methods as described in
domaincontrollerinterface_

.. _domaincontrollerinterface : interfaces/domaincontrollerinterface.py

"""
import sys

from wsgidav import util

__docformat__ = "reStructuredText"

_logger = util.get_module_logger(__name__)


class WsgiDAVDomainController(object):
    def __init__(self, user_map):
        self.user_map = user_map
        # self.allowAnonymous = allowAnonymous

    def __repr__(self):
        return self.__class__.__name__

    def get_domain_realm(self, input_url, environ):
        """Resolve a relative url to the  appropriate realm name."""
        # we don't get the realm here, its already been resolved in
        # request_resolver
        dav_provider = environ["wsgidav.provider"]
        if not dav_provider:
            if environ["wsgidav.verbose"] >= 2:
                _logger.debug(
                    "get_domain_realm({}): '{}'".format(
                        util.safe_re_encode(input_url, sys.stdout.encoding), None
                    )
                )
            return None
        realm = dav_provider.sharePath
        if realm == "":
            realm = "/"
        return realm

    def require_authentication(self, realm_name, environ):
        """Return True if this realm requires authentication or False if it is
        available for general access."""
        # TODO: Should check for --allow_anonymous?
        #        assert realm_name in environ["wsgidav.config"]["user_mapping"], (
        #            "Currently there must be at least on user mapping for this realm")
        return realm_name in self.user_map

    def is_realm_user(self, realm_name, user_name, environ):
        """Returns True if this user_name is valid for the realm, False otherwise."""
        return realm_name in self.user_map and user_name in self.user_map[realm_name]

    def get_realm_user_password(self, realm_name, user_name, environ):
        """Return the password for the given user_name for the realm.

        Used for digest authentication.
        """
        return self.user_map.get(realm_name, {}).get(user_name, {}).get("password")

    def auth_domain_user(self, realm_name, user_name, password, environ):
        """Returns True if this user_name/password pair is valid for the realm,
        False otherwise. Used for basic authentication."""
        user = self.user_map.get(realm_name, {}).get(user_name)
        return user is not None and password == user.get("password")
