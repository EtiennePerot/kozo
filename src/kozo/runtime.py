import itertools
import threading
import time
from .kozo import kozoSystem, kozoRuntime
from .log import *

class KozoRuntime(object):
	def __init__(self):
		self._lock = threading.RLock()
		self._transportThreads = []
		self._roleThreads = []
		self._connectionThreads = []
		self._incomingChannelThreads = {}
		self._outgoingChannels = {}
	def start(self):
		for node in kozoSystem().getNodes():
			if node.isSelf():
				for transport in node.getTransports():
					self._transportThreads.append(TransportThread(transport))
				for role in node.getRoles():
					self._roleThreads.append(RoleThread(role))
			else:
				self._connectionThreads.append(ConnectionThread(node))
		for threadList in (self._transportThreads, self._roleThreads, self._connectionThreads):
			for thread in threadList:
				thread.start()
	def isAlive(self):
		for thread in self._roleThreads:
			if thread.isAlive():
				return True
	def join(self):
		while self.isAlive():
			for thread in self._roleThreads:
				thread.join(30)
	def handOffIncomingChannel(self, channel):
		with self._lock:
			if channel.getFromNode() in self._incomingChannelThreads:
				self._incomingChannelThreads[channel.getFromNode()].kill()
			self._incomingChannelThreads[channel.getFromNode()] = ReceptionThread(channel)
			self._incomingChannelThreads[channel.getFromNode()].start()

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
	def execute(self):
		while self._channel.isAlive():
			try:
				message = self._channel.wrapReceive(4, 30) # FIXME: Use timeout value from config
				if not message:
					continue
				infoRuntime(self, 'Received message', message)
				# TODO: If no message in a long while, assume connection is dead
			except Exception as e:
				warnRuntime(self, 'Failed to receive message', e)
				self.kill()

class RoleThread(KozoThread):
	def __init__(self, role):
		self._role = role
		KozoThread.__init__(self, name='Role for ' + str(self._role))
	def execute(self):
		while self._role.isAlive():
			self._role.run()

class ConnectionThread(KozoThread):
	def __init__(self, node):
		self._node = node
		self._channel = None
		KozoThread.__init__(self, name='Connection to ' + str(self._node))
		self.daemon = True
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
								self._channel = None
			time.sleep(3) # FIXME: Use value from config
