# -*- coding: utf-8 -*-
# (c) 2009-2018 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
"""
Abstract base class of a domain controller (used by HTTPAuthenticator).
"""
from __future__ import print_function
from wsgidav import util

import abc
import six


__docformat__ = "reStructuredText"

logger = util.get_module_logger(__name__)


@six.add_metaclass(abc.ABCMeta)
class DomainControllerBase(object):
    def __init__(self, config):
        pass

    # def __repr__(self):
    #     return self.__class__.__name__

    @abc.abstractmethod
    def get_domain_realm(self, input_url, environ):
        raise NotImplementedError

    @abc.abstractmethod
    def require_authentication(self, realm_name, environ):
        raise NotImplementedError

    # @classmethod
    @abc.abstractmethod
    def _need_plaintext_password(self):
        raise NotImplementedError

    @abc.abstractmethod
    def is_realm_user(self, realm_name, user_name, environ):
        raise NotImplementedError

    @abc.abstractmethod
    def get_realm_user_password(self, realm_name, user_name, environ):
        raise NotImplementedError

    @abc.abstractmethod
    def auth_domain_user(self, realm_name, user_name, password, environ):
        raise NotImplementedError
