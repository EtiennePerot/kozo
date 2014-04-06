import os
import time
from kozo import Role, NODE_NAME
from kozo.messages import Log, RoleMessage

class Logger(Role):
	def localInit(self):
		if not os.path.isdir(os.path.dirname(self['file'])):
			os.makedirs(os.path.dirname(self['file']))
		self._rotate()
		self._flushCounter = self['flushEvery']
		self._rotateCounter = self['rotateEvery']
		self._timePrefix = self['timePrefix']
		self._file.write(time.strftime(self._timePrefix) + 'Log started.\n')
	def isInterestedIn(self, message):
		return isinstance(message, Log) and (self['nodeRestrict'] == '*' or message.getSenderRole().getNode().getName() == self['nodeRestrict'])
	def _rotate(self):
		for i in xrange(self['rotateMax'] - 1, 0, -1):
			logfile = self['file'] + '.' + str(i)
			nextLogfile = self['file'] + '.' + str(i + 1)
			if os.path.exists(logfile):
				os.rename(logfile, nextLogfile)
		if os.path.exists(self['file']):
			os.rename(self['file'], self['file'] + '.1')
		self._file = open(self['file'], 'w')
	def run(self):
		logMessage = self.getMessage()
		if logMessage is None:
			return
		if self['nodeRestrict'] == '*':
			sender = '%s@%s' % (logMessage.getSenderRole().getName(), logMessage.getSender().getName())
		else:
			sender = logMessage.getSenderRole().getName()
		logLine = time.strftime(self._timePrefix) + '<' + sender + '> ' + logMessage.getMessage()
		try:
			self._file.write(logLine + '\n')
			self.info(logLine)
			self._flushCounter -= 1
			self._rotateCounter -= 1
		except BaseException as e:
			self.warn('Failed to log message', logMessage, e)
		if self._flushCounter < 1:
			self._flushCounter = self['flushEvery']
			try:
				self._file.flush()
			except BaseException as e:
				self.warn('Failed to flush log file', e)
		if self._rotateCounter < 1:
			self._rotateCounter = self['rotateEvery']
			try:
				self._file.close()
				self._rotate()
			except BaseException as e:
				self.warn('Failed to flush log file', e)

roleInfo = {
	'format': '1.0',
	'class': Logger,
	'author': 'Etienne Perot',
	'version': '1.0',
	'description': 'Logs all Log messages to a file.',
	'config': {
		'file': {
			'default': '/var/log/kozo/kozo.log',
			'description': 'Path of the log file.'
		},
		'nodeRestrict': {
			'default': NODE_NAME,
			'description': 'Only log messages coming from this node. Set to "*" to log messages from all nodes.'
		},
		'timePrefix': {
			'default': '[%Y-%m-%d %H:%M:%S] ',
			'description': 'Timestamp format used as prefix on each line. See http://docs.python.org/2/library/time.html#time.strftime for the available variables.'
		},
		'flushEvery': {
			'default': 1024,
			'description': 'Flush the file every n messages.'
		},
		'rotateEvery': {
			'default': 524288,
			'description': 'Rotate logs every n messages.'
		},
		'rotateMax': {
			'default': 9,
			'description': 'How many rotated logs we should keep.'
		}
	}
}