import os
from contextlib import AbstractContextManager
import pwd
from typing import Tuple
from wsgidav import util
from wsgidav.mw.base_mw import BaseMiddleware 

_logger = util.get_module_logger(__name__)
_init_euid = os.geteuid()
_init_egid = os.getegid()
_logger.debug(f"impersonator: initial uid:gid = {_init_euid}:{_init_egid}")


class ImpersonateContext(AbstractContextManager):
	def __init__(self, ids: Tuple[int, int] | None) -> None:
		if ids is None:
			self._enabled = False
			return
		self._enabled = True
		self._new_euid = ids[0]
		self._new_egid = ids[1]
		self._old_euid = os.geteuid()
		self._old_egid = os.getegid()

		if self._old_euid != _init_euid or self._old_egid != _init_egid:
			raise Exception(
				"old ids mismatched with init ids: "
				f"{self._old_euid}:{self._old_egid} versus {_init_euid}:{_init_egid}, "
				"multithreading MUST be disabled for impersonator to function correctly"
			)

	def __enter__(self):
		if not self._enabled:
			return
		os.seteuid(self._new_euid)
		os.setegid(self._new_egid)
		_logger.debug(f"impersonator: set uid:gid = {self._new_euid}:{self._new_egid}")

	def __exit__(self, exc_type, exc_value, traceback, /):
		if not self._enabled:
			return
		os.seteuid(self._old_euid)
		os.setegid(self._old_egid)
		_logger.debug(f"impersonator: reset uid:gid = {self._old_euid}:{self._old_egid}")


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

	def _map_id(self, username: str) -> Tuple[int, int] | None:
		if self.is_disabled():
			return None

		unix_username = None

		if not username or username == "anonymous":
			unix_username = "nobody"
		elif self.get_config("impersonator.custom_user_mapping", None) is None: # type: ignore
			unix_username = username
		else:
			unix_username = self.get_config("impersonator.custom_user_mapping").get(username, None) # type: ignore

		if unix_username is None:
			raise RuntimeError(f"Failed mapping HTTP username '{username}' to Unix username")

		_logger.debug(f"impersonator: HTTP user {username} -> Unix user {unix_username}")

		try:
			passwd = pwd.getpwnam(unix_username)
		except:
			raise RuntimeError(f"Unix username '{unix_username}' does not exist")
		else:
			_logger.debug(f"impersonator: Unix user {unix_username} -> uid:gid = {passwd.pw_uid}:{passwd.pw_gid}")
			return (passwd.pw_uid, passwd.pw_gid)