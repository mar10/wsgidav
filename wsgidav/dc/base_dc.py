# -*- coding: utf-8 -*-
# (c) 2009-2020 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Abstract base class of a domain controller (used by HTTPAuthenticator).

This ABC serves as base class for DomainControllers and provides some
default implementations.

Domain controllers are called by `HTTPAuthenticator` to handle these tasks:

- Basic authentication:
  Check if user_name/password is allowed to perform a request

- Digest authentication (optional):
  Check if user_name is allowed to perform a request and return the MD5 hash.

- Define permissions and roles for a given user (optional).


Note that there is no checking for `isinstance(BaseDomainController)` in the
code, so WsgiDAV also accepts duck-typed domain controllers.

Digest Authentication
---------------------

See https://en.wikipedia.org/wiki/Digest_access_authentication


Permissions and Roles
---------------------

A domain controller MAY add entries to the `environment["wsgidav.auth. ..."]`
namespace in order to define access permissions for the following middleware
(e.g. dir_browser) and DAV providers.

TODO: Work In Progress / Subject to change

"""
from __future__ import print_function
from hashlib import md5
from wsgidav import compat, util

import abc
import six
import sys


__docformat__ = "reStructuredText"

logger = util.get_module_logger(__name__)


@six.add_metaclass(abc.ABCMeta)
class BaseDomainController(object):
    #: A domain controller MAY list these values as
    #: `environ["wsgidav.auth.permissions"] = (<permission>, ...)`
    known_permissions = ("browse_dir", "delete_resource", "edit_resource")
    #: A DC may list these values as `environ["wsgidav.auth.roles"] = (<role>, ...)`
    known_roles = ("admin", "editor", "reader")

    def __init__(self, wsgidav_app, config):
        self.wsgidav_app = wsgidav_app
        self.config = config

    def __str__(self):
        return "{}()".format(self.__class__.__name__)

    def _calc_realm_from_path_provider(self, path_info, environ):
        """Internal helper for derived classes to implement get_domain_realm()."""
        if environ:
            # Called while in a request:
            # We don't get the share from the path_info here: it was already
            # resolved and stripped by the request_resolver
            dav_provider = environ["wsgidav.provider"]
        else:
            # Called on start-up with the share root URL
            _share, dav_provider = self.wsgidav_app.resolve_provider(path_info)

        if not dav_provider:
            logger.warn(
                "_calc_realm_from_path_provider('{}'): '{}'".format(
                    util.safe_re_encode(path_info, sys.stdout.encoding), None
                )
            )
            return None

        realm = dav_provider.share_path
        if realm == "":
            realm = "/"
        return realm

    @abc.abstractmethod
    def get_domain_realm(self, path_info, environ):
        """Return the normalized realm name for a given URL.

        This method is called

        - On startup, to check if anonymous access is allowed for a given share.
          In this case, `environ` is None.
        - For every request, before basic or digest authentication is handled.

        A domain controller that uses the share path as realm name may use
        the `_calc_realm_from_path_provider()` helper.

        Args:
            path_info (str):
            environ (dict | None):
        Returns:
            str
        """
        raise NotImplementedError

    @abc.abstractmethod
    def require_authentication(self, realm, environ):
        """Return False to disable authentication for this request.

        This method is called

        - On startup, to check if anonymous access is allowed for a given share.
          In this case, `environ` is None.
        - For every request, before basic or digest authentication is handled.
          If False is returned, we MAY also set environment variables for
          anonymous access::

                environment["wsgidav.auth.roles"] = (<role>, ...)
                environment["wsgidav.auth.permissions"] = (<perm>, ...)
                return False

        Args:
            realm (str):
            environ (dict | None):
        Returns:
            False to allow anonymous access
            True to force subsequent digest or basic authentication
        """
        raise NotImplementedError

    def is_share_anonymous(self, path_info):
        """Return true if anonymous access will be granted to the share path.

        This method is called on start-up to print out info and warnings.

        Returns:
            bool
        """
        realm = self.get_domain_realm(path_info, None)
        return not self.require_authentication(realm, None)

    @abc.abstractmethod
    def basic_auth_user(self, realm, user_name, password, environ):
        """Check request access permissions for realm/user_name/password.

        Called by http_authenticator for basic authentication requests.

        Optionally set environment variables:

            environ["wsgidav.auth.roles"] = (<role>, ...)
            environ["wsgidav.auth.permissions"] = (<perm>, ...)

        Args:
            realm (str):
            user_name (str):
            password (str):
            environ (dict):
        Returns:
            False if user is not known or not authorized
            True if user is authorized
        """
        raise NotImplementedError

    @abc.abstractmethod
    def supports_http_digest_auth(self):
        """Signal if this DC instance supports the HTTP digest authentication theme.

        If true, `HTTPAuthenticator` will call `dc.digest_auth_user()`,
        so this method must be implemented as well.

        Returns:
            bool
        """
        raise NotImplementedError

    # def is_realm_user(self, realm, user_name, environ):
    #     """Return true if the user is known and allowed for that realm.

    #     This method is called as a pre-check for digest authentication.

    #     A domain controller MAY implement this method if this pre-check is
    #     more efficient than a hash calculation or in order to enforce a
    #     permission policy.

    #     If this method is not implemented, or None or True is returned, the
    #     http_authenticator will proceed with calculating and comparing digest
    #     hash with the current request.

    #     Returns:
    #         bool: False to reject authentication.
    #     """
    #     return None

    def _compute_http_digest_a1(self, realm, user_name, password):
        """Internal helper for derived classes to compute a digest hash (A1 part)."""
        data = user_name + ":" + realm + ":" + password
        A1 = md5(compat.to_bytes(data)).hexdigest()
        return A1

    def digest_auth_user(self, realm, user_name, environ):
        """Check access permissions for realm/user_name.

        Called by http_authenticator for basic authentication requests.

        Compute the HTTP digest hash A1 part.

        Any domain controller that returns true for `supports_http_digest_auth()`
        MUST implement this method.

        Optionally set environment variables:

            environ["wsgidav.auth.roles"] = (<role>, ...)
            environ["wsgidav.auth.permissions"] = (<perm>, ...)

        Note that in order to calculate A1, we need either

        - Access the plain text password of the user.
          In this case the method `self._compute_http_digest_a1()` can be used
          for convenience.
          Or

        - Return a stored hash value that is associated with the user name
          (for example from Apache's htdigest files).

        Args:
            realm (str):
            user_name (str):
            environ (dict):

        Returns:
            str: MD5("{usern_name}:{realm}:{password}")
            or false if user is unknown or rejected
        """
        raise NotImplementedError
