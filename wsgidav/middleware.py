class BaseMiddleware(object):
	def __init__(self, application, config):
		pass

	def __call__(self, environ, start_response):
		pass

	@staticmethod
	def isSuitable(config):
		return True