import collections
import imp
import os
import random
import sys
import time
import threading

def importFile(file, namePrefix='kozo_module_'):
	moduleName = namePrefix + os.path.basename(file)
	if moduleName.lower().endswith('.py'):
		moduleName = moduleName[:-3]
	imp.acquire_lock()
	newModule = imp.load_source(moduleName, file)
	imp.release_lock()
	return newModule

def randomWait(upTo, sleepFunction=time.sleep):
	return sleepFunction(random.uniform(0, upTo))

def rpio():
	try:
		import RPIO as GPIO
	except ImportError:
		import RPi.GPIO as GPIO
	return GPIO

class RollingQueue(object):
	"""
	A thread-safe, interruptible FIFO queue where pushing elements when full causes the oldest elements to be dropped.
	"""
	def __init__(self, maxLength=None):
		self._maxLength = maxLength
		self._deque = collections.deque(maxlen=self._maxLength)
		self._condition = threading.Condition()
		self._interrupted = False
	def isEmpty(self):
		return len(self) == 0
	def isFull(self):
		return self._maxLength is not None and len(self) == self._maxLength
	def __len__(self):
		with self._condition:
			return len(self._deque)
	def interrupt(self):
		with self._condition:
			self._interrupted = True
			self._condition.notifyAll()
	def push(self, item):
		with self._condition:
			self._deque.appendleft(item)
			self._condition.notifyAll()
	def pop(self, blocking=True, timeout=None):
		with self._condition:
			while not len(self._deque):
				if not blocking or self._interrupted:
					return None
				self._condition.wait(timeout)
			return self._deque.pop()
