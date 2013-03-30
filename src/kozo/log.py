import logging as _logging
import threading as _threading
try:
	import queue as _Queue
except ImportError:
	import Queue as _Queue
import traceback as _traceback
from .messages import Log as _Log

_logging.basicConfig()
_localLogger = _logging.getLogger('kozo')
_localLogger.setLevel(_logging.INFO)
_logQueue = _Queue.Queue()

class _logThread(_threading.Thread):
	def __init__(self):
		_threading.Thread.__init__(self, name='Logging thread')
		self.daemon = True
	def run(self):
		while True:
			level, message = _logQueue.get()
			_localLogger.log(level, message)

_logThreadInstance = _logThread()
_logThreadInstance.start()

def _log(level, *msg, **kwargs):
	newMsg = []
	for m in msg:
		if type(m) is type(''):
			newMsg.append(m)
		elif isinstance(m, Exception):
			if 'printTraceback' not in kwargs or kwargs['printTraceback']:
				try:
					trace = _traceback.print_exc()
					newMsg.append('; Exception: ' + str(m) + ' - Traceback:\n' + trace)
				except:
					newMsg.append('; Exception: ' + str(m) + ' - Traceback unavailable.')
			else:
				newMsg.append('; Exception: ' + str(m) + '.')
		else:
			newMsg.append(str(m))
	_logQueue.put((level, ' '.join(newMsg)))

def info(*msg, **kwargs):
	return _log(_logging.INFO, *msg, **kwargs)

def warn(*msg, **kwargs):
	return _log(_logging.WARNING, *msg, **kwargs)

def error(*msg, **kwargs):
	return _log(_logging.ERROR, *msg, **kwargs)

def infoTransport(transport, *msg, **kwargs):
	return info('[' + str(transport) + ']', *msg, **kwargs)

def warnTransport(transport, *msg, **kwargs):
	return warn('[' + str(transport) + ']', *msg, **kwargs)

def errorTransport(transport, *msg, **kwargs):
	return error('[' + str(transport) + ']', *msg, **kwargs)

def infoRuntime(thread, *msg, **kwargs):
	return info('[Runtime:' + thread.name + ']', *msg, **kwargs)

def warnRuntime(thread, *msg, **kwargs):
	return warn('[Runtime:' + thread.name + ']', *msg, **kwargs)

def errorRuntime(thread, *msg, **kwargs):
	return error('[Runtime:' + thread.name + ']', *msg, **kwargs)
