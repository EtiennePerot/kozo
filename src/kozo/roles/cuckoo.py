from kozo import Role
from kozo.messages import Event

class Cuckoo(Role):
	def localInit(self):
		self._lastCuckoo = self.getStorage()
	def isInterestedIn(self, message):
		return isinstance(message, Event) and message.getEventType() == 'tick' and (self['timer'] == '*' or message.getSenderRole().getName() == self['timer'])
	def run(self):
		message = self.getMessage()
		if message is not None:
			self.info('Received message', message.getEventData(), 'from timer', message.getSenderRole())
			if self['log']:
				self.sendLog('Cuckoo received message', message.getEventData(), '- Last cuckoo:', 'never' if self._lastCuckoo is None else self._lastCuckoo)
			self._lastCuckoo = message.getEventData()
			self.setStorage(self._lastCuckoo)

roleInfo = {
	'format': '1.0',
	'class': Cuckoo,
	'author': 'Etienne Perot',
	'version': '1.0',
	'description': 'Responds to pings sent by a certain Timer. Saves last time it cuckooed.',
	'config': {
		'timer': {
			'default': '*',
			'description': 'Name of the timer to respond to, or "*" to respond to all timers'
		},
		'log': {
			'default': True,
			'description': 'Log received messages.'
		}
	}
}