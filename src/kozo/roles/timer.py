import time
import kozo
from kozo.log import *

_defaultConfig = {
	'tick': 1,
	'message': 'Cuckoo!'
}

class Timer(kozo.Role):
	def __init__(self, name, config):
		kozo.Role.__init__(self, name, config, _defaultConfig)
	def run(self):
		time.sleep(self['tick'])
		info(self['message'])
