import itertools
import struct
import threading
import time
try:
	import queue
except ImportError:
	import Queue as queue
from .kozo import kozoSystem, kozoRuntime, kozoConfig, KozoStopError
from .messages import *
from .log import *

class KozoRuntime(object):
	def __init__(self):
		self._lock = threading.RLock()
		self._transportThreads = []
		self._roleThreads = {}
		self._connectionThreads = {}
		self._incomingChannelThreads = {}
		self._heartbeatThread = None
	def _allThreads(self, key=lambda x: True):
		allThreads = self._transportThreads + self._roleThreads.values() + self._connectionThreads.values() + self._incomingChannelThreads.values() + [self._heartbeatThread]
		return filter(key, allThreads)
	def _allActiveThreads(self):
		return self._allThreads(key=lambda x: not x.daemon)
	def start(self):
		for node in kozoSystem().getNodes():
			if node.isSelf():
				for transport in node.getTransports():
					self._transportThreads.append(TransportThread(transport))
				for role in node.getRoles():
					self._roleThreads[role] = RoleThread(role)
			else:
				self._connectionThreads[node] = ConnectionThread(node)
		self._heartbeatThread = HeartbeatThread()
		for thread in self._allThreads():
			thread.start()
	def isAlive(self):
		for thread in self._allActiveThreads():
			if thread.isAlive():
				return True
	def kill(self):
		for role in kozoSystem().getSelfNode().getRoles():
			role.kill()
	def join(self):
		while self.isAlive():
			for thread in self._allActiveThreads():
				thread.join(3600)
	def handOffIncomingChannel(self, channel):
		with self._lock:
			if channel.getFromNode() in self._incomingChannelThreads:
				self._incomingChannelThreads[channel.getFromNode()].kill()
			self._incomingChannelThreads[channel.getFromNode()] = ReceptionThread(channel)
			self._incomingChannelThreads[channel.getFromNode()].start()
	def handOffIncomingMessage(self, message):
		if isinstance(message, Heartbeat):
			pass # Nothing to do, reception thread automatically knows
		elif isinstance(message, RoleMessage):
			for role in kozoSystem().getSelfNode().getRoles():
				if role.isInterestedIn(message):
					self._roleThreads[role].deliver(message)
	def sendMessage(self, message):
		for node in message.getRecipientNodes():
			if node.isSelf():
				self.handOffIncomingMessage(message)
			else:
				self._connectionThreads[node].sendMessage(message)

class KozoThread(threading.Thread):
	_threadNumber = itertools.count() # Atomic
	def __init__(self, *args, **kwargs):
		threading.Thread.__init__(self, *args, **kwargs)
		self._threadId = KozoThread._threadNumber.next()
		self.name = str(self._threadId) + '#' + self.name
	def run(self):
		try:
			infoRuntime(self, 'Running')
			self.execute()
			infoRuntime(self, 'Stopped')
		except Exception as e:
			warnRuntime(self, 'Stopped with exception', e)

class HeartbeatThread(KozoThread):
	def __init__(self):
		KozoThread.__init__(self, name='Heartbeat thread')
		self.daemon = True
	def execute(self):
		while True:
			time.sleep(kozoConfig('heartbeat'))
			kozoRuntime().sendMessage(Heartbeat())

class TransportThread(KozoThread):
	def __init__(self, transport):
		self._transport = transport
		self._transport.bind()
		KozoThread.__init__(self, name='Server for ' + str(self._transport))
		self.daemon = True
	def execute(self):
		while True:
			try:
				channel = self._transport.accept()
				infoRuntime(self, 'Accepted channel', channel)
				kozoRuntime().handOffIncomingChannel(channel)
			except Exception as e:
				warnRuntime(self, 'Could not accept channel', e)

class ReceptionThread(KozoThread):
	def __init__(self, channel):
		self._channel = channel
		KozoThread.__init__(self, name='Reception for ' + str(self._channel))
		self.daemon = True
	def kill(self):
		self._channel.kill()
		infoRuntime(self, 'Killed')
	def _receiveBytes(self, bytes, timeout):
		totalData = b''
		# This may take at most (bytes * timeout) seconds, but that is OK right now.
		# If not, then this function also needs to keep track of time.
		while len(totalData) < bytes:
			data = self._channel.wrapReceive(bytes, timeout)
			if not data:
				return b''
			totalData += data
		return totalData
	def execute(self):
		while self._channel.isAlive():
			try:
				lengthBytes = self._receiveBytes(struct.calcsize('I'), kozoConfig('connectionRetry'))
				if lengthBytes:
					length = struct.unpack('I', lengthBytes)[0]
					messageBytes = self._receiveBytes(length, kozoConfig('connectionRetry'))
					if messageBytes:
						message = decodeMessage(messageBytes)
						kozoRuntime().handOffIncomingMessage(message)
					else:
						infoRuntime(self, 'Channel timeout while trying to read message of expected size', messageBytes)
						self.kill()
				else:
					infoRuntime(self, 'Channel timeout while trying to read message size.')
					self.kill()
			except Exception as e:
				warnRuntime(self, 'Failed to receive message', e)
				self.kill()

class RoleThread(KozoThread):
	def __init__(self, role):
		self._role = role
		self._incomingMessagesQueue = queue.Queue(self._role.getMessageQueueSize())
		KozoThread.__init__(self, name='Role for ' + str(self._role))
		self._dead = threading.Event()
		self._role.setControllingThread(self)
		self._role.init()
	def deliver(self, message):
		self._incomingMessagesQueue.put(message)
	def sendMessage(self, message):
		kozoRuntime().sendMessage(message)
	def sleep(self, seconds):
		isDead = self._dead.wait(seconds)
		if isDead:
			raise KozoStopError()
	def kill(self):
		self._dead.set()
	def getMessage(self, blocking=True):
		if blocking:
			try:
				return self._incomingMessagesQueue.get(True, kozoConfig('connectionRetry'))
			except queue.Empty:
				return None
		return self._incomingMessagesQueue.get(False)
	def execute(self):
		try:
			while not self._dead.is_set():
				self._role.run()
		except KozoStopError:
			pass

class ConnectionThread(KozoThread):
	def __init__(self, node):
		self._node = node
		self._channel = None
		self._outgoingMessagesQueue = queue.Queue(kozoConfig('outgoingQueueSize'))
		KozoThread.__init__(self, name='Connection to ' + str(self._node))
		self.daemon = True
	def sendMessage(self, message):
		self._outgoingMessagesQueue.put_nowait(message)
	def _sendBytes(self, bytes):
		while len(bytes):
			sentBytes = self._channel.wrapSend(bytes)
			if sentBytes == 0:
				return 0
			bytes = bytes[sentBytes:]
	def kill(self):
		try:
			self._channel.kill()
		except:
			pass
		self._channel = None
		infoRuntime(self, 'Killed')
	def execute(self):
		while True:
			if self._channel is None or not self._channel.isAlive():
				originNode = kozoSystem().getSelfNode()
				targetNode = self._node
				for originTransport in sorted(originNode.getTransports(), key=lambda t: t.getPriority()):
					for targetTransport in sorted(targetNode.getTransports(), key=lambda t: t.getPriority()):
						if originTransport.canConnect(targetTransport):
							try:
								infoRuntime(self, 'Attempting to connect', originTransport, 'to', targetTransport)
								self._channel = originTransport.connect(targetTransport)
								if self._channel is None:
									infoRuntime(self, 'Connection failed (None returned)')
									continue
								infoRuntime(self, 'Successful connection', self._channel)
							except Exception as e:
								infoRuntime(self, 'Connection failed', e)
								self.kill()
			if self._channel is not None:
				try:
					toDeliver = self._outgoingMessagesQueue.get(True, kozoConfig('connectionRetry'))
					messageBytes = toDeliver.toBytes()
					if self._sendBytes(struct.pack('I', len(messageBytes)) + messageBytes) == 0:
						infoRuntime(self, 'Could not send message; assuming connection is dead.')
						self.kill()
				except queue.Empty:
					warnRuntime(self, 'Did not send any mesage during the last period, is heartbeat thread dead?', e)
			else:
				time.sleep(kozoConfig('connectionRetry'))
