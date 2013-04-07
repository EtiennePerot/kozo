import dbus
import socket
import time
import bluetooth
from kozo.authenticatedtransport import AuthenticatedTransport
from kozo.log import infoTransport

class BluetoothTransport(AuthenticatedTransport):
	def init(self):
		self._serverSocket = None
		self._uuid = self['uuid'].lower()
		self._address = None
		if self['address'] is not None:
			self._address = self['address'].upper()
	def getPriority(self):
		return BluetoothTransport.Priority_BAD
	def bind(self):
		AuthenticatedTransport.bind(self)
		bus = dbus.SystemBus()
		manager = dbus.Interface(bus.get_object('org.bluez', '/'), 'org.bluez.Manager')
		adapter = dbus.Interface(bus.get_object('org.bluez', manager.DefaultAdapter()), 'org.bluez.Adapter')
		adapter.SetProperty('Discoverable', self._address is None, signature='sv')
		self._serverSocket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
		self._serverSocket.bind(('', bluetooth.PORT_ANY))
		self._serverSocket.listen(self['socketConnectionBacklog'])
		bluetooth.advertise_service(self._serverSocket, 'kozo', service_id=self._uuid, service_classes=[self._uuid, bluetooth.SERIAL_PORT_CLASS], profiles=[bluetooth.SERIAL_PORT_PROFILE])
		infoTransport(self, 'Bound on port', self._serverSocket.getsockname()[1], 'with UUID', self._uuid)
	def getUnauthenticatedConnectAddresses(self, otherTransport):
		return [(otherTransport._address, otherTransport._uuid)]
	def getUnauthenticatedSocket(self, otherTransport, addressIndex, address):
		targetAddress, targetUuid = address
		serviceMatches = bluetooth.find_service(name='kozo', address=targetAddress, uuid=targetUuid)
		infoTransport(self, 'Found', len(serviceMatches), 'services matches for UUID', targetUuid, '/ Address', targetAddress)
		if not len(serviceMatches):
			return None
		sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
		sock.connect((serviceMatches[0]['host'], serviceMatches[0]['port']))
		return _BluetoothSocketWrapper(sock)
	def acceptUnauthenticatedConnection(self):
		return _BluetoothSocketWrapper(self._serverSocket.accept()[0])

class _BluetoothSocketWrapper(object):
	def __init__(self, bluetoothSocket):
		self._socket = bluetoothSocket
		self.send = self._socket.send
		self.close = self._socket.close
		self.settimeout = self._socket.settimeout
	def recv(self, numBytes):
		try:
			return self._socket.recv(numBytes)
		except bluetooth.BluetoothError as e:
			if type(e.args) is type(()) and type(e.args[0]) is int:
				raise socket.error(*e.args)
			errorString = str(e).lower()
			if 'connection reset' in errorString: # Catches BluetoothError('(104, \'Connection reset by peer\')') - Yes really, it's a stringified tuple
				raise socket.error(104, 'Connection reset by peer')
			if 'timed out' in errorString:
				raise socket.timeout()
			raise
	def __str__(self):
		return str(self._socket)

transportInfo = {
	'format': '1.0',
	'class': BluetoothTransport,
	'author': 'Etienne Perot',
	'version': '1.0',
	'description': 'Transport over Bluetooth.',
	'config': {
		'uuid': {
			'description': 'A UUID that is used to identity this transport. Can be anything, just run uuidgen to generate one.'
		},
		'address': {
			'default': None,
			'description': 'The MAC address of the Bluetooth adapter. If not provided, the node will set the adapter to publicly discoverable, and other nodes will prod all nearby Bluetooth devices. If not provided, the node will not be publicly discoverable, and other nodes will prod only the correct device. You can find out your adapter\'s MAC address by typing `hciconfig`.'
		},
		'socketConnectionBacklog': {
			'default': 256,
			'description': 'Maximum number of incoming-but-unprocessed connections to allow.'
		}
	}
}