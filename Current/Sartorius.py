from __future__ import absolute_import, division, print_function	#, unicode_literals

import sys

import numpy as np
import serial

import SerialTask

class Combics1(SerialTask.SerialTask):
	def __init__(self, port, verbosity=0):
		if port is None  or  port == '':
			self.fd = None
			SerialTask.SerialTask.__init__(self, self.fd, None)
		else:
			self.fd = serial.Serial(port, baudrate=1200,
					bytesize=serial.SEVENBITS, parity=serial.PARITY_ODD,
					timeout=2.5)
			self.fd.flushInput()
			SerialTask.SerialTask.__init__(self, self.fd)
		self.verbosity = verbosity

	def close(self):
		self.fd.close()

	def readline(self, eol=b'\r\n'):
		s = b''
		while 1:
			c = self.fd.read(1)		#TODO: unicode .decode('ASCII')
			if c == '':
				break
			s += c
			if s.endswith(eol):
				break
		if sys.version_info > (3,0):
			s = s.decode('Latin-1')
		return s

	def ask(self, cmd):
		if self.verbosity > 0:
			print("Satorius.Combics1 %s -> " % cmd, end='')
		#We don't seem to actually need the \r\n at the end at all
		self.fd.write(b'\x1b' + cmd + b'\r\n')
		s = self.readline()
		if self.verbosity > 0:
			print(repr(s))
		assert(s.endswith('\r\n'))
		s = s[:-2]		# Strip \r\n
		return s

	def GetInformation(self):
		#Returns "CAIS1/01-61-08/1\r\n"
		s = self.ask(b'i_')
		return s

	def GetValue(self):
		s = self.ask(b'P')
		if len(s) != 20:
			print(len(s), repr(s))
			return '', np.nan, ''
		#assert(s.endswith("  "))
		hdr = s[0:6].strip()
		sign = s[6]
		value = s[7:7+8+1]
		units = s[7+8+1:7+8+1+3].strip()
		#print(repr(hdr), repr(sign), repr(value), repr(units))
		value = float(value)
		if sign == '-':
			value = -value;
		if units == '':
			value = np.nan
		return hdr, value, units

#	def TareAndZero(self):
#		self.fd.write(b"D")

	def Zero(self):
		self.fd.write(b"\x1b" + b"f3_")

	def Tare(self):
		self.fd.write(b"\x1b" + b"f4_")


if __name__ == "__main__":
	import time
	import msvcrt
	import os.path

	def logger(scale):
		fileName = raw_input("Enter filename: ")
		pathName = "C:\\Users\\Gadgil Lab Stoves\\Desktop\\Dropbox\\75C Lab Dropbox Folder\\Satorius\\" + fileName
		if os.path.exists(pathName):
			print("File already exists.  Please delete first")
			return
		f = open(pathName, "w")
		print("Press any key to stop")
		while not msvcrt.kbhit():
			hdr, value, units = scale.GetValue()
			s = time.strftime("%H:%M:%S", time.localtime(time.time()))
			if units != '':
				s += "\t%3s\t%8.1f\t%s" % (hdr, value, units)
			print(s)
			f.write(s + "\n")
			time.sleep(0.8)
		f.close()
		msvcrt.getch()

	d = Combics1(port='COM7', verbosity=1)
	try:
		if 0:
			logger(d)
		else:
			print(d.GetInformation())
			#print(d.GetValue())
			#w/o any sleeps, this runs at about 0.3 to 0.4 seconds per reading
			#while not msvcrt.kbhit():
#			print(d.TareAndZero())
			print(d.Tare())
#			time.sleep(3)
#			print(d.Zero())
#			time.sleep(2)

#			last = time.clock()
#			while not msvcrt.kbhit():
#				s = d.GetValue()
#				t = time.clock()
#				print("%8.3f %5.3f" % (t, t-last), repr(s))
#				last = t
#				#break
#				#time.sleep(0.8)
#			#msvcrt.getch()
	finally:
		d.close()
