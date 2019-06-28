from __future__ import absolute_import, division, print_function	#, unicode_literals

import sys
import serial
import SerialTask

class Scale(SerialTask.SerialTask):
	def __init__(self, port='COM6', serialNo=1, verbosity=0):
		if port is None  or  port == '':
			self.fd = None
			SerialTask.SerialTask.__init__(self, self.fd, None)
		else:
			self.fd = serial.Serial(port, baudrate=9600,
					bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
					timeout=2.5)
			SerialTask.SerialTask.__init__(self, self.fd)
		self.verbosity = verbosity
		self.serialNo = serialNo
		self.verbosity = verbosity

	def close(self):
		self.fd.close()

	def exchange(self, cmd):
		cmd = chr(self.serialNo) + cmd
		if self.verbosity > 0:
			print("AWS.SCcale:Write %r" % cmd)
		s = cmd + '\r'
		if sys.version_info >= (3,0):
			s = s.encode('Latin-1')
		self.fd.write(s)
		reply = self.fd.read(13)
		if sys.version_info >= (3,0):
			reply = reply.decode('Latin-1')
		reply = reply[1:12]
		if self.verbosity > 0:
			print("AWS.Scale:Read %r" % reply)
		return reply

	def RequestWeightData(self):
		s = self.exchange('s')
		s = s.rstrip()
		s = s[0:-1]		# Strip unit string
		try:
			v = float(s)
		except ValueError:
			print("AWS Request Weight Data returned %r\n" % s, end='')
			v = np.nan
		return v


if __name__ == "__main__":
	import time

	d = Scale(serialNo=1, verbosity=1)
	try:
		while 1:
			print(repr(d.RequestWeightData()))
			time.sleep(0.1)
	finally:
		d.close()
