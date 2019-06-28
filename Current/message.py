from __future__ import absolute_import, division, print_function	#, unicode_literals

import sys
import time

import wx

class MessageLogger:
	def __init__(self):
		pass

	def open(self, pathName, mode="w"):
		self.file = open(pathName, mode)
		self.pathName = pathName
		self.nextWrite = 0

	def close(self):
		self.file.close()
		del self.file

	#TODO: What is happening with the doecho stuff ???
	def LogMessage(self, category, msg, doecho=True):
		#TODO: What if there are tabs or newlines or the like in msg???
		s = '\t'.join([time.strftime("%H:%M:%S"), category, msg]) + '\n'
		if doecho:
			sys.stdout.write(s.replace('\t', '  '))
		if hasattr(self, 'file'):
			self.file.write(s)

