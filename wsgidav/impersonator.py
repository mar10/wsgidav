import os
from contextlib import AbstractContextManager
from typing import Tuple
from wsgidav import util
from wsgidav.mw.base_mw import BaseMiddleware 

_logger = util.get_module_logger(__name__)


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
		ids = environ.get("wsgidav.auth.unix_ids", None)
		with ImpersonateContext(ids):
			yield from self.next_app(environ, start_response)