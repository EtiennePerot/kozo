import struct
import time
import itertools
from kozo import kozoSystem, Node
from .log import *

_serializers = []

class _Serializer(object):
	def pack(self, data):
		raise NotImplementedError()
	def unpack(self, data):
		raise NotImplementedError()

class _NullSerializer(_Serializer):
	def pack(self, data):
		return None
	def unpack(self, data):
		return None

try:
	import msgpack as _msgpack
	class _MsgpackSerializer(_Serializer):
		def pack(self, data):
			if len(repr(data)) > 32768:
				return None
			return _msgpack.packb(data)
		def unpack(self, data):
			return _msgpack.unpackb(data, use_list=False)
	_serializers.append(_MsgpackSerializer())
except ImportError:
	warn('Cannot import msgpack. msgpack serializer will not be available.')
	_serializers.append(_NullSerializer())

import cPickle as _cPickle
class _CPickleSerializer(_Serializer):
	def pack(self, data):
		return _cPickle.dumps(data)
	def unpack(self, data):
		return _cPickle.loads(data)
_serializers.append(_CPickleSerializer())

import pickle as _pickle
class _PickleSerializer(_Serializer):
	def pack(self, data):
		return _pickle.dumps(data)
	def unpack(self, data):
		return _pickle.loads(data)
_serializers.append(_PickleSerializer())

_definedMessageClasses = {}
class _MessageMetaclass(type):
	def __new__(*args, **kwargs):
		builtClass = type.__new__(*args, **kwargs)
		builtClass._kozoMessage_init = builtClass.__init__
		def newInit(self, *args, **kwargs):
			if '_kozoMessage_payload' in kwargs:
				self._content = kwargs['_kozoMessage_payload']
				self._size = None
			else:
				builtClass._kozoMessage_init(self, *args, **kwargs)
		builtClass.__init__ = newInit
		if builtClass.__name__ in _definedMessageClasses:
			raise KozoError('Cannot define two message classes with the same name.')
		_definedMessageClasses[builtClass.__name__] = builtClass
		return builtClass

def decodeMessage(bytes):
	indexBytes = struct.calcsize('I')
	serializerIndex = struct.unpack('I', bytes[:indexBytes])[0]
	try:
		serializer = _serializers[serializerIndex]
	except IndexError:
		warn('Received payload with unknown serializer index:', serializerIndex)
		return None
	payload = serializer.unpack(bytes[indexBytes:])
	if payload is None:
		warn('Cannot deserialize payload with serializer', serializer, ':', repr(bytes[indexBytes:]))
		return None
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
		self._size = None
	def getRecipientNodes(self):
		return kozoSystem().getNodes()
	def toBytes(self):
		message = (self.__class__.__name__, self._content)
		for i, serializer in enumerate(_serializers):
			serialized = serializer.pack(message)
			if serialized is not None:
				return struct.pack('I', i) + serialized
		return None
	def getSize(self):
		if self._size is None:
			toBytes = self.toBytes()
			if toBytes is not None:
				self._size = len(toBytes)
		return self._size
	def getType(self):
		return self._content['type']
	def getTimestamp(self):
		return self._content['timestamp']
	def getSender(self):
		return kozoSystem().getNodeByName(self._content['sender'])
	def getData(self):
		return self._content['data']

class Heartbeat(_Message):
	def __init__(self, toNode):
		_Message.__init__(self, 'heartbeat', None)
		self._toNode = toNode
	def getRecipientNodes(self):
		return [self._toNode]

class RoleMessage(_Message):
	def __init__(self, fromRole, type, channel=None, data={}):
		_Message.__init__(self, 'role', {
			'roleMessageType': type,
			'fromRole': fromRole.getName(),
			'channel': channel,
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
	def getChannel(self):
		return self.getData()['channel']
	def getRoleData(self):
		return self.getData()['roleData']

class Event(RoleMessage):
	def __init__(self, fromRole, eventType, channel=None, eventData={}):
		RoleMessage.__init__(self, fromRole, 'event', channel=channel, data={
			'eventType': eventType,
			'eventData': eventData
		})
	def getEventType(self):
		return self.getRoleData()['eventType']
	def getEventData(self):
		return self.getRoleData()['eventData']

class Order(RoleMessage):
	def __init__(self, fromRole, orderType, channel=None, orderData={}):
		RoleMessage.__init__(self, fromRole, 'order', channel=channel, data={
			'orderType': orderType,
			'orderData': orderData
		})
	def getOrderType(self):
		return self.getRoleData()['orderType']
	def getOrderData(self):
		return self.getRoleData()['orderData']

class Log(RoleMessage):
	def __init__(self, fromRole, *message):
		RoleMessage.__init__(self, fromRole, 'log', data={
			'message': ' '.join(map(str, message))
		})
	def getMessage(self):
		return self.getRoleData()['message']
