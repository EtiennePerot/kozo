import collections
import imp
import os
import random
import sys
import time
import threading

def importFile(file, namePrefix='kozo_module_', extraPaths=[]):
	moduleName = namePrefix + os.path.basename(file)
	if moduleName.lower().endswith('.py'):
		moduleName = moduleName[:-3]
	originalPath = sys.path[:]
	for p in reversed(extraPaths):
		sys.path.insert(0, p)
	imp.acquire_lock()
	newModule = imp.load_source(moduleName, file)
	imp.release_lock()
	sys.path = originalPath
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
	Limits by both maximum length (number of elements) and maximum size (memory used by elements).
	Note that the queue will still accept one larger than the maximum size, in which case all other elements will be dropped from the queue.
	"""
	def __init__(self, maxLength=None, maxSize=None):
		self._maxLength = None if maxLength is None else max(1, maxLength)
		self._maxSize = None if maxSize is None else max(1, maxSize)
		self._currentSize = 0
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
	def size(self):
		with self._condition:
			return self._currentSize
	def interrupt(self):
		with self._condition:
			self._interrupted = True
			self._condition.notifyAll()
	def push(self, item, itemSize=0):
		if itemSize is None:
			itemSize = 0
		with self._condition:
			self._currentSize += itemSize
			while ((self._maxSize is not None and self._currentSize > self._maxSize) or
			       (self._maxLength is not None and len(self._deque) >= self._maxLength)):
				_, size = self._deque.pop()
				self._currentSize -= size
			self._deque.appendleft((item, itemSize))
			self._condition.notifyAll()
	def popWithSize(self, blocking=True, timeout=None):
		with self._condition:
			while not len(self._deque):
				if not blocking or self._interrupted:
					return None, None
				self._condition.wait(timeout)
			element, size = self._deque.pop()
			self._currentSize -= size
			return element, size
	def pop(self, blocking=True, timeout=None):
		return self.popWithSize(blocking, timeout)[0]
	def purge(self, predicate):
		"""Purge all elements from the queue that don't match the given predicate."""
		with self._condition:
			elements = []
			while not self.isEmpty():
				element, size = self.popWithSize()
				if predicate(element):
					elements.append((element, size))
			for element, size in elements:
				self.push(element, size)
