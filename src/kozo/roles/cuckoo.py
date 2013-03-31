import time
from kozo import Role
from kozo.messages import Event

class Cuckoo(Role):
	def isInterestedIn(self, message):
		return isinstance(message, Event) and message.getEventType() == 'tick' and (self['timer'] == '*' or message.getSenderRole().getName() == self['timer'])
	def run(self):
		message = self.getMessage()
		if message is not None:
			self.info('Received message', message.getEventData(), 'from timer', message.getSenderRole())

roleInfo = {
	'format': '1.0',
	'class': Cuckoo,
	'author': 'Etienne Perot',
	'version': '1.0',
	'description': 'Responds to pings sent by a certain Timer.',
	'config': {
		'timer': {
			'default': '*',
			'description': 'Name of the timer to respond to, or "*" to respond to all timers'
		},
		'message': {
			'default': 'Cuckoo!',
			'description': 'Message to show in local log at every tick'
		}
	}
}