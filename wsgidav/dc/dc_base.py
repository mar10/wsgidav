# -*- coding: utf-8 -*-
# (c) 2009-2018 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Abstract base class of a domain controller (used by HTTPAuthenticator).

This ABC serves as base class for DomainControllers and provides some
default implementations.

Note that there is no checking for `isinstance(DomainControllerBase)` in the
code, so WsgiDAV also accepts duck-typed domain controllers.

Digest Authentication
---------------------

See https://en.wikipedia.org/wiki/Digest_access_authentication
"""
from __future__ import print_function
from hashlib import md5
from wsgidav import compat, util

import abc
import six


__docformat__ = "reStructuredText"

logger = util.get_module_logger(__name__)


@six.add_metaclass(abc.ABCMeta)
class DomainControllerBase(object):
    def __init__(self, config):
        pass

    @abc.abstractmethod
    def get_domain_realm(self, path_info, environ):
        """Return the normalized realm name for a given URL."""
        raise NotImplementedError

    @abc.abstractmethod
    def require_authentication(self, realm, environ):
        """Return False to disable authentication for this request."""
        raise NotImplementedError

    @abc.abstractmethod
    def auth_domain_user(self, realm, user_name, password, environ):
        """Returns True if this user_name/password pair is valid for the realm,
        False otherwise.

        Called by http_authenticator for basic authentication requests.

        Returns:
            bool
        """
        raise NotImplementedError

    @abc.abstractmethod
    def supports_http_digest_auth(self):
        """Signal if this DC instance supports the HTTP digest authentication theme.

        If true, `HTTPAuthenticator` will call `dc.compute_http_digest_a1()`,
        so this method must be implemented as well.

        Returns:
            True if
        """
        raise NotImplementedError

    def is_realm_user(self, realm, user_name, environ):
        """Return true if the user is known and allowed for that realm.

        This method is called as a pre-check for digest authentication.

        A domain controller MAY implement this method if the pre-check is
        more efficient than a hash calculation or in order to enforce a
        permission policy.

        If this method is not implemented, or None or True is returned, the
        http_authenticator will proceed with calculating and comparing digest
        hash with the current request.

        Returns:
            bool: False to reject authentication.
        """
        return None

    def _compute_http_digest_a1(self, realm, user_name, password):
        """Internal helper to compute digest hash (A1 part)."""
        data = user_name + ":" + realm + ":" + password
        A1 = md5(compat.to_bytes(data)).hexdigest()
        return A1

    def compute_http_digest_a1(self, realm, user_name):
        """Compute the HTTP digest hash A1 part.

        Any domain controller that returns true for `supports_http_digest_auth()`
        MUST implement this method.

        Note that in order to calculate A1, we need either

        - Access the plain text password of the user.
          In this case the method `self._compute_http_digest_a1()` can be used
          for convenience.
          Or
        - Return a stored hash value that is associated to the user name
          (for example from Apache's htdigest files).

        Args:
            realm (str):
            user_name (str):

        Return:
            string (MD5 Hash)
        """
        raise NotImplementedError
