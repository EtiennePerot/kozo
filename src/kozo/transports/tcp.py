import socket
import six
from kozo import kozoConfig
from kozo.authenticatedtransport import AuthenticatedTransport
from kozo.log import infoTransport

class TCPTransport(AuthenticatedTransport):
	def init(self):
		AuthenticatedTransport.init(self)
		if isinstance(self['address'], six.string_types):
			self['address'] = [self['address']]
		if len(self['address']) < 0:
			raise KozoError('Must provide at least one address.')
		self._serverSocket = None
	def getPriority(self):
		return TCPTransport.Priority_BEST
	def bind(self):
		AuthenticatedTransport.bind(self)
		self._serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self._serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._serverSocket.bind((self['bindAddress'], self['port']))
		self._serverSocket.listen(self['socketConnectionBacklog'])
	def getUnauthenticatedConnectAddresses(self, otherTransport):
		return [(address,  otherTransport['port']) for address in otherTransport['address']]
	def getUnauthenticatedSocket(self, otherTransport, addressIndex, address):
		return socket.create_connection(address, kozoConfig('connectionRetry'))
	def acceptUnauthenticatedConnection(self):
		return self._serverSocket.accept()[0]

transportInfo = {
	'format': '1.0',
	'class': TCPTransport,
	'author': 'Etienne Perot',
	'version': '1.0',
	'description': 'A simple TCP socket transport.',
	'config': {
		'address': {
			'description': 'An address or a list of addresses that the node can be reached from.'
		},
		'port': {
			'default': 6020,
			'description': 'TCP port to bind to.'
		},
		'bindAddress': {
			'default': '',
			'description': 'Address to bind to. If not specified, listens on all interfaces.'
		},
		'socketConnectionBacklog': {
			'default': 256,
			'description': 'Maximum number of incoming-but-unprocessed connections to allow.'
		}
	}
}