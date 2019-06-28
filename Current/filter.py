from __future__ import absolute_import, division, print_function	#, unicode_literals

import time

#
# Filter:  Moving average filter, based on number of samples
# of maximum duration in seconds.  Output is unweighted mean.
#

class Moving:
	def __init__(self, size=None, duration=None):
		self.size = size
		self.duration = duration
		self.flush()

	def flush (self):
		self.accum = 0
		self.data = []

	def AddValue(self, value):
		now = time.clock()
		value = float(value)
		self.data.append((now, value))
		self.accum = self.accum + value
		if self.size is not None:
			while (len(self.data) > self.size):
				#print("Pop size: %d %s" % (len(self.data), self.data[0]))
				self.accum = self.accum - self.data.pop(0)[1]
		if self.duration is not None:
			while self.data[0][0] < now - self.duration:
				#print("Pop time: %s %s" % (now, self.data[0]))
				self.accum = self.accum - self.data.pop(0)[1]
#		print('filter', self.data)
		return self.GetValue()


class MovingMean(Moving):
	def GetValue(self):
		return self.accum / len(self.data)


class MovingMedian(Moving):
	def GetValue(self):
		values = [v for t,v in self.data]
		return values[len(values) // 2]


if __name__ == '__main__':
	f = Filter(size=None, duration=1e-3)
	for i in range(20):
		v = f.AddValue(i)
		print(v,f.accum,f.data)

