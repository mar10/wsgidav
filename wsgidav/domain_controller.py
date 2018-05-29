# (c) 2009-2018 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Original PyFileServer (c) 2005 Ho Chun Wei.
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
Implementation of a domain controller that uses realm/username/password mappings
from the configuration file and uses the share path as realm name.

userMap is defined a follows::

    userMap = {'realm1': {
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

    def __init__(self, userMap):
        self.userMap = userMap
#        self.allowAnonymous = allowAnonymous

    def __repr__(self):
        return self.__class__.__name__

    def get_domain_realm(self, inputURL, environ):
        """Resolve a relative url to the  appropriate realm name."""
        # we don't get the realm here, its already been resolved in
        # request_resolver
        davProvider = environ["wsgidav.provider"]
        if not davProvider:
            if environ["wsgidav.verbose"] >= 2:
                _logger.debug("get_domain_realm({}): '{}'".format(
                        util.safe_re_encode(inputURL, sys.stdout.encoding),
                        None))
            return None
        realm = davProvider.sharePath
        if realm == "":
            realm = "/"
        return realm

    def require_authentication(self, realmname, environ):
        """Return True if this realm requires authentication or False if it is
        available for general access."""
        # TODO: Should check for --allow_anonymous?
#        assert realmname in environ["wsgidav.config"]["user_mapping"], (
#            "Currently there must be at least on user mapping for this realm")
        return realmname in self.userMap

    def is_realm_user(self, realmname, username, environ):
        """Returns True if this username is valid for the realm, False otherwise."""
        return realmname in self.userMap and username in self.userMap[realmname]

    def get_realm_user_password(self, realmname, username, environ):
        """Return the password for the given username for the realm.

        Used for digest authentication.
        """
        return self.userMap.get(realmname, {}).get(username, {}).get("password")

    def auth_domain_user(self, realmname, username, password, environ):
        """Returns True if this username/password pair is valid for the realm,
        False otherwise. Used for basic authentication."""
        user = self.userMap.get(realmname, {}).get(username)
        return user is not None and password == user.get("password")
