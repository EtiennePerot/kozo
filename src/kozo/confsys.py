from .kozo import KozoError

# Constant usable as default value for role/transport configuration, autoreplaced with node name.
NODE_NAME = object()

# Constant usable as default value for role configuration, autoreplaced with role name.
ROLE_NAME = object()

# Constant usable as default value for role configuration, autoreplaced with role name@node name.
ROLENODE_NAME = object()

# Constant usable as default value for transport configuration, autoreplaced with transport name.
TRANSPORT_NAME = object()

# Constant usable as default value for transport configuration, autoreplaced with transport name@node name.
TRANSPORTNODE_NAME = object()

class Config(object):
	def __init__(self, context, providedConfig, defaultConfig={}, requiredKeys=[], consistency=True):
		if providedConfig is None:
			providedConfig = {}
		for key in requiredKeys:
			if key not in providedConfig:
				raise ValueError('Must provide a value for', context, '->', key)
		self._consistency = consistency
		self._provided = providedConfig.copy()
		self._default = defaultConfig.copy()
		self._allowedKeys = frozenset.union(frozenset(defaultConfig.keys()), frozenset(requiredKeys))
		for key in self._default.keys():
			if type(self._default[key]) is type({}):
				self._provided[key] = Config(context, self._provided.get(key, {}), self._default[key], [], False)
		self._consistencyCheck()
	def _consistencyCheck(self):
		if not self._consistency:
			return
		for key in self._provided:
			if key not in self._allowedKeys:
				raise KozoError('Unknown configuration option', key, '; Allowed:', tuple(self._allowedKeys))
	def overrideWith(self, override):
		if isinstance(override, Config):
			self._provided.update(override._provided)
		else:
			self._provided.update(override)
		self._consistencyCheck()
	def __getitem__(self, key):
		return self._provided.get(key, self._default.get(key, None))
	def __setitem__(self, key, value):
		self._provided[key] = value

class Configurable(object):
	def __init__(self, name, providedConfig, defaultConfig={}, requiredKeys=[]):
		self._name = name
		self._config = Config(name, providedConfig, defaultConfig, requiredKeys)
	def __getitem__(self, key):
		return self._config[key]
	def __setitem__(self, key, value):
		self._config[key] = value
	def __str__(self):
		return self._name
