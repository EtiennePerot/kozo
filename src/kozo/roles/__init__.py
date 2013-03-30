from .timer import Timer as _Timer

_roles = {
	'timer': _Timer
}

def kozoRole(type):
	return _roles[type]
