from passlib.apache import HtdigestFile

from wsgidav import util
from wsgidav.dc.base_dc import BaseDomainController
from wsgidav.dir_browser._dir_browser import ASSET_SHARE


class HtdigestDomainController(BaseDomainController):
	def __init__(self, wsgidav_app, config):
		super().__init__(wsgidav_app, config)

		dc_conf = util.get_dict_value(config, "htdigest_dc", as_dict=True)
		file_path = dc_conf.get("htdigest_file")

		if file_path is None:
			raise RuntimeError("Missing option: htdigest_dc.htdigest_file")

		self.htdigest = HtdigestFile(file_path)

	def __str__(self):
		return f"{self.__class__.__name__}()"

	def get_domain_realm(self, path_info, environ):
		realm = self._calc_realm_from_path_provider(path_info, environ)
		return realm

	def require_authentication(self, realm, environ):
		if realm == ASSET_SHARE:
			return False
		return True

	def basic_auth_user(self, realm, user_name, password, environ):
		return self.htdigest.check_password(user_name, realm, password)

	def supports_http_digest_auth(self):
		return True

	def digest_auth_user(self, realm, user_name, environ):
		return self.htdigest.get_hash(user_name, realm)
