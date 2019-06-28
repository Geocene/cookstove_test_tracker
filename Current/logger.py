from __future__ import absolute_import, division, print_function	#, unicode_literals

import os

class Logger:
	def __init__(self):
		#self.open(pathName, mode)
		self.delim = ','
		self.ClearItems()

#	def __del__(self):
#		if self.file is not None:
#			self.close()

	def open(self, pathName, mode="w"):
		self.file = open(pathName, mode)
		self.pathName = pathName
		self.nextWrite = 0

	def close(self):
		self.file.close()
		self.file = None

	def ClearItems(self):
		self.logItems = []

	def AddItem(self, label, units, fmt, fct):
		self.logItems.append((label, units, fmt, fct))

#	def AddItems(self, items):
##		self.logItems = logItems
#		for item in items:
#			assert(len(item) == 3)
#		self.logItems = self.logItems + items

	def Start(self, skipLine=False):
		hdr1 = self.delim.join(label for (label, units, fmt, fct) in self.logItems)
		hdr2 = self.delim.join(units for (label, units, fmt, fct) in self.logItems)
#		print("Logger:", hdr)
		self.file.seek(0, os.SEEK_END)
		if self.file.tell() == 0:
			self.file.write(hdr1 + "\n");
			self.file.write(hdr2 + "\n");
		elif skipLine:
			self.file.write("\n");

	def Write(self):
#		s = self.delim.join(fmt % fct() for (label, units, fmt, fct) in self.logItems)
		items = []
		for label, units, fmt, fct in self.logItems:
			try:
				item = fmt % fct()
			except AttributeError as e:
				item = "???"
				print("Logger.Write", e)
			items.append(item)
		s = self.delim.join(items)
#		print("Logger:", s)
		self.file.write(s + "\n");
		self.file.flush()
