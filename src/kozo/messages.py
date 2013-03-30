import time
import itertools

class _Message(object):
	_sequenceNumberCounter = itertools.count()
	def __init__(self, type, fromRole, toRole='*', data={}):
		self._content = {
			'fromRole': fromRole,
			'toRole': toRole,
			'type': type,
			'timestamp': time.time(),
			'sequenceNumber': _sequenceNumberCounter.next(),
			'data': content
		}
	def send(self):
		pass

class Event(_Message):
	def __init__(self, fromRole, toRole, eventType, eventData={}):
		_Message.__init__(self, 'event', fromRole, toRole, {
			'eventType': eventType,
			'eventData': eventData
		})

class Order(_Message):
	def __init__(self, fromRole, toRole, orderType, orderData={}):
		_Message.__init__(self, 'order', fromRole, toRole, {
			'orderType': orderType,
			'orderData': orderData
		})

class Log(_Message):
	def __init__(fromRole, toRole='logger', message=''):
		_Message.__init__(self, 'log', fromRole, toRole, {
			'message': message
		})

class Heartbeat(_Message):
	def __init__(fromRole, toRole='heartbeat'):
		_Message.__init__(self, 'heartbeat', fromRole, toRole, None)
