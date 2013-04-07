import collections
import os
import random
import sys
import time
import threading

def importFile(file):
	previousPath = sys.path[:]
	sys.path = [os.path.dirname(file)] + sys.path
	importedFile = __import__(os.path.basename(file)[:os.path.basename(file).rfind('.')])
	sys.path = previousPath
	return importedFile

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
