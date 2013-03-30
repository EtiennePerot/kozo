import os
import random
import socket
import six
import paramiko
from kozo import *
from kozo.log import *

class _KozoSSHServerInterface(paramiko.ServerInterface):
	def __init__(self, *args, **kwargs):
		paramiko.ServerInterface.__init__(self, *args, **kwargs)
		self._key = None
	def get_allowed_auths(self):
		return 'publickey'
	def check_auth_publickey(self, username, key):
		if username == '':
			for node in kozoSystem().getNodes():
				for transport in node.getTransports():
					if transport.__class__ == SSHTransport and transport._hasPublicKey(key):
						self._key = key
						return paramiko.AUTH_SUCCESSFUL
		return paramiko.AUTH_FAILED
	def check_channel_request(self, kind, channelId):
		if kind == 'kozo':
			return paramiko.OPEN_SUCCEEDED
		return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
	def getKey(self):
		return self._key
	def check_channel_subsystem_request(self, channel, name):
		print('CALLED', channel, name)

_defaultConfig = {
	'address': [],
	'port': 6020,
	'privateKey': '/var/lib/kozo/transports/ssh/key',
	'publicKey': '',
	'socketConnectionBacklog': 256,
	'channelCreationTimeout': 30
}

class SSHTransport(Transport):
	def __init__(self, name, config):
		Transport.__init__(self, name, config, _defaultConfig, ['address'])
		if isinstance(self['address'], six.string_types):
			self['address'] = [self['address']]
		if len(self['address']) < 0:
			raise KozoError('Must provide at least one address.')
		self._serverSocket = None
		self._privateKey = None
		self._publicKey = self['publicKey'].split(' ', 3)
		if len(self._publicKey) < 2:
			raise KozoError('Invalid public key.')
	def _hasPublicKey(self, key):
		return self._publicKey[0] == key.get_name() and self._publicKey[1] == key.get_base64()
	def bind(self):
		if self._privateKey is None:
			self._privateKey = paramiko.RSAKey.from_private_key_file(self['privateKey'])
		self._serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._serverSocket.bind(('', self['port']))
		self._serverSocket.listen(self['socketConnectionBacklog'])
	def connect(self, otherTransport):
		if self._privateKey is None:
			self._privateKey = paramiko.RSAKey.from_private_key_file(self['privateKey'])
		for address in otherTransport['address']:
			try:
				transport = paramiko.Transport((address, otherTransport['port']))
				transport.set_keepalive(True)
				transport.start_client()
				hostKey = transport.get_remote_server_key()
				if not otherTransport._hasPublicKey(hostKey):
					warnTransport(self, 'Got an invalid host key when connecting to', e)
					continue
				transport.auth_publickey('', self._privateKey)
				channel = transport.open_channel('kozo')
				return SSHChannel(self.getNode(), otherTransport.getNode(), channel)
			except Exception as e:
				infoTransport(self, 'Failed to connect to', address, e, printTraceback=False)
	def accept(self):
		infoTransport(self, 'Waiting for a connection')
		connection = self._serverSocket.accept()[0]
		try:
			transport = paramiko.Transport(connection)
			try:
				transport.load_server_moduli()
			except:
				pass
			transport.add_server_key(self._privateKey)
			transport.set_keepalive(True)
			serverInterface = _KozoSSHServerInterface()
			infoTransport(self, 'Starting SSH server on socket', connection)
			transport.start_server(server=serverInterface)
			sshChannel = transport.accept(self['channelCreationTimeout'])
			if sshChannel is None:
				raise KozoError('Channel not created')
			infoTransport(self, 'Channel created successfully', sshChannel)
			matchingNodes = kozoSystem().getNodesByTransport(lambda t: t.__class__ == self.__class__ and t._hasPublicKey(serverInterface.getKey()))
			assert len(matchingNodes) > 0
			if len(matchingNodes) > 1:
				raise KozoError('Cannot have more than one node with a given public key.')
			return SSHChannel(matchingNodes[0], self.getNode(), sshChannel)
		except:
			try:
				connection.close()
			except:
				pass
			raise
	def __str__(self):
		return 'SSH' + Transport.__str__(self)

class SSHChannel(Channel):
	def __init__(self, fromNode, toNode, sshChannel):
		Channel.__init__(self, fromNode, toNode)
		self._sshChannel = sshChannel
	def kill(self):
		Channel.kill(self)
		self._sshChannel.shutdown_read()
		self._sshChannel.shutdown_write()
	def send(self, message):
		return self._sshChannel.send(message)
	def receive(self, bytes, timeout):
		self._sshChannel.settimeout(timeout)
		try:
			return self._sshChannel.recv(bytes)
		except socket.timeout:
			return None
	def __str__(self):
		return 'SSH' + Channel.__str__(self)
