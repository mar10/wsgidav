from passlib.apache import HtpasswdFile
from wsgidav import util
from wsgidav.dc.base_dc import BaseDomainController


class HtpasswdDomainController(BaseDomainController):
    def __init__(self, wsgidav_app, config):
        super().__init__(wsgidav_app, config)

        dc_conf = util.get_dict_value(config, "htpasswd_dc", as_dict=True)
        file_path = dc_conf.get("htpasswd_file")

        if file_path is None:
            raise RuntimeError("Missing option: htpasswd_dc.htpasswd_file")

        self.htpasswd = HtpasswdFile(file_path)

    def __str__(self):
        return f"{self.__class__.__name__}()"

    def get_domain_realm(self, path_info, environ):
        realm = self._calc_realm_from_path_provider(path_info, environ)
        return realm

    def require_authentication(self, realm, environ):
        return True

    def supports_http_digest_auth(self):
        return False

    def basic_auth_user(self, realm, user_name, password, environ):
        return self.htpasswd.check_password(user_name, password)
