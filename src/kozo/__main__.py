import os
import sys
import yaml
if len(sys.argv) != 3:
	sys.stderr.write('Usage: ' + sys.argv[0] + ' config.json localNode\n')
	sys.exit(1)
if not os.path.isfile(sys.argv[1]):
	sys.stderr.write('Config file does not exist: ' + sys.argv[1] + '\n')
	sys.exit(2)
try:
	config = yaml.load(open(sys.argv[1], 'r').read(-1))
except:
	sys.stderr.write('Invalid JSON file: ' + sys.argv[1] + '\n')
	sys.exit(3)
if sys.argv[2] not in config['system']:
	sys.stderr.write('Node ' + sys.argv[2] + ' is not defined in the configuration file.\n')
	sys.exit(4)
from .kozo import kozo
kozo(config, sys.argv[2])
