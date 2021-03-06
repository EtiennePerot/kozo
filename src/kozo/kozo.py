class KozoError(RuntimeError):
	pass

class KozoStopError(KozoError):
	pass

from .confsys import *

class Role(Configurable):
	def __init__(self, name, nodeName, providedConfig):
		roleConfig = self.__class__._roleConfig.copy()
		for key, default in self.__class__._roleConfig.iteritems():
			if default is NODE_NAME:
				roleConfig[key] = nodeName
			elif default is ROLE_NAME:
				roleConfig[key] = name
			elif default is ROLENODE_NAME:
				roleConfig[key] = '%s@%s' % (name, nodeName)
		Configurable.__init__(self, 'Role<' + name + '>', providedConfig, roleConfig, self.__class__._roleConfigRequired)
		self._name = name
		self._node = None
		self._controllingThread = None
		self._storage = (False, None) # (Initialized bool, RoleMessage instance)
	def getName(self):
		return self._name
	def getNode(self):
		return self._node
	def _setNode(self, node):
		self._node = node
	def setControllingThread(self, controllingThread):
		self._controllingThread = controllingThread
	def isInterestedIn(self, message):
		return False
	def getRateControl(self):
		return None
	def getMessageRateControlOverride(self):
		return None
	def sleep(self, seconds):
		if self._controllingThread is not None:
			self._controllingThread.sleep(seconds)
	def getMessageQueueLength(self):
		if self['messageQueueLength'] is not None:
			return self['messageQueueLength']
		return 8
	def getMessageQueueSize(self):
		if self['messageQueueSize'] is not None:
			return self['messageQueueSize']
		return 4 * 1024 * 1024 # 4 megabytes
	def getMessage(self, timeout=None):
		"""Get a message from our queue.

		Arguments:
			timeout: Timeout when waiting for a message. 0 for non-blocking, None for default timeout value. Custom values cannot surpass the default.

		Returns:
			A RoleMessage object, or None if we didn't receive anything in time.
		"""
		if self._controllingThread is not None:
			return self._controllingThread.getMessage(timeout)
	def sendEvent(self, eventType, channel=None, data={}):
		from .messages import Event
		if self._controllingThread is not None:
			self._controllingThread.sendMessage(Event(self, eventType, channel, data))
	def sendOrder(self, orderType, channel=None, data={}):
		from .messages import Order
		if self._controllingThread is not None:
			self._controllingThread.sendMessage(Order(self, orderType, channel, data))
	def sendLog(self, *logMessage):
		from .messages import Log
		if self._controllingThread is not None:
			self._controllingThread.sendMessage(Log(self, *logMessage))
	def info(self, *msg, **kwargs):
		from .log import infoRole
		return infoRole(self, *msg, **kwargs)
	def warn(self, *msg, **kwargs):
		from .log import warnRole
		return warnRole(self, *msg, **kwargs)
	def error(self, *msg, **kwargs):
		from .log import errorRole
		return errorRole(self, *msg, **kwargs)
	def init(self):
		pass
	def localInit(self):
		pass
	def getStorage(self):
		from .messages import RoleStorage
		if not self._storage[0]:
			self._storage = (True, RoleStorage.load(self))
		return self._storage[1].getRoleStorage()
	def setStorage(self, storage):
		from .messages import RoleStorage
		roleStorage = RoleStorage(self, storage)
		roleStorage.save()
		self._storage = (True, roleStorage)
	def run(self):
		raise NotImplementedError()
	def kill(self):
		if self._controllingThread is not None:
			self._controllingThread.kill()
	def __hash__(self):
		return hash((self._node, self._name))
	def __eq__(self, other):
		return isinstance(other, Role) and other._node == self._node and other._name == self._name

class Transport(Configurable):
	Priority_BEST = 4
	Priority_GOOD = 3
	Priority_MEH = 2
	Priority_BAD = 1
	Priority_WORST = 0
	def __init__(self, name, nodeName, providedConfig):
		transportConfig = self.__class__._transportConfig.copy()
		for key, default in self.__class__._transportConfig.iteritems():
			if default is NODE_NAME:
				transportConfig[key] = nodeName
			elif default is TRANSPORT_NAME:
				transportConfig[key] = name
			elif default is TRANSPORTNODE_NAME:
				transportConfig[key] = '%s@%s' % (name, nodeName)
		Configurable.__init__(self, 'Transport<' + name + '>', providedConfig, transportConfig, self.__class__._transportConfigRequired)
		self._name = name
		self._node = None
	def getNode(self):
		return self._node
	def _setNode(self, node):
		self._node = node
	def isSelf(self):
		return self.getNode().isSelf()
	def getPriority(self):
		return Transport.Priority_MEH
	def init(self):
		pass
	def localInit(self):
		pass
	def bind(self):
		pass
	def canAccept(self):
		return True
	def accept(self):
		raise NotImplementedError()
	def canConnect(self, otherTransport):
		return self.getNode() is not otherTransport.getNode() and self.__class__ is otherTransport.__class__
	def connect(self, otherTransport):
		raise NotImplementedError()
	def __str__(self):
		return self.__class__.__name__ + '<' + self._node.getName() + ':' + self._name + '>'
	def __hash__(self):
		return hash((self._node, self._name))
	def __eq__(self, other):
		return isinstance(other, Transport) and other._node == self._node and other._name == self._name

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
	def wrapSend(self, bytes):
		if self._alive:
			return self.send(bytes)
	def send(self, bytes):
		raise NotImplementedError()
	def wrapReceive(self, bytes, timeout):
		if self._alive:
			return self.receive(bytes, timeout)
	def receive(self, bytes, timeout):
		raise NotImplementedError()
	def __str__(self):
		return 'Channel<' + self._fromNode.getName() + ' to ' + self._toNode.getName() + '>'

class Node(Configurable):
	CONNECTPOLICY_CONSTANT = 'constant'
	CONNECTPOLICY_ONDEMAND = 'ondemand'
	CONNECTPOLICY_NEVER = 'never'
	CONNECTPOLICIES = (CONNECTPOLICY_CONSTANT, CONNECTPOLICY_ONDEMAND, CONNECTPOLICY_NEVER)
	def __init__(self, name, providedConfig):
		Configurable.__init__(self, 'Node<' + name + '>', providedConfig, {
			'selfToOthersConnectPolicy': self.CONNECTPOLICY_CONSTANT,
			'othersToSelfConnectPolicy': self.CONNECTPOLICY_CONSTANT,
			'roleStorage': None,
			'overrideMainConfiguration': {},
		}, ['publicKey', 'privateKey', 'roles', 'transports'])
		self._name = name
		self._roles = []
		self._transports = []
		self._publicKey = self['publicKey'].split(' ', 3)
		if len(self._publicKey) < 2:
			raise KozoError('Invalid public key on node', self.getName())
		if self._publicKey[0] != 'ssh-rsa':
			raise KozoError('Only RSA keys are supported; node', self.getName(), 'has a non-RSA or invalid key.')
		self._privateKeyPath = self['privateKey']
		self._roleStorage = self['roleStorage']
		self._selfToOthersConnectPolicy = self['selfToOthersConnectPolicy']
		if self._selfToOthersConnectPolicy not in self.CONNECTPOLICIES:
			raise KozoError('Invalid selfToOthersConnectPolicy on node', self.getName())
		self._othersToSelfConnectPolicy = self['othersToSelfConnectPolicy']
		if self._othersToSelfConnectPolicy not in self.CONNECTPOLICIES:
			raise KozoError('Invalid othersToSelfConnectPolicy on node', self.getName())
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
	def getRoleByName(self, name):
		for role in self._roles:
			if role.getName() == name:
				return role
		return None
	def getRoleStorage(self):
		return self._roleStorage
	def getPublicKey(self):
		return self._publicKey
	def getPrivateKeyPath(self):
		return self._privateKeyPath
	def getSelfToOthersConnectPolicy(self):
		return self._selfToOthersConnectPolicy
	def getOthersToSelfConnectPolicy(self):
		return self._othersToSelfConnectPolicy
	def addTransport(self, transport):
		transport._setNode(self)
		self._transports.append(transport)
	def getTransports(self):
		return self._transports

_kozoRuntime = None
def kozoRuntime():
	global _kozoRuntime
	if _kozoRuntime is None:
		from .runtime import KozoRuntime
		_kozoRuntime = KozoRuntime()
	return _kozoRuntime

class KozoSystem(object):
	def __init__(self):
		self._nodes = []
		self._nodesByName = {}
		self._selfNode = None
	def addNode(self, node):
		if node.getName() not in self._nodesByName:
			self._nodes.append(node)
			self._nodesByName[node.getName()] = node
	def getNodes(self):
		return self._nodes
	def getNodeByName(self, name):
		return self._nodesByName.get(name, None)
	def getNodesBy(self, func):
		return filter(func, self.getNodes())
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
			kozoRuntime().join(verbose=False)
		except KeyboardInterrupt:
			kozoRuntime().kill()
			kozoRuntime().join(verbose=True)

_kozoSystem = None
def kozoSystem():
	global _kozoSystem
	if _kozoSystem is None:
		_kozoSystem = KozoSystem()
	return _kozoSystem

_kozoConfig = None
_kozoConfigDefault = {
	'heartbeat': 10,
	'connectionRetry': 60,
	'outgoingQueueLength': 128,
	'outgoingQueueSize': 4 * 1024 * 1024, # 4 megabytes
	'maxBufferReadSize': 64 * 1024, # 64 kilobytes
	'cipher': 'aes256-ctr',
	'hmac': 'hmac-sha1',
	'rolePath': '',
	'transportPath': '',
	'importPath': '',
}
def kozoConfig(key):
	return _kozoConfig[key]

def kozo(config, selfNode): # System entry point
	global _kozoConfig
	if _kozoConfig is not None:
		raise KozoError('Can only run one system.')
	from .roles import kozoRole
	from .transports import kozoTransport
	from .log import info
	info('Kozo system is being defined.')
	_kozoConfig = Config('main', config, _kozoConfigDefault, ['system'])
	for nodeName, nodeConf in config['system'].items():
		node = Node(nodeName, nodeConf)
	kozoSystem()._setSelfNode(selfNode)
	if kozoSystem().getSelfNode() is None:
		raise KozoError('Unknown node name:', selfNode)
	_kozoConfig.overrideWith(kozoSystem().getSelfNode()['overrideMainConfiguration'])
	for nodeName, nodeConf in config['system'].items():
		node = kozoSystem().getNodeByName(nodeName)
		for roleName, roleConf in nodeConf['roles'].items():
			if roleConf is None:
				roleConf = {}
			if 'type' in roleConf:
				roleClass = kozoRole(roleConf['type'], roleName, nodeName)
			else:
				roleClass = kozoRole(roleName, roleName, nodeName)
			if 'description' in roleConf:
				del roleConf['description']
			node.addRole(roleClass(roleName, nodeName, roleConf))
		for transportName, transportConf in nodeConf['transports'].items():
			if 'type' in transportConf:
				transportClass = kozoTransport(transportConf['type'], transportName, nodeName)
			else:
				transportClass = kozoTransport(transportName, transportName, nodeName)
			node.addTransport(transportClass(transportName, nodeName, transportConf))
	info('Kozo system defined. Starting runtime.')
	kozoSystem().run()
