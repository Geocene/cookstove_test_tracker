from __future__ import absolute_import, division, print_function	#, unicode_literals

import sys
import time
from collections import namedtuple

import numpy as np
import serial
import SerialTask

class Aethalometer(SerialTask.SerialTask):
	#TODO: Flow vs UV ???
	valuesType = namedtuple('AethalometerValuesType',
					'date time conc1 conc2 flow ' +
					'sz1 sb1 rz1 rb1 fract1 atten1 '
					'sz2 sb2 rz2 rb2 fract2 atten2')

	def __init__(self, port='COM8', verbosity=0):
		if port is None  or  port == '':
			self.fd = None
			SerialTask.SerialTask.__init__(self, self.fd)
		else:
			self.fd = serial.Serial(port, baudrate=9600,
					bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
					timeout=12.5)
			SerialTask.SerialTask.__init__(self, self.fd)
			self.fd.flushInput()
		self.verbosity = verbosity
		#self.first = True

	def close(self):
		self.fd.close()

	def readline(self, eol=b'\n'):
		#if self.first:
		#	self.first = False
		#	raise UnicodeDecodeError('xxx')
		s = b''
		while 1:
			c = self.fd.read(1)		#TODO: Unicode .decode('ASCII')
			if c == '':
				break
			s += c
			if s.endswith(eol):
				break
		if sys.version_info >= (3,0):
			s = s.decode('Latin-1')
		return s

	def GetValues(self):
		s = self.readline()
		#print(s)
		#s = '"20-aug-13","13:59:30",  1313,   621,  1.4, 0.0216, 3.1055, 0.0217, 2.1570, 1.00,   .312, 0.0216, 1.7909, 0.0217, 1.3037, 1.00,   .811\r\n'
		#print('Aethalometer', repr(s))
		if not s.endswith("\r\n"):
			print("Aethalometer: Bad string %d %r\n" % (len(s),s), end='')
			return self.valuesType(*(["?","?"] + [-1]*15))
		v = s[0:-2].split(',')
		if len(v) != 17  and len(v) != 10:
			print("Aethalometer: Bad string %d %r\n" % (len(s),s), end='')
			return self.valuesType(*(["?","?"] + [-1]*15))
		for i in range(2):
			v[i] = v[i][1:-1]
		for i in range(2,len(v)):
			v[i] = float(v[i])

		#If UV source is turned off, none of the "2" values are transmitted
		#Move the other values around put them in the slots they would be in
		#if the UV source was on, and fill the missing values with something
		#TODO: Decide on the best fill value. Nan's do not trigger the UI
		#alarm limits at the moment, and should not, at least for the Satorious,
		#where we will have missing values regularly.
		if len(v) == 10:
			#v.insert(3, np.nan)
			#v += [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan]
			v.insert(3, -1)
			v += [-1, -1, -1, -1, -1, -1]
		values = self.valuesType(*v)
		#print(values)
		return values

if __name__ == "__main__":
	d = Aethalometer(verbosity=1)
	try:
		for i in range(2):
#			s = d.readline()
#			print(len(s), repr(s))
			print(d.GetValues())
	finally:
		d.close()