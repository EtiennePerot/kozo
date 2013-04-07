import time
import itertools
from kozo import kozoSystem
from .log import *

try:
	import msgpack as _msgpack
	_pack = _msgpack.packb
	_unpack = lambda x: _msgpack.unpackb(x, use_list=False)
	info('Using msgpack as serializer. Make sure this is the case for all other nodes.')
except ImportError:
	import cPickle
	_pack = cPickle.dumps
	_unpack = cPickle.loads
	info('Using cPickle as serializer. Make sure this is the case for all other nodes.')

_definedMessageClasses = {}
class _MessageMetaclass(type):
	def __new__(*args, **kwargs):
		builtClass = type.__new__(*args, **kwargs)
		builtClass._kozoMessage_init = builtClass.__init__
		def newInit(self, *args, **kwargs):
			if '_kozoMessage_payload' in kwargs:
				self._content = kwargs['_kozoMessage_payload']
			else:
				builtClass._kozoMessage_init(self, *args, **kwargs)
		builtClass.__init__ = newInit
		if builtClass.__name__ in _definedMessageClasses:
			raise KozoError('Cannot define two message classes with the same name.')
		_definedMessageClasses[builtClass.__name__] = builtClass
		return builtClass

def decodeMessage(bytes):
	payload = _unpack(bytes)
	if type(payload) is not type(()):
		warn('Received non-tuple payload:', type(payload))
		return None
	if len(payload) != 2:
		warn('Tuple payload was not the correct size:', len(payload))
		return None
	messageClass, messageContents = payload
	if messageClass not in _definedMessageClasses:
		warn('Message class does not exist:', messageClass)
		return None
	if type(messageContents) is not type({}):
		warn('Message content is not a dictionary:', type(messageContents))
		return None
	return _definedMessageClasses[messageClass](_kozoMessage_payload=messageContents)

class _Message(object):
	__metaclass__ = _MessageMetaclass
	def __init__(self, type, data={}):
		self._content = {
			'type': type,
			'timestamp': time.time(),
			'sender': kozoSystem().getSelfNode().getName(),
			'data': data
		}
	def getRecipientNodes(self):
		return kozoSystem().getNodes()
	def toBytes(self):
		return _pack((self.__class__.__name__, self._content))
	def getType(self):
		return self._content['type']
	def getTimestamp(self):
		return self._content['timestamp']
	def getSender(self):
		return kozoSystem().getNodeByName(self._content['sender'])
	def getData(self):
		return self._content['data']

class Heartbeat(_Message):
	def __init__(self):
		_Message.__init__(self, 'heartbeat', None)
	def getRecipientNodes(self):
		return kozoSystem().getNodesBy(lambda n: not n.isSelf())

class RoleMessage(_Message):
	def __init__(self, fromRole, type, data={}):
		_Message.__init__(self, 'role', {
			'roleMessageType': type,
			'fromRole': fromRole.getName(),
			'roleData': data
		})
	def getRecipientNodes(self):
		recipients = []
		for node in _Message.getRecipientNodes(self):
			for role in node.getRoles():
				if role.isInterestedIn(self):
					recipients.append(node)
					break
		return recipients
	def getRoleType(self):
		return self.getData()['roleMessageType']
	def getSenderRole(self):
		return self.getSender().getRoleByName(self.getData()['fromRole'])
	def getSenderRoleClass(self):
		return self.getSenderRole().__class__
	def getRoleData(self):
		return self.getData()['roleData']

class Event(RoleMessage):
	def __init__(self, fromRole, eventType, eventData={}):
		RoleMessage.__init__(self, fromRole, 'event', {
			'eventType': eventType,
			'eventData': eventData
		})
	def getEventType(self):
		return self.getRoleData()['eventType']
	def getEventData(self):
		return self.getRoleData()['eventData']

class Order(RoleMessage):
	def __init__(self, fromRole, orderType, orderData={}):
		RoleMessage.__init__(self, fromRole, 'order', {
			'orderType': orderType,
			'orderData': orderData
		})
	def getOrderType(self):
		return self.getRoleData()['orderType']
	def getOrderData(self):
		return self.getRoleData()['orderData']

class Log(RoleMessage):
	def __init__(self, fromRole, *message):
		RoleMessage.__init__(self, fromRole, 'log', {
			'message': ' '.join(map(str, message))
		})
	def getMessage(self):
		return self.getRoleData()['message']
