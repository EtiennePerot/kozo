from .ssh import SSHTransport as _SSHTransport

_transports = {
	'ssh': _SSHTransport
}

def kozoTransport(type):
	return _transports[type]
