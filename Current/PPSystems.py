from __future__ import absolute_import, division, print_function	#, unicode_literals

from collections import namedtuple

import sys
import numpy as np
import serial

import SerialTask

class SBA5(SerialTask.SerialTask):
	measurementType = namedtuple('SBA5Measurement',
				'ZeroCounts CurrentCounts Measured AverageTemp Humidity ' +
				'HumiditySensorTemp Pressure DetectorTemp SourceTemp Errors')

	def __init__(self, port='COM18', verbosity=0):
		if port is None  or port == '':
			self.fd = None
			SerialTask.SerialTask.__init__(self, self.fd)
		else:
			self.fd = serial.Serial(port, baudrate=19200,
					bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
					timeout=2)
			SerialTask.SerialTask.__init__(self, self.fd)
		self.verbosity = verbosity

	def close(self):
		self.fd.close()

	def write(self, s):
		self.fd.flush()
		if sys.version_info > (3,0):
			s = s.encode('Latin-1')
		self.fd.write(s)

	#TODO: Figure out if there is really a default eol for the SBA 5
	def readline(self, eol): #='\x00'):
#		print([ord(c) for c in eol])
		s = b''
		while 1:
			c = self.fd.read(1)
			if c == b'':
				break
			s += c
#			print([ord(c) for c in s])
			if s.endswith(eol):
				break
#		print("SBA5: %r" % s)
		if sys.version_info >= (3,0):
			s = s.decode('Latin-1')
		return s

	#def SetMeasurementFormat(self, mask)

	def Zero(self):
		self.write("Z\r")
		s = self.readline(eol=b'\r\x00')
		expected = "Z\x00\r\x00"
		if s == expected:
			return "Ok"
		else:
			#print("SBA5 Zero -> %r" % (s))
			return repr(s)

	def SetLowAlarmLimit(self, loLimit):
		self.write("L%s\r" % loLimit)
		while 1:
			s = self.readline(eol=b'\r\n\x00')
			if s.startswith('M ')  or s.startswith('Z ')  or s.startswith('W,'):
				#print("SBA5 flushing", s)
				continue
			break
		expected = "L\x00%s\x00\r\x00\r\nOk\r\n\x00" % loLimit
		if s == expected:
#			print("SBA5 Set Alarm Limit %g -> Ok" % loLimit)
			return "Ok"
		else:
#			print("SBA5 Set Alarm Limit %g -> %r" % (loLimit, s))
			return repr(s)

	def GetRecord(self):
		#Each line seems to be terminated by a \r\n\x00
		#Returns a named tuple(or None) and a msg (or None)
		s = self.readline(b"\r\n\x00")
		#print(repr(s))
		if s.startswith(" W")  or s.startswith(" Z"):
			#Warmup or Zero
			return None, s[1:-3]
		elif s.startswith('M'):
			assert(s.endswith("\r\n\x00"))
			org = s
			#Strip off the "M " at the beginning and the "\r\r\x00" at the end
			s = s[2:-3]
			#I am guessing that multiple errors might appear on separate lines.
			#This logic will replace it one line separated by semicolons.
			#It is fine if it is simply a single message
			lines = s.split("\r\n",1)
#			print(lines)
			errorMsg = lines[1][1:].replace("\r\n", ";") if len(lines) == 2 else ''
			fields = lines[0].split()
			if len(fields) != 9:
				#The manual indicates there should always be an error/status
				#I might need to enable it manually with the "F" command
				#value at the end
				#print("SBA5: Measurement info format error %r" % s)
				return None, "Format Error %r" % org
				#return
			#print('SBA5', repr(fields))
#			values = [np.inf if v == 'fp_overflow' else float(v) for v in fields]
			values = []
			for v in fields:
				try:
					value = np.inf if v == 'fp_overflow' else float(v)
				except ValuesError as e:
					print('SBA5', repr(fields))
					print('SBA5', repr(value))
					value = np.nan
				values.append(value)
			values.append(errorMsg)
			#print(v)
			#print(values, repr(errorMsg))
			v = self.measurementType(*values)
			return v, None
		else:
			#print("SBA5: Measurement info format error %r" % s)
			#TODO: Return real error.  It might be multiple lines long
			return None, "Format Error %r" % s

if __name__ == "__main__":
	d = SBA5('COM12', verbosity=1)
	d.SetLowAlarmLimit(0)
	try:
		for i in range(10):
			print(d.GetRecord())
	finally:
		d.close()
