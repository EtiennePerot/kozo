import os
import sys
from kozo import KozoError

def _importFile(file):
	previousPath = sys.path[:]
	sys.path = [os.path.dirname(file)] + sys.path
	importedFile = __import__(os.path.basename(file)[:os.path.basename(file).rfind('.')])
	sys.path = previousPath
	return importedFile

_roles = {}
def kozoRole(role):
	global _roles
	if role in _roles:
		return _roles[role]
	roleFile = None
	paths = [os.path.dirname(os.path.abspath(__file__))]
	if 'KOZOROLEPATH' in os.environ:
		paths.extend(os.environ['KOZOROLEPATH'].split(':'))
	for path in paths:
		if os.path.isdir(path) and os.path.isfile(path + os.sep + role + '.py'):
			roleFile = path + os.sep + role + '.py'
			break
	if roleFile is None:
		raise KozoError('Could not find role:', role, paths)
	try:
		roleData = _importFile(roleFile)
	except Exception as e:
		raise KozoError('Error while trying to import role', roleFile, e)
	if 'roleInfo' not in roleData.__dict__:
		raise KozoError('roleInfo not found in', roleFile)
	if type(roleData.roleInfo) is not type({}):
		raise KozoError('roleInfo is not a dictionary in', roleFile)
	for key in ('format', 'class', 'config'):
		if key not in roleData.roleInfo:
			raise KozoError(roleFile, '- Key not found in roleInfo:', key)
	if roleData.roleInfo['format'] != '1.0':
		raise KozoError(role, 'has unsupported role format', roleData.roleInfo['format'])
	roleClass = roleData.roleInfo['class']
	roleDefaultConfig = {}
	roleConfigRequired = []
	for key in roleData.roleInfo['config']:
		if 'default' in roleData.roleInfo['config'][key]:
			roleDefaultConfig[key] = roleData.roleInfo['config'][key]['default']
		else:
			roleConfigRequired.append(key)
	roleClass._roleConfig = roleDefaultConfig
	roleClass._roleConfigRequired = roleConfigRequired
	_roles[role] = roleClass
	return roleClass
