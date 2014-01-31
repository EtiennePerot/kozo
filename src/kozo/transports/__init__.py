import os
import sys
from kozo import KozoError, kozoConfig, NODE_NAME, TRANSPORT_NAME
from kozo.helpers import importFile as _importFile

_transports = {}
def kozoTransport(transport, transportName, nodeName):
	global _transports
	if transport in _transports:
		return _transports[transport]
	transportFile = None
	paths = [os.path.dirname(os.path.abspath(__file__))]
	if 'KOZOTRANSPORTPATH' in os.environ:
		paths.extend(os.environ['KOZOTRANSPORTPATH'].split(':'))
	if kozoConfig('transportPath'):
		paths.extend(kozoConfig('transportPath').split(':'))
	for path in paths:
		if os.path.isdir(path) and os.path.isfile(path + os.sep + transport + '.py'):
			transportFile = path + os.sep + transport + '.py'
			break
	if transportFile is None:
		raise KozoError('Could not find transport:', transport, paths)
	importPaths = kozoConfig('importPath').split(':')
	if 'KOZOIMPORTPATH' in os.environ:
		importPaths.extend(os.environ['KOZOIMPORTPATH'].split(':'))
	try:
		transportData = _importFile(transportFile, extraPaths=filter(lambda p: p, importPaths))
	except BaseException as e:
		raise KozoError('Error while trying to import transport', transportFile, e)
	if 'transportInfo' not in transportData.__dict__:
		raise KozoError('transportInfo not found in', transportFile)
	if type(transportData.transportInfo) is not type({}):
		raise KozoError('transportInfo is not a dictionary in', transportFile)
	for key in ('format', 'class', 'config'):
		if key not in transportData.transportInfo:
			raise KozoError(transportFile, '- Key not found in transportInfo:', key)
	if transportData.transportInfo['format'] != '1.0':
		raise KozoError(transport, 'has unsupported transport format', transportData.transportInfo['format'])
	transportClass = transportData.transportInfo['class']
	transportDefaultConfig = {}
	transportConfigRequired = []
	for key in transportData.transportInfo['config']:
		if 'default' in transportData.transportInfo['config'][key]:
			default = transportData.transportInfo['config'][key]['default']
			if default is NODE_NAME:
				default = nodeName
			elif default is TRANSPORT_NAME:
				default = transportName
			transportDefaultConfig[key] = default
		else:
			transportConfigRequired.append(key)
	transportClass._transportConfig = transportDefaultConfig
	transportClass._transportConfigRequired = transportConfigRequired
	_transports[transport] = transportClass
	return transportClass
