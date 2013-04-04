import os
import random
import sys
import time

def importFile(file):
	previousPath = sys.path[:]
	sys.path = [os.path.dirname(file)] + sys.path
	importedFile = __import__(os.path.basename(file)[:os.path.basename(file).rfind('.')])
	sys.path = previousPath
	return importedFile

def randomWait(upTo, sleepFunction=time.sleep):
	return sleepFunction(random.uniform(0, upTo))
