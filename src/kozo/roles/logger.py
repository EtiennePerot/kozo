import time
from kozo import Role
from kozo.messages import Log

class Logger(Role):
	def isInterestedIn(self, message):
		return isinstance(message, Log)
	def init(self):
		if self['clearLog']:
			self._file = open(self['file'], 'w')
		else:
			self._file = open(self['file'], 'a')
		self._flushCounter = self['flushEvery']
		self._timePrefix = self['timePrefix']
		self._file.write(time.strftime(self._timePrefix) + 'Log started.\n')
	def run(self):
		logMessage = self.getMessage()
		if logMessage is None:
			return
		logLine = time.strftime(self._timePrefix) + '<' + logMessage.getSender().getName() + '> ' + logMessage.getMessage() + '\n'
		try:
			self._file.write(logLine)
			self.info(logLine)
			self._flushCounter -= 1
		except BaseException as e:
			self.warn('Failed to log message', logMessage, e)
		if self._flushCounter < 1:
			self._flushCounter = self['flushEvery']
			try:
				self._file.flush()
			except BaseException as e:
				self.warn('Failed to flush log file', e)

roleInfo = {
	'format': '1.0',
	'class': Logger,
	'author': 'Etienne Perot',
	'version': '1.0',
	'description': 'Logs all Log messages sent on the network to a file.',
	'config': {
		'file': {
			'default': '/var/log/kozo/kozo.log',
			'description': 'Path of the log file.'
		},
		'timePrefix': {
			'default': '[%Y-%m-%d %H:%M:%S] ',
			'description': 'Timestamp format used as prefix on each line. See http://docs.python.org/2/library/time.html#time.strftime for the available variables.'
		},
		'flushEvery': {
			'default': 1024,
			'description': 'Flush the file every n messages'
		},
		'clearLog': {
			'default': False,
			'description': 'Whether to clear any existing log when starting up'
		}
	}
}