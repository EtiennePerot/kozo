import time
from kozo import Role

_defaultConfig = {
	'tick': 1,
	'message': 'Ping!'
}

class Timer(Role):
	"""
	Sends a ping every so often.
	Config variables:
	  - tick: Interval between pings
	  - message: Optional message to show in local log at every tick
	"""
	def __init__(self, name, config):
		Role.__init__(self, name, config, _defaultConfig)
	def run(self):
		time.sleep(self['tick'])
		if self['message']:
			self.sendEvent('tick', self['message'])
