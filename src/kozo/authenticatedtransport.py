import socket # Required for socket.timeout
import paramiko
from .kozo import *
from .log import *

def _publicKeyCompare(key1, key2):
	if isinstance(key1, paramiko.PKey):
		key1 = (key1.get_name(), key1.get_base64())
	if isinstance(key2, paramiko.PKey):
		key2 = (key2.get_name(), key2.get_base64())
	return key1[0] == key2[0] and key1[1] == key2[1]

class _KozoSSHServerInterface(paramiko.ServerInterface):
	def __init__(self, *args, **kwargs):
		paramiko.ServerInterface.__init__(self, *args, **kwargs)
		self._key = None
	def get_allowed_auths(self):
		return 'publickey'
	def check_auth_publickey(self, username, key):
		if username == '':
			for node in kozoSystem().getNodes():
				if _publicKeyCompare(node.getPublicKey(), key):
					self._key = key
					return paramiko.AUTH_SUCCESSFUL
		return paramiko.AUTH_FAILED
	def check_channel_request(self, kind, channelId):
		if kind == 'kozo':
			return paramiko.OPEN_SUCCEEDED
		return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
	def getKey(self):
		return self._key

class AuthenticatedTransport(Transport):
	def __init__(self, name, config, *args, **kwargs):
		Transport.__init__(self, name, config, *args, **kwargs)
		self._privateKey = None
	def _initializeParamikoTransport(self, transport):
		transport.set_keepalive(True)
		transport.get_security_options().ciphers = (kozoConfig('cipher'),)
		transport.get_security_options().digests = (kozoConfig('hmac'),)
	def bind(self):
		Transport.bind(self)
		if self._privateKey is None:
			self._privateKey = paramiko.RSAKey.from_private_key_file(self.getNode().getPrivateKeyPath())
	def connect(self, otherTransport):
		if self._privateKey is None:
			self._privateKey = paramiko.RSAKey.from_private_key_file(self['privateKey'])
		addresses = self.getUnauthenticatedConnectAddresses(otherTransport)
		for addressIndex, address in enumerate(addresses):
			try:
				unauthenticatedSocket = self.getUnauthenticatedSocket(otherTransport, addressIndex, address)
				if unauthenticatedSocket is None:
					infoTransport(self, 'Failed to connect to', address, '(No socket returned)')
					continue
				transport = paramiko.Transport(unauthenticatedSocket)
				self._initializeParamikoTransport(transport)
				transport.start_client()
				hostKey = transport.get_remote_server_key()
				if not _publicKeyCompare(hostKey, otherTransport.getNode().getPublicKey()):
					warnTransport(self, 'Got an invalid host key when connecting to', otherTransport)
					continue
				transport.auth_publickey('', self._privateKey)
				channel = transport.open_channel('kozo')
				return AuthenticatedChannel(self.getNode(), otherTransport.getNode(), channel)
			except Exception as e:
				infoTransport(self, 'Failed to connect to', address, e, printTraceback=False)
	def accept(self):
		infoTransport(self, 'Waiting for a connection')
		connection = self.acceptUnauthenticatedConnection()
		if connection is not None:
			try:
				transport = paramiko.Transport(connection)
				self._initializeParamikoTransport(transport)
				try:
					transport.load_server_moduli()
				except:
					pass
				transport.add_server_key(self._privateKey)
				serverInterface = _KozoSSHServerInterface()
				infoTransport(self, 'Starting SSH server on socket', connection)
				transport.start_server(server=serverInterface)
				authChannel = transport.accept(self['channelCreationTimeout'])
				if authChannel is None:
					raise KozoError('Channel not created')
				infoTransport(self, 'Channel created successfully', authChannel)
				matchingNodes = kozoSystem().getNodesBy(lambda t: _publicKeyCompare(t.getPublicKey(), serverInterface.getKey()))
				assert len(matchingNodes) > 0
				if len(matchingNodes) > 1:
					raise KozoError('Cannot have more than one node with a given public key.')
				return AuthenticatedChannel(matchingNodes[0], self.getNode(), authChannel)
			except:
				try:
					connection.close()
				except:
					pass
				raise
	def __str__(self):
		return 'Auth' + Transport.__str__(self)
	def getUnauthenticatedConnectAddresses(self, otherTransport):
		raise NotImplementedError()
	def getUnauthenticatedSocket(self, otherTransport, addressIndex, address):
		"""
		Must return a socket that conforms to http://www.lag.net/paramiko/docs/paramiko.Transport-class.html#__init__
		"""
		raise NotImplementedError()
	def acceptUnauthenticatedConnection(self):
		"""
		Must return a socket that conforms to http://www.lag.net/paramiko/docs/paramiko.Transport-class.html#__init__
		"""
		raise NotImplementedError()

class AuthenticatedChannel(Channel):
	def __init__(self, fromNode, toNode, authenticatedChannel):
		Channel.__init__(self, fromNode, toNode)
		self._authenticatedChannel = authenticatedChannel
	def kill(self):
		Channel.kill(self)
		self._authenticatedChannel.shutdown_read()
		self._authenticatedChannel.shutdown_write()
		self._authenticatedChannel.close()
	def send(self, bytes):
		return self._authenticatedChannel.send(bytes)
	def receive(self, bytes, timeout):
		self._authenticatedChannel.settimeout(timeout)
		try:
			return self._authenticatedChannel.recv(bytes)
		except socket.timeout: # Sent by Paramiko, not the underlying socket
			return None
	def __str__(self):
		return 'Auth' + Channel.__str__(self)
