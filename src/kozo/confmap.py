class Config(object):
	def __init__(self, context, providedConfig, defaultConfig={}, requiredKeys=[]):
		if providedConfig is None:
			providedConfig = {}
		for key in requiredKeys:
			if key not in providedConfig:
				from kozo import KozoError
				raise KozoError('Must provide a value for', context, '->', key)
		self._provided = providedConfig
		self._default = defaultConfig
		for key in self._default.keys():
			if type(self._default[key]) is type({}):
				self._provided[key] = Config(self._provided.get(key, {}), self._default[key])
	def __getitem__(self, key):
		return self._provided.get(key, self._default.get(key, None))
	def __setitem__(self, key, value):
		self._provided[key] = value
