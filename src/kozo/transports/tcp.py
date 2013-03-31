import socket
import six
from kozo.authenticatedtransport import AuthenticatedTransport
from kozo.log import infoTransport

_defaultConfig = {
	'port': 6020,
	'socketConnectionBacklog': 256,
	'channelCreationTimeout': 30
}

class TCPTransport(AuthenticatedTransport):
	def __init__(self, name, config):
		AuthenticatedTransport.__init__(self, name, config, _defaultConfig, ['address'])
		if isinstance(self['address'], six.string_types):
			self['address'] = [self['address']]
		if len(self['address']) < 0:
			raise KozoError('Must provide at least one address.')
		self._serverSocket = None
	def bind(self):
		AuthenticatedTransport.bind(self)
		self._serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._serverSocket.bind(('', self['port']))
		self._serverSocket.listen(self['socketConnectionBacklog'])
	def getUnauthenticatedConnectAddresses(self, otherTransport):
		return [(address,  otherTransport['port']) for address in otherTransport['address']]
	def getUnauthenticatedSocket(self, otherTransport, addressIndex, address):
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.connect(address)
		return sock
	def acceptUnauthenticatedConnection(self):
		return self._serverSocket.accept()[0]
