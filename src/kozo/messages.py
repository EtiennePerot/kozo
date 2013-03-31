import cPickle
import time
import itertools
from kozo import kozoSystem
from .log import *

def decodeMessage(bytes):
	payload = cPickle.loads(bytes)
	if not isinstance(payload, _Message):
		warn('Received invalid payload.')
		return None
	return payload

class _Message(object):
	def __init__(self, type, data={}):
		self._content = {
			'type': type,
			'timestamp': time.time(),
			'sender': kozoSystem().getSelfNode().getName(),
			'data': data
		}
	def __getstate__(self):
		return self._content
	def __setstate__(self, state):
		self._content = state
	def getRecipientNodes(self):
		return kozoSystem().getNodes()
	def toBytes(self):
		return cPickle.dumps(self, cPickle.HIGHEST_PROTOCOL)
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
