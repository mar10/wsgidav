# (c) 2009-2024 Martin Wendt and contributors; see WsgiDAV https://github.com/mar10/wsgidav
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
"""
WSGI middleware to impersonate a Unix user based on the HTTP username.
This middleware changes the effective user ID (euid) and group ID (egid) of the
current process to match the Unix user corresponding to the HTTP username.
This is useful for applications that need to access files or resources with the
permissions of a specific Unix user.

NOTE: **Experimental**:
This middleware is not thread-safe and should not be used in a
multithreaded environment. It is designed to be used in a single-threaded
context where the effective user ID and group ID can be safely changed and
restored.
"""

import os
import pwd
from contextlib import AbstractContextManager

from wsgidav import util
from wsgidav.mw.base_mw import BaseMiddleware

_logger = util.get_module_logger(__name__)
_init_pwd = pwd.getpwuid(os.geteuid())
_logger.debug(f"impersonator: initial uid:gid = {_init_pwd.pw_uid}:{_init_pwd.pw_gid}")


class ImpersonateContext(AbstractContextManager):
    def __init__(self, pwd: pwd.struct_passwd | None) -> None:
        if pwd is None:
            self._enabled = False
            return

        self._enabled = True
        self._pwd = pwd

        if os.geteuid() != _init_pwd.pw_uid or os.getegid() != _init_pwd.pw_gid:
            raise Exception(
                "current ids mismatched with init ids: "
                f"{os.geteuid()}:{os.getegid()} versus {_init_pwd.pw_uid}:{_init_pwd.pw_gid}, "
                "multithreading MUST be disabled for impersonator to function correctly"
            )

    def __enter__(self):
        if not self._enabled:
            return
        os.seteuid(self._pwd.pw_uid)
        os.setegid(self._pwd.pw_gid)
        os.initgroups(self._pwd.pw_name, self._pwd.pw_gid)
        _logger.debug(f"impersonator: set uid:gid = {os.geteuid()}:{os.getegid()}")
        _logger.debug(f"impersonator: set groups = {os.getgroups()}")

    def __exit__(self, exc_type, exc_value, traceback, /):
        if not self._enabled:
            return
        os.seteuid(_init_pwd.pw_uid)
        os.setegid(_init_pwd.pw_gid)
        os.initgroups(_init_pwd.pw_name, _init_pwd.pw_gid)
        _logger.debug(f"impersonator: reset uid:gid = {os.geteuid()}:{os.getegid()}")
        _logger.debug(f"impersonator: reset groups = {os.getgroups()}")


class Impersonator(BaseMiddleware):
    def __init__(self, wsgidav_app, next_app, config):
        super().__init__(wsgidav_app, next_app, config)

    def __call__(self, environ, start_response):
        username = environ.get("wsgidav.auth.user_name", "")
        ids = self._map_id(username)
        with ImpersonateContext(ids):
            yield from self.next_app(environ, start_response)

    def is_disabled(self):  # type: ignore
        return not self.get_config("impersonator.enable", False)  # type: ignore

    def _map_id(self, username: str) -> pwd.struct_passwd | None:
        if self.is_disabled():
            return None

        unix_username = None

        if not username:
            unix_username = "nobody"
        elif self.get_config("impersonator.custom_user_mapping", None) is None:  # type: ignore
            unix_username = username
        else:
            unix_username = self.get_config("impersonator.custom_user_mapping").get(
                username, None
            )  # type: ignore

        if unix_username is None:
            raise RuntimeError(f"Failed mapping HTTP username '{username}' to Unix username")

        _logger.debug(
            f"impersonator: HTTP user {username or '(anonymous)'} -> Unix user {unix_username}"
        )

        try:
            passwd = pwd.getpwnam(unix_username)
            if self.get_config("impersonator.reject_system_users", False) and passwd.pw_uid <= 999:
                raise ValueError
        except ValueError:
            raise RuntimeError(
                f"Unix user '{unix_username}' is a system user, impersonating rejected"
            ) from None
        except Exception:
            raise RuntimeError(
                f"Unix username '{unix_username}' does not exist"
            ) from None
        else:
            return passwd
