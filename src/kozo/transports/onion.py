import base64
import random
import socket
import struct
import time
import Crypto.Random
import paramiko
import six
from kozo import kozoConfig, kozoSystem, KozoError, Transport, Channel
from kozo.log import infoTransport

def _readLoop(read, bytes, timeout):
	data = b''
	deadline = time.time() + timeout
	while len(data) < bytes and time.time() < deadline:
		try:
			data += read(bytes - len(data))
		except socket.timeout:
			break
	if time.time() >= deadline:
		return None
	return data

class OnionTransport(Transport):
	MAGIC_KNOCKKNOCK = b'KOZO_KNOCK_KNOCK'
	RANDOM_LENGTH = (4 * 1024, 8 * 1024)
	INITIAL_SIGN_FORMAT = b'{date}|{server}|{client}|{random}'
	MAX_INITIAL_SIGN_LENGTH = 32 * 1024
	ACTUAL_SIGN_FORMAT = b'{initial}|{date}|{server}|{client}|{random}'
	MAX_ACTUAL_SIGN_LENGTH = 64 * 1024
	SIGNED_MAX_EXPANSION_FACTOR = 16
	MAX_DATE_DELTA = 24 * 3600
	SIGN_OK = b'KOZO_OK'
	RANDOM_DEADLINE = 600
	def init(self):
		if self['incomingOnly'] and self['outgoingOnly']:
			raise KozoError('Cannot have both incomingOnly and outgoingOnly enabled.')
		if self['outgoingOnly'] and self['address']:
			raise KozoError('Cannot provide both outgoingOnly and address.')
		if not self['outgoingOnly']:
			if not self['address']:
				raise KozoError('Must provide .onion address.')
			if not self['address'].endswith('.onion'):
				raise KozoError('Address must end in .onion.')
		if self['onionPort'] is None:
			self['onionPort'] = self['port']
		self._serverSocket = None
		self._maxNodeNameLength = max(len(node.getName()) for node in kozoSystem().getNodes())
		if self._maxNodeNameLength + self.RANDOM_LENGTH[1] > self.MAX_INITIAL_SIGN_LENGTH / 2:
			raise KozoError('Some Node in the system has a name that is too long for the onion Transport to work.')
	def localInit(self):
		self._privateKey = paramiko.RSAKey.from_private_key_file(self.getNode().getPrivateKeyPath())
	def bind(self):
		if not self['outgoingOnly']:
			self._serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self._serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			self._serverSocket.bind(('localhost', self['port']))
			self._serverSocket.listen(self['socketConnectionBacklog'])
	def getPriority(self):
		return Transport.Priority_MEH
	def canAccept(self):
		return not self['outgoingOnly']
	def canConnect(self, otherTransport):
		return not self['incomingOnly'] and not otherTransport['outgoingOnly'] and Transport.canConnect(self, otherTransport)
	def _genRandom(self):
		numBytes = random.randint(*self.RANDOM_LENGTH) # We can be more lax with the range
		data = _readLoop(Crypto.Random.new().read, numBytes, min(self.RANDOM_DEADLINE, kozoConfig('connectionRetry')))
		if data is None:
			raise KozoError('Could not generate', numBytes, 'of random data fast enough')
		return data
	def _readLoop(self, read, bytes):
		data = _readLoop(read, bytes, kozoConfig('connectionRetry'))
		if data is None:
			raise KozoError('Could not read', bytes, 'bytes before timeout')
		return data
	def connect(self, otherTransport):
		assert self._privateKey is not None
		selfNode = self.getNode()
		selfName = selfNode.getName()
		remoteNode = otherTransport.getNode()
		remoteName = remoteNode.getName()
		remoteAddress = (otherTransport['address'], otherTransport['onionPort'])
		try:
			sock = socket.create_connection(remoteAddress, kozoConfig('connectionRetry'))
			# First, send magic knock-knock message.
			sock.sendall(self.MAGIC_KNOCKKNOCK + struct.pack('=H', len(selfName)) + selfName.encode('utf8'))
			# We expect to be asked to sign a message of length up to 32K characters.
			signLength = struct.unpack('=H', self._readLoop(sock.recv, struct.calcsize('=H')))[0]
			if signLength > self.MAX_INITIAL_SIGN_LENGTH:
				raise KozoError('Initial signature length too long:', signLength)
			# Get message to sign.
			initialToSign = self._readLoop(sock.recv, signLength)
			# Expand it.
			selfDate = int(time.time())
			selfRandom = self._genRandom()
			actualToSign = self.ACTUAL_SIGN_FORMAT.format(
				initial=initialToSign,
				date=str(selfDate).encode('utf8'),
				server=remoteName.encode('utf8'),
				client=selfName.encode('utf8'),
				random=selfRandom
			)
			# Sign it.
			signed = bytes(self._privateKey.sign_ssh_data(Crypto.Random.new(), actualToSign))
			# Send signed response back.
			sock.sendall(struct.pack('=Qii', selfDate, len(selfRandom), len(signed)) + selfRandom + signed)
			# Expect acknowledgement.
			acknowledgement = self._readLoop(sock.recv, len(self.SIGN_OK))
			if acknowledgement != self.SIGN_OK:
				raise KozoError('Invalid acknowledgement.')
			# We're all clear.
			return OnionChannel(selfNode, remoteNode, sock)
		except BaseException as e:
			infoTransport(self, 'Failed to connect to', remoteAddress, e, printTraceback=False)
	def accept(self):
		infoTransport(self, 'Waiting for a connection')
		assert self._serverSocket is not None
		selfNode = self.getNode()
		selfName = selfNode.getName()
		connection = self._serverSocket.accept()[0]
		try:
			connection.settimeout(kozoConfig('connectionRetry'))
			# Parse header.
			knockHeader = self._readLoop(connection.recv, len(self.MAGIC_KNOCKKNOCK))
			if knockHeader != self.MAGIC_KNOCKKNOCK:
				raise KozoError('Invalid header received')
			nodeNameLength = struct.unpack('=H', self._readLoop(connection.recv, struct.calcsize('=H')))[0]
			if nodeNameLength > self._maxNodeNameLength:
				raise KozoError('Node length field larger than largest-named node defined in the system:', nodeNameLength)
			remoteName = self._readLoop(connection.recv, nodeNameLength).decode('utf8')
			remoteNode = kozoSystem().getNodeByName(remoteName)
			if remoteNode is None:
				raise KozoError('Unknown node name received', repr(remoteName))
			remoteKey = paramiko.RSAKey(data=base64.b64decode(remoteNode.getPublicKey()[1]))
			# Generate message to sign.
			selfDate = int(time.time())
			selfRandom = self._genRandom()
			initialToSign = self.INITIAL_SIGN_FORMAT.format(
				date=str(selfDate).encode('utf8'),
				server=selfName.encode('utf8'),
				client=remoteName.encode('utf8'),
				random=selfRandom
			)
			# Send it.
			connection.sendall(struct.pack('=H', len(initialToSign)) + initialToSign)
			# Get and verify signed response.
			remoteDate, remoteRandomLength, remoteSignedLength = struct.unpack('=Qii', self._readLoop(connection.recv, struct.calcsize('=Qii')))
			if abs(remoteDate - selfDate) > self.MAX_DATE_DELTA:
				raise KozoError('Clocks differ by', abs(remoteDate - selfDate), 'seconds; rejecting message')
			if remoteRandomLength < self.RANDOM_LENGTH[0]:
				raise KozoError('Remote random string is shorter than minimum of', self.RANDOM_LENGTH[0], 'bytes')
			if remoteRandomLength > self.RANDOM_LENGTH[1]:
				raise KozoError('Remote random string is longer than maximum of', self.RANDOM_LENGTH[1], 'bytes')
			remoteRandom = self._readLoop(connection.recv, remoteRandomLength)
			actualToSign = self.ACTUAL_SIGN_FORMAT.format(
				initial=initialToSign,
				date=str(remoteDate).encode('utf8'),
				server=selfName.encode('utf8'),
				client=remoteName.encode('utf8'),
				random=remoteRandom
			)
			if len(actualToSign) > self.MAX_ACTUAL_SIGN_LENGTH:
				raise KozoError('Message to sign is too long:', len(actualToSign), 'bytes while max is', self.MAX_ACTUAL_SIGN_LENGTH)
			if remoteSignedLength > len(actualToSign) * self.SIGNED_MAX_EXPANSION_FACTOR:
				raise KozoError('Signed message is too long:', remoteSignedLength, 'bytes while max is', len(actualToSign) * self.SIGNED_MAX_EXPANSION_FACTOR)
			actualSigned = paramiko.Message(self._readLoop(connection.recv, remoteSignedLength))
			if not remoteKey.verify_ssh_sig(actualToSign, actualSigned):
				raise KozoError('Invalid signature received')
			# Send acknowledgement.
			connection.sendall(self.SIGN_OK)
			# We're clear.
			return OnionChannel(remoteNode, selfNode, connection)
		except BaseException:
			try:
				connection.close()
			except:
				pass
			raise

class OnionChannel(Channel):
	def __init__(self, fromNode, toNode, sock):
		Channel.__init__(self, fromNode, toNode)
		self._sock = sock
	def kill(self):
		Channel.kill(self)
		self._sock.close()
	def send(self, bytes):
		return self._sock.send(bytes)
	def receive(self, bytes, timeout):
		self._sock.settimeout(timeout)
		try:
			return self._sock.recv(bytes)
		except socket.timeout:
			return None
	def __str__(self):
		return 'Onion' + Channel.__str__(self)

transportInfo = {
	'format': '1.0',
	'class': OnionTransport,
	'author': 'Etienne Perot',
	'version': '1.0',
	'description': 'A transport going over Tor, using hidden services (.onion domains). As these already provide encryption, this Transport only does initial authentication of the client. Requires Tor running on the machine and set up to do transparent DNS resolution and proxying for .onion domain names.',
	'config': {
		'address': {
			'default': None,
			'description': 'Domain name ending in .onion. Required unless outgoingOnly is specified.'
		},
		'port': {
			'default': 6027,
			'description': 'Local TCP port to bind to.'
		},
		'incomingOnly': {
			'default': False,
			'description': 'If True, this Transport can only be used to receive connections from other onion transports. Useful if the local node doesn\'t have transparent DNS resolution and proxying for .onion domain names.'
		},
		'outgoingOnly': {
			'default': False,
			'description': 'If True, this Transport can only be used to connect to other onion transports. Useful if the local node doesn\'t have a .onion address, but still has Tor running.'
		},
		'onionPort': {
			'default': None,
			'description': 'Virtual onion port number that will get forwarded to the local TCP port. If not set, the same value as port is used.'
		},
		'socketConnectionBacklog': {
			'default': 256,
			'description': 'Maximum number of incoming-but-unprocessed connections to allow.'
		}
	}
}