class KozoError(RuntimeError):
	pass

class KozoStopError(KozoError):
	pass

from .confsys import *

class Role(Configurable):
	def __init__(self, name, providedConfig):
		Configurable.__init__(self, 'Role<' + name + '>', providedConfig, self.__class__._roleConfig, self.__class__._roleConfigRequired)
		self._name = name
		self._node = None
		self._controllingThread = None
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
	def sleep(self, seconds):
		if self._controllingThread is not None:
			self._controllingThread.sleep(seconds)
	def getMessageQueueSize(self):
		if self['messageQueueSize'] is not None:
			return self['messageQueueSize']
		return 8
	def getMessage(self, blocking=True):
		if self._controllingThread is not None:
			return self._controllingThread.getMessage(blocking)
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
	def run(self):
		raise NotImplementedError()
	def kill(self):
		if self._controllingThread is not None:
			self._controllingThread.kill()

class Transport(Configurable):
	Priority_BEST = 4
	Priority_GOOD = 3
	Priority_MEH = 2
	Priority_BAD = 1
	Priority_WORST = 0
	def __init__(self, name, providedConfig):
		Configurable.__init__(self, 'Transport<' + name + '>', providedConfig, self.__class__._transportConfig, self.__class__._transportConfigRequired)
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
	def bind(self):
		pass
	def accept(self):
		raise NotImplementedError()
	def canConnect(self, otherTransport):
		return self.getNode() is not otherTransport.getNode() and self.__class__ is otherTransport.__class__
	def connect(self, otherTransport):
		raise NotImplementedError()
	def __str__(self):
		return self.__class__.__name__ + '<' + self._node.getName() + ':' + self._name + '>'

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
	def __init__(self, name, providedConfig):
		Configurable.__init__(self, 'Node<' + name + '>', providedConfig, {}, ['publicKey', 'privateKey', 'roles', 'transports'])
		self._name = name
		self._roles = []
		self._transports = []
		self._publicKey = self['publicKey'].split(' ', 3)
		if len(self._publicKey) < 2:
			raise KozoError('Invalid public key on node', self.getName())
		self._privateKeyPath = self['privateKey']
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
	def getPublicKey(self):
		return self._publicKey
	def getPrivateKeyPath(self):
		return self._privateKeyPath
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
	'outgoingQueueSize': 128,
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
	_kozoConfig = Config('main', config, _kozoConfigDefault)
	for nodeName, nodeConf in config['system'].items():
		node = Node(nodeName, nodeConf)
		for roleName, roleConf in nodeConf['roles'].items():
			if roleConf is None:
				roleConf = {}
			if 'type' in roleConf:
				roleClass = kozoRole(roleConf['type'], roleName, nodeName)
			else:
				roleClass = kozoRole(roleName, roleName, nodeName)
			if 'description' in roleConf:
				del roleConf['description']
			node.addRole(roleClass(roleName, roleConf))
		for transportName, transportConf in nodeConf['transports'].items():
			if 'type' in transportConf:
				transportClass = kozoTransport(transportConf['type'], transportName, nodeName)
			else:
				transportClass = kozoTransport(transportName, transportName, nodeName)
			node.addTransport(transportClass(transportName, transportConf))
	kozoSystem()._setSelfNode(selfNode)
	info('Kozo system defined. Starting runtime.')
	kozoSystem().run()
