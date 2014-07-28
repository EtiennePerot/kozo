import time
from kozo import Role
from kozo.messages import Order

class Debugger(Role):
	def localInit(self):
		import rpdb2
		self._rpdb2 = rpdb2
	def isInterestedIn(self, message):
		return isinstance(message, Order) and message.getOrderType() == 'debug' and (self['channel'] is None or message.getChannel() == self['channel'])
	def run(self):
		message = self.getMessage()
		if message is not None:
			if self['log']:
				self.sendLog('Got debug request from', message.getSenderRole(), '- Starting debug session in 5 seconds...')
				time.sleep(5)
			self._rpdb2.start_embedded_debugger(self['password'], fAllowRemote=self['allowRemote'], timeout=self['debugTimeout'])
			if self['log']:
				self.sendLog('Debug session ended or timeout of', self['debugTimeout'], 'seconds reached.')

roleInfo = {
	'format': '1.0',
	'class': Debugger,
	'author': 'Etienne Perot',
	'version': '1.0',
	'description': 'Starts an rpdb2 remote debugger upon receiving a message. Note: Only useful while debugging. Do NOT leave this role lingering in a node when done.',
	'config': {
		'password': {
			'default': 'kozo',
			'description': 'Debugger password.'
		},
		'allowRemote': {
			'default': True,
			'description': 'Whether or not to allow debugging from remote machines.'
		},
		'debugTimeout': {
			'default': 600,
			'description': 'How many seconds to wait until a debugging session is attached before giving up.'
		},
		'channel': {
			'default': None,
			'description': 'Name of the debug order channel to subscribe to. If not provided, all debug orders will start a debugging session.'
		},
		'log': {
			'default': True,
			'description': 'Log debug attempts.'
		}
	}
}
