from kozo import Role
from kozo.helpers import rpio
rpio = rpio()

class MotionDetector(Role):
	def localInit(self):
		self._hadMotion = False
	def getRateControl(self):
		return self['period']
	def run(self):
		hasMotion = rpio.input(self['pin'])
		self.sendEvent('motion detection', data=hasMotion)
		if self['log'] and self._hadMotion != hasMotion:
			if hasMotion:
				self.sendLog('Motion detected!')
			else:
				self.sendLog('Motion stopped.')
		self._hadMotion = hasMotion

roleInfo = {
	'format': '1.0',
	'class': MotionDetector,
	'author': 'Etienne Perot',
	'version': '1.0',
	'description': 'Report movement given by a motion detector on a GPIO pin.',
	'config': {
		'pin': {
			'default': 18,
			'description': 'Pin number of the motion detector\'s output wire'
		},
		'period': {
			'default': 0.5,
			'description': 'How many seconds to wait between motion detection checks.'
		},
		'log': {
			'default': True,
			'description': 'Whether or not to send a log message every time motion starts or stops.'
		}
	}
}