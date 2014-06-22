import socket
from kozo import Role

MESSAGE_TYPES = {
	'event': lambda x: x.sendEvent,
	'order': lambda x: x.sendOrder,
	'log': lambda x: x.sendLog
}

class MessageInjector(Role):
	def localInit(self):
		self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._socket.bind((self['bindAddress'], self['bindPort']))
		self._socket.listen(1)
	def getRateControl(self):
		return self['tick']
	def _debugMessage(self, *message, **kwargs):
		exception = kwargs.get('exception')
		if self['log']:
			if exception is None:
				self.sendLog(*message)
			else:
				self.sendLog(*(message + (exception,)))
	def run(self):
		connection, address = self._socket.accept()
		self._debugMessage('Got connection from', address)
		try:
			message = ''
			while True:
				while '\n' not in message:
					message += connection.recv(1024)
				messages = message.split('\n')
				actualMessages, message = messages[:-1], messages[-1]
				for m in actualMessages:
					try:
						evaled = eval(m)
					except Exception as e:
						self._debugMessage('Cannot evaluate message', m, ': got exception', e)
						continue
					if type(evaled) is not tuple:
						self._debugMessage('Expected tuple type, not', type(evaled))
					elif evaled[0].lower() not in MESSAGE_TYPES:
						self._debugMessage('Expected first value to be one of', MESSAGE_TYPES.keys(), 'not', evaled[0])
					elif evaled[0].lower() == 'log':
						if len(evaled) != 2:
							self._debugMessage('Expected tuple of length 2 for log messages, not', len(evaled))
						else:
							logMessage = evaled[1]
							if type(logMessage) in (str, unicode):
								logMessage = (logMessage,)
							self._debugMessage('Sending log message', logMessage)
							self.sendLog(*logMessage)
					elif len(evaled) not in (3, 4):
						self._debugMessage('Expected 3 or 4 tuple values, not', len(evaled))
					elif type(evaled[1]) not in (str, unicode):
						self._debugMessage('Expected type to be string, not', type(evaled[1]))
					elif len(evaled) == 3:
						self._debugMessage('Sending', evaled[0], 'with type', evaled[1], 'on the None channel with content', evaled[2])
						MESSAGE_TYPES[evaled[0].lower()](self)(evaled[1], data=evaled[2])
					elif type(evaled[2]) not in (str, unicode):
						self._debugMessage('Expected channel to be string, not', type(evaled[2]))
					else:
						self._debugMessage('Sending', evaled[0], 'with type', evaled[1], 'on channel', evaled[2], 'with content', evaled[3])
						MESSAGE_TYPES[evaled[0].lower()](self)(evaled[1], channel=evaled[2], data=evaled[3])
				if not message:
					try:
						connection.close()
					except:
						pass
					break
		except Exception as e2:
			self._debugMessage('Exception during main loop:', exception=e2)
		finally:
			try:
				connection.close()
			except:
				pass

roleInfo = {
	'format': '1.0',
	'class': MessageInjector,
	'author': 'Etienne Perot',
	'version': '1.0',
	'description': 'Binds to a TCP port and listens for messages to send on it (one per line). Injects them into the network. Useful for debugging.',
	'config': {
		'bindAddress': {
			'default': 'localhost',
			'description': 'Address to bind to.'
		},
		'bindPort': {
			'default': 7050,
			'description': 'TCP port to bind to.'
		},
		'log': {
			'default': True,
			'description': 'Log sent messages.'
		}
	}
}