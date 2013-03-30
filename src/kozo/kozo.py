class KozoError(RuntimeError):
	pass

class Configurable(object):
	def __init__(self, context, providedConfig, defaultConfig={}, requiredKeys=[]):
		from .confmap import Config
		self._config = Config(context, providedConfig, defaultConfig, requiredKeys)
	def __getitem__(self, key):
		return self._config[key]
	def __setitem__(self, key, value):
		self._config[key] = value

class Role(Configurable):
	def __init__(self, name, providedConfig, defaultConfig={}, requiredKeys=[]):
		Configurable.__init__(self, 'Role<' + name + '>', providedConfig, defaultConfig, requiredKeys)
		self._name = name
		self._node = None
		self._alive = True
	def getNode(self):
		return self._node
	def _setNode(self, node):
		self._node = node
	def isAlive(self):
		return self._alive
	def emit(self, message):
		pass # FIXME
	def run(self):
		raise NotImplementedError()
	def kill(self):
		self._alive = False
	def __str__(self):
		return 'Role<' + self._name + '>'

class Transport(Configurable):
	def __init__(self, name, providedConfig, defaultConfig={}, requiredKeys=[]):
		Configurable.__init__(self, 'Transport<' + name + '>', providedConfig, defaultConfig, requiredKeys)
		self._name = name
		self._node = None
	def getNode(self):
		return self._node
	def _setNode(self, node):
		self._node = node
	def isSelf(self):
		return self.getNode().isSelf()
	def getPriority(self):
		return 0
	def bind(self):
		pass
	def accept(self):
		raise NotImplementedError()
	def canConnect(self, otherTransport):
		return self.getNode() is not otherTransport.getNode() and self.__class__ is otherTransport.__class__
	def connect(self, otherTransport):
		raise NotImplementedError()
	def __str__(self):
		return 'Transport<' + self._node.getName() + ':' + self._name + '>'

class Channel(object):
	def __init__(self, fromNode, toNode):
		self._fromNode = fromNode
		self._toNode = toNode
		self._alive = True
	def getFromNode(self):
		return self._fromNode
	def getToNode(self):
		return self._toNode
	def isAlive(self):
		return self._alive
	def kill(self):
		self._alive = False
	def wrapSend(self, message):
		if self._alive:
			return self.send(message)
	def send(self, message):
		raise NotImplementedError()
	def wrapReceive(self, bytes, timeout):
		if self._alive:
			return self.receive(bytes, timeout)
	def receive(self, bytes, timeout):
		raise NotImplementedError()
	def __str__(self):
		return 'Channel<' + self._fromNode.getName() + ' to ' + self._toNode.getName() + '>'

class Node(object):
	def __init__(self, name):
		self._name = name
		self._roles = []
		self._transports = []
		kozoSystem().addNode(self)
	def getName(self):
		return self._name
	def isSelf(self):
		return kozoSystem().getSelfNode() is self
	def addRole(self, role):
		role._setNode(self)
		self._roles.append(role)
	def getRoles(self):
		return self._roles
	def _kill(self):
		for role in self._roles:
			role.kill()
	def addTransport(self, transport):
		transport._setNode(self)
		self._transports.append(transport)
	def getTransports(self):
		return self._transports
	def __str__(self):
		return 'Node<' + self._name + '>'

class _NodeSet(object):
	def __init__(self):
		self._nodes = []
		self._nodesByName = {}
	def addNode(self, node):
		if node.getName() not in self._nodesByName:
			self._nodes.append(node)
			self._nodesByName[node.getName()] = node
	def getNodes(self):
		return self._nodes
	def getNodeByName(self, name):
		return self._nodesByName.get(name, None)
	def getNodesByTransport(self, transportLambda):
		nodes = []
		for node in self._nodes:
			for transport in node.getTransports():
				if transportLambda(transport):
					nodes.append(node)
					break
		return nodes

_kozoRuntime = None
def kozoRuntime():
	global _kozoRuntime
	if _kozoRuntime is None:
		from .runtime import KozoRuntime
		_kozoRuntime = KozoRuntime()
	return _kozoRuntime

class KozoSystem(_NodeSet):
	def __init__(self):
		_NodeSet.__init__(self)
		self._selfNode = None
	def getSelfNode(self):
		return self._selfNode
	def kill(self):
		for node in self.getNodes():
			node._kill()
	def _setSelfNode(self, node):
		if type(node) is type(''):
			node = self.getNodeByName(node)
		self._selfNode = node
	def run(self):
		if self._selfNode is None:
			raise KozoError('Did not set self node.')
		kozoRuntime().start()
		try:
			kozoRuntime().join()
		except KeyboardInterrupt:
			self.kill()
			kozoRuntime().join()

_kozoSystem = None
def kozoSystem():
	global _kozoSystem
	if _kozoSystem is None:
		_kozoSystem = KozoSystem()
	return _kozoSystem

def kozo(config, selfNode): # System entry point
	from .roles import kozoRole
	from .transports import kozoTransport
	for nodeName, nodeConf in config['system'].items():
		node = Node(nodeName)
		for roleName, roleConf in nodeConf['roles'].items():
			if 'type' in roleConf:
				roleClass = kozoRole(roleConf['type'])
			else:
				roleClass = kozoRole(roleName)
			node.addRole(roleClass(roleName, roleConf))
		for transportName, transportConf in nodeConf['transports'].items():
			if 'type' in transportConf:
				transportClass = kozoTransport(transportConf['type'])
			else:
				transportClass = kozoTransport(transportName)
			node.addTransport(transportClass(transportName, transportConf))
	kozoSystem()._setSelfNode(selfNode)
	kozoSystem().run()
