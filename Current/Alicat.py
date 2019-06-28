#
#
from __future__ import absolute_import, division, print_function	#, unicode_literals///////

import sys
import time
from collections import namedtuple

import serial
import SerialTask

class MSeries(SerialTask.SerialTask):
	valuesType = namedtuple('AlicatValuesType', 'P T Flow StdFlow, Setpoint Gas')

	def __init__(self, port, verbosity=0):
		if port is None  or  port == '':
			self.fd = None
			SerialTask.SerialTask.__init__(self, self.fd, None)
		else:
			self.fd = serial.Serial(port, baudrate=19200,
					bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
					timeout=0.5)
			SerialTask.SerialTask.__init__(self, self.fd, None)
		self.verbosity = verbosity
		self.maxFlow = 100

	def close(self):
		self.fd.close()

	def readline(self, eol=b'\r'):
		s = b''
		while 1:
			c = self.fd.read(1)			# TODO unicode .decode('ASCII')
			if c == b'':
				break
			s += c
			if s.endswith(eol):
				break
		if sys.version_info >= (3,0):
			s = s.decode('ASCII')
		return s

	def ask(self, cmd):
		if self.verbosity > 0:
			print("Alicat.MSeries %s -> " % cmd, end='')
		if sys.version_info >= (3,0):
			cmd = cmd.encode('ASCII')
		self.fd.write(cmd + b'\r')
		s = self.readline()
		if self.verbosity > 0:
			print(repr(s))
		#assert(s.endswith('\r')
		#s = 'a' + s[1:]

		#s = s[:-1]
		return s

	def SetRange(self, maxFlow):
		self.maxFlow

	def GetValues(self):
		# 30 milliseconds
		s = self.ask('A')
		#Figure out best way to avoid making ask return the terminator
		if not s.startswith("A")  or  not s.endswith("\r"):
			print("Alicat: Bad reply %r" % s)
			return self.valuesType(-1, -1, -1, -1, -1, "?")

		#assert(s.startswith("A"))

		w = s.split()
		for i in range(1,6):
			w[i] = float(w[i])
#		v = self.valuesType(P=w[1], T=w[2],	MDot1=w[3], MDot2=w[4], MDot3=w[5],
#							Gas=w[6])
		v = self.valuesType(*w[1:])
		return v

	def SetSetpoint(self, value):
#		s = self.ask("AS%.1f" % value)
		value = 64000 * value / self.maxFlow
		s = self.ask("A%d" % value)
		return s


if __name__ == "__main__":
	import os
	import msvcrt

	def logger(alicat):
		fileName = raw_input("Enter filename: ")
		pathName = "C:\\Users\\Gadgil Lab Stoves\\Desktop\\Dropbox\\75C Lab Dropbox Folder\\Alicat\\" + fileName
		if os.path.exists(pathName):
			print("File already exists.  Please delete first")
			return
		f = open(pathName, "w")
		print("Press any key to stop")
		while not msvcrt.kbhit():
			d = alicat.GetValues()
			s = time.strftime("%H:%M:%S", time.localtime(time.time()))
			s += "\t%5.2f\t%5.2f\t%6.1f\t%6.1f\t%6.1f\t%s" % \
				(d.P, d.T, d.Flow, d.StdFlow, d.Setpoint, d.Gas)
			print(s)
			f.write(s + "\n")
			time.sleep(0.97)
		f.close()

	#Serial Octopus Cable Connector 1
	d = MSeries(port='COM7', verbosity=1)
	d.SetRange(100)
	try:
		print('xxx', d.SetSetpoint(50))
#		d.SetSetpoint(0.1)
#		d.SetSetpoint(4.5)
		for i in range(2):
			start = time.clock()
			print(d.GetValues(), time.clock()-start)
#		logger(d)
	finally:
		d.close()
