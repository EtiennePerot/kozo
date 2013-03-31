from .tcp import TCPTransport as _TCPTransport

_transports = {
	'tcp': _TCPTransport
}

def kozoTransport(type):
	return _transports[type]
