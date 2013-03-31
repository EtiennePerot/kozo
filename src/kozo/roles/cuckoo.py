import time
from kozo import Role
from .timer import Timer
from kozo.messages import Event

_defaultConfig = {
	'timer': '*',
	'message': 'Cuckoo!'
}

class Cuckoo(Role):
	"""
	Responds to pings sent by a certain Timer.
	Config variables:
	  - timer: Name of the timer to respond to, or "*" to respond to all timers
	  - message: Optional message to show in local log at every tick
	"""
	def __init__(self, name, config):
		Role.__init__(self, name, config, _defaultConfig)
	def isInterestedIn(self, message):
		return isinstance(message, Event) and message.getEventType() == 'tick' and (self['timer'] == '*' or message.getSenderRole().getName() == self['timer'])
	def run(self):
		message = self.getMessage()
		self.info('Received message', message.getEventData(), 'from timer', message.getSenderRole())
