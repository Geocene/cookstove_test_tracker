from __future__ import absolute_import, division, print_function	#, unicode_literals

import time

class TaskList:
	def __init__(self):
		self.Clear()

	def Clear(self):
		self.tasks = []

	def Insert(self, proc, *args, **kwargs):
		self.tasks.insert(0, (proc, args, kwargs))

	def Append(self, proc, *args, **kwargs):
		self.tasks.append((proc, args, kwargs))

	def RunAll(self):
		for proc, args, kwargs in self.tasks:
			#print('%8.3f %r' % (time.clock(), proc))
			proc(*args, **kwargs)

