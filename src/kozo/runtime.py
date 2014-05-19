import itertools
import random
import struct
import threading
import time
from .kozo import kozoSystem, kozoRuntime, kozoConfig, KozoStopError, Node
from .messages import *
from .log import *
from .helpers import randomWait, RollingQueue

_messageMagicHeader = 'KOZOMSG'

class KozoRuntime(object):
	def __init__(self):
		self._lock = threading.RLock()
		self._transportThreads = []
		self._roleThreads = {}
		self._connectionThreads = {}
		self._incomingChannelThreads = {}
	def _allThreads(self, key=lambda x: True):
		allThreads = self._transportThreads + self._roleThreads.values() + self._connectionThreads.values() + self._incomingChannelThreads.values()
		return filter(key, allThreads)
	def _allActiveThreads(self):
		return self._allThreads(key=lambda x: not x.daemon)
	def start(self):
		for node in kozoSystem().getNodes():
			for transport in node.getTransports():
				transport.init()
			for role in node.getRoles():
				role.init()
		selfNode = kozoSystem().getSelfNode()
		tryOutgoingConnections = selfNode.getSelfToOthersConnectPolicy() != Node.CONNECTPOLICY_NEVER
		listenIncomingConnections = selfNode.getOthersToSelfConnectPolicy() != Node.CONNECTPOLICY_NEVER
		for transport in selfNode.getTransports():
			transport.localInit()
			if listenIncomingConnections and transport.canAccept():
				self._transportThreads.append(TransportThread(transport))
		for role in selfNode.getRoles():
			role.localInit()
			self._roleThreads[role] = RoleThread(role)
		for node in kozoSystem().getNodes():
			if not node.isSelf() and tryOutgoingConnections and node.getOthersToSelfConnectPolicy() != Node.CONNECTPOLICY_NEVER:
				self._connectionThreads[node] = ConnectionThread(node)
		for thread in self._allThreads():
			thread.start()
	def isAlive(self):
		for thread in self._allActiveThreads():
			if thread.isAlive():
				return True
	def kill(self):
		for role in kozoSystem().getSelfNode().getRoles():
			role.kill()
	def join(self, verbose=False):
		while self.isAlive():
			for thread in self._allActiveThreads():
				if verbose:
					info('Waiting for runtime thread', thread)
				try:
					thread.join(3600)
					if verbose:
						info('Waited for runtime thread', thread)
				except BaseException as e:
					if verbose:
						info('Got exception while waiting for runtime thread', thread, e)
					raise
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
			elif node in self._connectionThreads:
				self._connectionThreads[node].sendMessage(message)
			else:
				warn('Tried to send a message to', node, 'but no connection thread for it exists; likely a connection policy issue.')

class KozoThread(threading.Thread):
	_threadNumber = itertools.count() # Atomic
	def __init__(self, *args, **kwargs):
		threading.Thread.__init__(self, *args, **kwargs)
		self._threadId = KozoThread._threadNumber.next()
		self.name = str(self._threadId) + '#' + self.name
	def getSubthreads(self):
		return []
	def start(self):
		threading.Thread.start(self)
		for subthread in self.getSubthreads():
			subthread.start()
	def kill(self):
		for subthread in self.getSubthreads():
			subthread.kill()
	def join(self, timeout=None):
		for subthread in self.getSubthreads():
			subthread.join(timeout)
		threading.Thread.join(self, timeout)
	def isAlive(self):
		for subthread in self.getSubthreads():
			if subthread.isAlive():
				return True
		return threading.Thread.isAlive(self)
	is_aliv = isAlive
	def run(self):
		try:
			infoRuntime(self, 'Running')
			self.execute()
			infoRuntime(self, 'Stopped')
		except BaseException as e:
			warnRuntime(self, 'Stopped with exception', e)

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
			except BaseException as e:
				warnRuntime(self, 'Could not accept channel', e)

class ReceptionThread(KozoThread):
	def __init__(self, channel):
		self._channel = channel
		KozoThread.__init__(self, name='Reception for ' + str(self._channel))
		self.daemon = True
	def kill(self):
		KozoThread.kill(self)
		self._channel.kill()
		infoRuntime(self, 'Killed')
	def _receiveBytes(self, bytes, timeout):
		totalData = b''
		bufferSize = max(1, min(kozoConfig('maxBufferReadSize'), bytes))
		deadline = time.time() + timeout * (1 + bytes / bufferSize)
		while len(totalData) < bytes:
			data = self._channel.wrapReceive(min(bytes - len(totalData), bufferSize), timeout)
			if not data or time.time() > deadline:
				return b''
			totalData += data
		return totalData
	def execute(self):
		while self._channel.isAlive():
			try:
				lengthBytes = self._receiveBytes(len(_messageMagicHeader) + struct.calcsize('I'), kozoConfig('connectionRetry'))
				if lengthBytes:
					if lengthBytes[:len(_messageMagicHeader)] != _messageMagicHeader:
						warnRuntime(self, 'Message did not have valid header:', repr(lengthBytes[:len(_messageMagicHeader)]), '; killing connection.')
						self.kill()
					else:
						length = struct.unpack('I', lengthBytes[len(_messageMagicHeader):])[0]
						messageBytes = self._receiveBytes(length, kozoConfig('connectionRetry'))
						if messageBytes:
							message = decodeMessage(messageBytes)
							kozoRuntime().handOffIncomingMessage(message)
						else:
							infoRuntime(self, 'Channel timeout while trying to read message of expected size', length)
							self.kill()
				else:
					infoRuntime(self, 'Channel timeout while trying to read message.')
					self.kill()
			except BaseException as e:
				warnRuntime(self, 'Failed to receive message', e)
				self.kill()

class RoleThread(KozoThread):
	def __init__(self, role):
		self._role = role
		self._incomingMessagesQueue = RollingQueue(self._role.getMessageQueueLength(), self._role.getMessageQueueSize())
		KozoThread.__init__(self, name='Role for ' + str(self._role))
		self._dead = threading.Event()
		self._role.setControllingThread(self)
	def deliver(self, message):
		self._incomingMessagesQueue.push(message, message.getSize())
	def sendMessage(self, message):
		kozoRuntime().sendMessage(message)
	def sleep(self, seconds):
		isDead = self._dead.wait(seconds)
		if isDead:
			raise KozoStopError()
	def kill(self):
		KozoThread.kill(self)
		self._dead.set()
		self._incomingMessagesQueue.interrupt()
	def getMessage(self, timeout=None):
		"""Get a message from the incoming message queue.

		Arguments:
			timeout: Timeout when waiting for a message. 0 for non-blocking, None for default timeout value. Custom values cannot surpass the default.

		Returns:
			A RoleMessage object, or None if we didn't receive anything in time.
		"""
		if timeout is None:
			timeout = kozoConfig('connectionRetry')
		else:
			timeout = min(timeout, kozoConfig('connectionRetry'))
		return self._incomingMessagesQueue.pop(timeout > 0, timeout)
	def execute(self):
		beforeTimestamp = None
		rateControl = self._role.getRateControl()
		try:
			if rateControl is not None:
				randomWait(rateControl, sleepFunction=self.sleep)
			while not self._dead.is_set():
				beforeTimestamp = time.time()
				self._role.run()
				rateControl = self._role.getRateControl()
				if type(rateControl) is int or type(rateControl) is float:
					if self._role.getMessageRateControlOverride() and not self._incomingMessagesQueue.isEmpty():
						# We have a message, don't sleep
						continue
					afterTimestamp = time.time()
					if afterTimestamp - beforeTimestamp < rateControl:
						self.sleep(rateControl - (afterTimestamp - beforeTimestamp))
		except KozoStopError:
			pass

class HeartbeatThread(KozoThread):
	def __init__(self, connectionThread, toNode):
		self._connectionThread = connectionThread
		self._toNode = toNode
		KozoThread.__init__(self, name='Heartbeat to ' + str(self._toNode))
		self.daemon = True
	def execute(self):
		randomWait(kozoConfig('heartbeat'))
		while True:
			time.sleep(kozoConfig('heartbeat'))
			if self._connectionThread.shouldSendHeartbeat():
				kozoRuntime().sendMessage(Heartbeat(self._toNode))

class ConnectionThread(KozoThread):
	def __init__(self, node):
		self._node = node
		self._channel = None
		self._outgoingMessagesQueue = RollingQueue(kozoConfig('outgoingQueueLength'), kozoConfig('outgoingQueueSize'))
		self._heartbeatThread = HeartbeatThread(self, self._node)
		KozoThread.__init__(self, name='Connection to ' + str(self._node))
		self.daemon = True
	def getSubthreads(self):
		return [self._heartbeatThread]
	def _shouldConnect(self):
		selfToRemote = kozoSystem().getSelfNode().getSelfToOthersConnectPolicy()
		remoteToSelf = self._node.getOthersToSelfConnectPolicy()
		return (
			remoteToSelf != Node.CONNECTPOLICY_NEVER
		) and (
			selfToRemote != Node.CONNECTPOLICY_NEVER
		) and (
			(
				(
					remoteToSelf == Node.CONNECTPOLICY_CONSTANT
				) and (
					selfToRemote == Node.CONNECTPOLICY_CONSTANT
				)
			) or (
				not self._outgoingMessagesQueue.isEmpty()
			)
		)
	def shouldSendHeartbeat(self):
		return self._channel is not None or self._shouldConnect()
	def sendMessage(self, message):
		self._outgoingMessagesQueue.push(message, message.getSize())
	def _sendBytes(self, bytes):
		while len(bytes):
			sentBytes = self._channel.wrapSend(bytes)
			if sentBytes == 0:
				return 0
			bytes = bytes[sentBytes:]
	def kill(self):
		KozoThread.kill(self)
		try:
			self._channel.kill()
		except:
			pass
		self._channel = None
		self._outgoingMessagesQueue.purge(lambda m: not isinstance(m, Heartbeat))
		infoRuntime(self, 'Killed')
	def execute(self):
		randomWait(kozoConfig('connectionRetry'))
		originNode = kozoSystem().getSelfNode()
		targetNode = self._node
		while True:
			if self._shouldConnect() and (self._channel is None or not self._channel.isAlive()):
				for originTransport in sorted(originNode.getTransports(), key=lambda t: t.getPriority(), reverse=True):
					for targetTransport in sorted(targetNode.getTransports(), key=lambda t: t.getPriority(), reverse=True):
						if originTransport.canConnect(targetTransport):
							try:
								infoRuntime(self, 'Attempting to connect', originTransport, 'to', targetTransport)
								self._channel = originTransport.connect(targetTransport)
								if self._channel is None:
									infoRuntime(self, 'Connection failed (None returned)')
									continue
								infoRuntime(self, 'Successful connection', self._channel)
							except BaseException as e:
								infoRuntime(self, 'Connection failed', e)
								self.kill()
			if self._channel is not None:
				try:
					toDeliver = self._outgoingMessagesQueue.pop(True, kozoConfig('connectionRetry'))
					if toDeliver is not None:
						messageBytes = toDeliver.toBytes()
						if messageBytes is None:
							infoRuntime(self, 'Could not serialize message; killing connection.')
							self.kill()
						elif self._sendBytes(_messageMagicHeader + struct.pack('I', len(messageBytes)) + messageBytes) == 0:
							infoRuntime(self, 'Could not send message; assuming connection is dead.')
							self.kill()
					else:
						warnRuntime(self, 'Did not send any mesage during the last period, is heartbeat thread dead?', e)
				except BaseException as e:
					warnRuntime(self, 'Got exception while trying to send, assuming connection is dead.', e)
					self.kill()
			else:
				time.sleep(kozoConfig('connectionRetry'))
