from kozo import Role
import bluetooth

class BluetoothDiscoverer(Role):
	def init(self):
		self._currentKnownDevices = {}
	def run(self):
		self.sleep(self['cooldown'])
		devices = bluetooth.discover_devices(duration=self['searchDuration'], lookup_names=True)
		currentDevices = {}
		for address, name in devices:
			currentDevices[address.lower()] = name
		self.sendEvent('bluetooth devices in range', currentDevices)
		if len(currentDevices):
			self.info('Found Bluetooth devices:', currentDevices)
		else:
			self.info('No Bluetooth devices in range.')
		if self['log']:
			newDevices = {}
			lostDevices = {}
			nameChangedDevices = {}
			for address in self._currentKnownDevices:
				if address not in currentDevices:
					lostDevices[address] = self._currentKnownDevices[address]
			for address in lostDevices:
				del self._currentKnownDevices[address]
			for address in currentDevices:
				if address not in self._currentKnownDevices:
					newDevices[address] = currentDevices[address]
				elif currentDevices[address] != self._currentKnownDevices[address]:
					nameChangedDevices[address] = (self._currentKnownDevices[address], currentDevices[address])
			for address in newDevices:
				self.sendLog('New Bluetooth device in range:', address, '/', newDevices[address])
			for address in lostDevices:
				self.sendLog('Bluetooth device out of range:', address, '/', lostDevices[address])
			for address in nameChangedDevices:
				self.sendLog('Bluetooth device', address, 'changed name from', nameChangedDevices[address][0], 'to', nameChangedDevices[address][1])
		self._currentKnownDevices = currentDevices

roleInfo = {
	'format': '1.0',
	'class': BluetoothDiscoverer,
	'author': 'Etienne Perot',
	'version': '1.0',
	'description': 'Discovers Bluetooth devices around the node.',
	'config': {
		'searchDuration': {
			'default': 8,
			'description': 'How long to search for devices.'
		},
		'cooldown': {
			'default': 30,
			'description': 'How long to wait between searches.'
		},
		'log': {
			'default': True,
			'description': 'Whether or not to send a log message every time a device enters or leaves range.'
		}
	}
}