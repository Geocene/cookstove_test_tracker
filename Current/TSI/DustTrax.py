from __future__ import absolute_import, division, print_function	#, unicode_literals

import sys
import socket
from collections import namedtuple

import numpy as np

try:
	from SerialTask import SerialTask
except ImportError:
	class SerialTask:
		def __init__(self, fd, handle):
			pass

class DustTrax(SerialTask):
	FaultMessagesType = namedtuple('FaultMessages',
		'SystemError LaserError FlowError FlowBlockedError '
		'MaxConcPM1 MaxConcPM25 MaxConcResp MaxConcPM10 MaxConcTotal ' +
		'FilterConcError '
		'BatteryInstalled BatteryCharging BatteryPercentage BatteryLowError '
		'MemoryPercentageAvailable MemoryLowError')

	#The IP address can be displayed on the front panel.  I am
	#not sure how to chane it.  The port seems to be hard coded
	#as 3602.  Since it is the only thing at that IP address, there
	#is not need to change it
	def __init__(self, host='169.254.119.193', port=3602, verbosity=0):
		if host is None  or host == '':
			self.fd = None
		else:
			self.fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.fd.settimeout(0.25)
			self.fd.connect((host,port))
			self.fd.settimeout(5.0)

		self.verbosity = verbosity
		#SerialTask.SerialTask.__init__(self, self.fd)


	def close(self):
		self.fd.close()

	def exchange(self, cmd ):
		if self.verbosity > 0:
			print('DustTrax: Send', cmd)
		s = cmd + '\r'
		if sys.version_info >= (3,0):
			s = s.encode('Latin-1')
		self.fd.send(s)

		s = self.fd.recv(1000)
		if sys.version_info >= (3,0):
			s = s.decode('Latin-1')
		#Strip off CR/LF at start and end
		#TODO: Check for errors here
		s = s[2:-2]

		if self.verbosity > 0:
			print('DustTrax: Recv', s)
		return s

	def ReadModel(self):
		s = self.exchange('RDMN')
		print(s)

	def ReadSerialNumber(self):
		s = self.exchange('RDSN')
		print(s)

	def ReadDateAndTime(self):
		s = self.exchange('RSDATETIME')
		print(s)

	def StartMeasurement(self):
		s = self.exchange('MSTART')
		return s

	def StopMeasurement(self):
		s = self.exchange('MSTOP')
		return s

#	def ReadChannelSetupData(self):
#		s = self.exchange('RMODECHSETUP')
#		print(s)
#		return s

#	def ReadUnitMeasurements(self):
#		s = self.exchange('RMUNITMEAS')
#		print(s)
#		return s

	def ReadFaultMessages(self):
		s = self.exchange('RMMESSAGES')
		#Need to strip a trailing comma
		values = [int(v) for v in s[0:-1].split(',')]
		return self.FaultMessagesType(*values)

#	def ReadUserCalibrationSetupData(self):
#		s = self.exchange('RMODEUSERCAL')
#		print(s)
#		return s

	def ReadCurrentMeasurements(self):
		s = self.exchange('RMMEAS')
		s = s[:-1]	# strip trailing comma
		values = [float(v) for v in s.split(',')]
		#print(repr(s))
		#print(values)
		return values[1:]

	def ReadCurrentMeasurementsAndStatistics(self):
		s = self.exchange('RMMEASSTATS')
		#Returns 5 lines.  One each for PM1, PM2.5, PM4, PM10, Total
		parts = s.split('\r\n')
		for i, p in enumerate(parts):
			print(i, repr(p))
		print()

	def ZeroMeasurement(self):
		s = self.exchange("MZERO")
		return s

	def ReadZeroingStatus(self):
		s = self.exchange("RMZEROING")
		return s

	def CheckFaultState(self, f):
		"""Test if a set of "FaultMessages" Indicates a Real Problem"""
		return np.any(f[0:10])

	def FormatFaultMessages(self, f):
		"""String representation of fault status, ignoring OK items"""
		s = ', '.join("%s=%s" % (f._fields[i], v) for i,v in enumerate(f[0:10]) if v != 0)
		return s

if __name__ == "__main__":
	import time
	d = DustTrax(host='169.254.119.193', port=3602, verbosity=0)
	try:
		d.ReadModel()
		d.ReadSerialNumber()
		d.ReadDateAndTime()
		#d.ReadChannelSetupData()
		#d.ReadUnitMeasurements()
		#d.ReadUserCalibrationSetupData()
		#d.ReadChannelSetupData()
		#d.StartMeasurement()
		#d.ReadUnitMeasurements()
		#print(repr(d.ReadFaultMessages()))

#		print(d.ZeroMeasurement())
#		for i in range(100):
#			time.sleep(1)
#			print(d.ReadZeroingStatus())

#			for i in range(5):
#				print(d.ReadCurrentMeasurements())
#				#d.ReadCurrentMeasurementsAndStatistics()
#				time.sleep(1)
#				print(repr(d.ReadFaultMessages()))
		#d.StopMeasurement()
	finally:
		d.close()
