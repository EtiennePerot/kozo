from .timer import Timer as _Timer
from .cuckoo import Cuckoo as _Cuckoo

_roles = {
	'timer': _Timer,
	'cuckoo': _Cuckoo
}

def kozoRole(type):
	return _roles[type]
