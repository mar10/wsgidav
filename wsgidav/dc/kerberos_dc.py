from abc import ABC, abstractmethod
import bcrypt
import redis
import re
import os
import gssapi
import gssapi.raw
import gssapi.raw.misc
import time

from wsgidav import util
from wsgidav.dc.base_dc import BaseDomainController


class KerberosAuthCacheBase(ABC):
	@abstractmethod
	def save(self, username: str, password: str) -> None:
		raise NotImplementedError

	@abstractmethod
	def check(self, username: str, password: str) -> bool:
		raise NotImplementedError

	@abstractmethod
	def delete(self, username: str) -> None:
		raise NotImplementedError

	@abstractmethod
	def flush(self) -> None:
		raise NotImplementedError

	def _bcrypt_hash_password(self, password: str) -> bytes:
		return bcrypt.hashpw(bytes(password, encoding='ascii'), bcrypt.gensalt())

	def _bcrypt_check_password(self, password: str, pwhash: bytes):
		return bcrypt.checkpw(bytes(password, encoding='ascii'), pwhash)


class MemoryKerberosAuthCache(KerberosAuthCacheBase):
	def __init__(self, ttl: int = 600) -> None:
		self.cache = dict()
		self.ttl = ttl

	def save(self, username: str, password: str) -> None:
		self.cache[username] = (self._bcrypt_hash_password(password), int(time.time()))

	def check(self, username: str, password: str) -> bool:
		if username not in self.cache: return False
		if int(time.time()) - self.cache[username][1] >= self.ttl: return False
		return self._bcrypt_check_password(password, self.cache[username][0])

	def delete(self, username: str) -> None:
		if username not in self.cache: return
		del self.cache[username]

	def flush(self) -> None:
		self.cache = dict()


class RedisKerberosAuthCache(KerberosAuthCacheBase):
	def __init__(self, host: str, port: int = 6379, db: int = 0, password: str | None = None, ttl: int = 600) -> None:
		self.redis = None
		self.host = host
		self.port = port
		self.db = db
		self.password = password
		self.ttl = ttl

	def save(self, username: str, password: str) -> None:
		if self.redis is None:
			self.redis = redis.Redis(self.host, self.port, self.db, self.password)
		self.redis.set(username, self._bcrypt_hash_password(password), ex=self.ttl)

	def check(self, username: str, password: str) -> bool:
		if self.redis is None:
			self.redis = redis.Redis(self.host, self.port, self.db, self.password)
		pwhash = self.redis.get(username)
		if pwhash is None: return False
		assert isinstance(pwhash, bytes)
		return self._bcrypt_check_password(password, pwhash)

	def flush(self) -> None:
		if self.redis is None:
			self.redis = redis.Redis(self.host, self.port, self.db, self.password)
		self.redis.flushdb()

	def delete(self, username: str) -> None:
		if self.redis is None:
			self.redis = redis.Redis(self.host, self.port, self.db, self.password)
		self.redis.delete(username)


class KerberosDomainController(BaseDomainController):
	def __init__(self, wsgidav_app, config):
		super().__init__(wsgidav_app, config)

		dc_conf = util.get_dict_value(config, 'kerberos_dc', as_dict=True)

		if not isinstance(dc_conf, dict):
			raise RuntimeError('Missing config: kerberos_dc')

		keytab = dc_conf.get('keytab', None)
		realm = dc_conf.get('realm')
		spn = dc_conf.get('spn')
		upn_allowlist = dc_conf.get('upn_allowlist', None)
		cache = dc_conf.get('cache', None)

		if realm is None:
			raise RuntimeError('Missing option: kerberos_dc.realm')

		if spn is None:
			raise RuntimeError('Missing option: kerberos_dc.spn')

		if not re.fullmatch(r'^[^/]+/[^/]+$', spn):
			raise RuntimeError(f'Invalid Kerberos SPN: {spn}')

		if keytab is not None:
			os.environ['KRB5_KTNAME'] = f'FILE:{keytab}'

		self.cache = None
		self.realm = realm
		self.spn = spn
		self.upn_allowlist = upn_allowlist

		if cache is not None:
			self.cache = util.dynamic_instantiate_class_from_opts(cache, expand={"${application}": self})

	def __str__(self):
		return f"{self.__class__.__name__}()"

	def get_domain_realm(self, path_info, environ):
		return self._calc_realm_from_path_provider(path_info, environ)

	def require_authentication(self, realm, environ):
		return True

	def supports_http_digest_auth(self):
		return False  # Kerberos auth requires password in plaintext

	def basic_auth_user(self, realm, user_name, password, environ):
		if isinstance(self.upn_allowlist, list) and not user_name in self.upn_allowlist: return False
		if isinstance(self.cache, KerberosAuthCacheBase) and self.cache.check(user_name, password) is True: return True
		s = self.__server_ctx()
		try:
			# allow ASCII only for password, do not allow any non-ASCII,
			# assuming encoding=UTF-8 is not viable as 
			# Kerberos RFC does not mandates any encoding for password
			c = self.__client_ctx(user_name, bytes(password, encoding='ascii'))
			r = self.__negotiate(s, c)
		except gssapi.raw.misc.GSSError as e:  # kerberos auth failed
			return False
		except UnicodeEncodeError as e:  # invalid (non-ascii) password
			return False
		except Exception as e:
			raise e
		if isinstance(self.cache, KerberosAuthCacheBase) and r is True: self.cache.save(user_name, password)
		return r

	def __server_ctx(self) -> gssapi.SecurityContext:
		server_name = gssapi.Name(f'{self.spn}@{self.realm}')
		server_creds = gssapi.Credentials(usage='accept', name=server_name)
		return gssapi.SecurityContext(usage='accept', creds=server_creds)

	def __client_ctx(self, username: str, password: bytes) -> gssapi.SecurityContext:
		server_name = gssapi.Name(f'{self.spn}@{self.realm}')
		client_name = gssapi.Name(f'{username}@{self.realm}')
		client_creds = gssapi.raw.acquire_cred_with_password(client_name, password).creds
		return gssapi.SecurityContext(usage='initiate', name=server_name, creds=client_creds)

	def __negotiate(self, server_ctx: gssapi.SecurityContext, client_ctx: gssapi.SecurityContext) -> bool:
		client_token = None
		server_token = None
		while True:
			client_token = client_ctx.step(server_token)
			if client_ctx.complete and server_ctx.complete: return True
			if not client_token: break
			server_token = server_ctx.step(client_token)
			if client_ctx.complete and server_ctx.complete: return True
			if not server_token: break
		return False
