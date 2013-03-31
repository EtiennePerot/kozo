import time
from kozo import Role

class Timer(Role):
	def run(self):
		self.sleep(self['tick'])
		if self['message']:
			message = (self['message'], time.strftime('%H:%M:%S'))
			self.sendEvent('tick', message)
			self.info('Sent message:', message)

roleInfo = {
	'format': '1.0',
	'class': Timer,
	'author': 'Etienne Perot',
	'version': '1.0',
	'description': 'Sends a ping event every so often.',
	'config': {
		'tick': {
			'default': 1,
			'description': 'Interval between pings.'
		},
		'message': {
			'default': 'Ping!',
			'description': 'Optional message to show in local log at every tick.'
		}
	}
}