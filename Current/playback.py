#
# 
from __future__ import absolute_import, division, print_function

import warnings

warnings.simplefilter('once', UserWarning)

class Playback:
	def __init__(self, pathName):
		self.file = open(pathName, "rU")
		hdr1 = self.file.readline()	# Header 1
		hdr2 = self.file.readline()	# Header 2
		self.names = hdr1.strip().split(',')

	def readline(self):
		self.line = self.file.readline()
		self.values = self.line[0:-1].split(',')

	def getvalue(self, fct, *names):
		for name in names:
			if name in self.names:
				i = self.names.index(name)
				v = self.values[i]
				break
		else:
			#print("{} not in playback file".format(names))
			warnings.warn("{} not in playback file".format(names))
			v = "NaN"
		v = fct(v)
		return v
