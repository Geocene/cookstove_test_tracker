from __future__ import absolute_import, division, print_function	#, unicode_literals

import sys
import socket
import serial
from collections import namedtuple

import numpy as np

try:
	from SerialTask import SerialTask
except ImportError:
	class SerialTask:
		pass

class OPS3330(SerialTask):
	UnitMeasurementsType = namedtuple('UnitMeasurements',
		'TotalFlow SheathFlow LaserCurrent LaserScatter FlowTemp UnitTemp Humidity AmbientPressure')
	FaultMeasurementsType = namedtuple('FaultMessages',
		'MStatus SystemError MeasurementAlarmed BuzzerAlarmed LaserError ' +
		'FlowError FlowBlocked FlowBlockedStopError CoincidenceError ' +
		'FilterConcentrationWarning BatteryInstalled BatteryCharging ' +
		'BatteryPercentage BatteryLowError ACPluggedIn MemoryPercentage ' +
		'MemoryLowError')
	UserCalSetupType = namedtuple("CalSetup",
		"UserCalEnabled DeadTimeCorrectionEnabled Density " +
		"RefractiveIndexReal RefractiveIndexImaginary ShapeCorrectionFactor")

	#The IP address can be displayed and changed on the front panel.
	#The port seems to be hard coded as 3602.  Since it is the only
	#thing at that IP address, there is not need to change it.
	def __init__(self, host='169.254.110.157', port=3602, verbosity=0):
		if host is None or host == '':
			self.fd = None
		elif 1:
			self.fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			self.fd.settimeout(0.25)
			self.fd.connect((host,port))
			self.fd.settimeout(5.0)
			#self.fd.read = self.fd.recv
			#self.fd.write = self.fd.send
		#SerialTask.SerialTask.__init__(self, self.fd)
		else:
			self.fd = serial.Serial(host, baudrate=9600,
#					bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
					timeout=0.5)

		self.verbosity = verbosity


	def close(self):
		self.fd.close()

	def exchange(self, cmd ):
		if self.verbosity > 0:
			print('OPS3330: Send', cmd)
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
			print('OPS3330: Recv', s)
		return s

	def GetBinEdges(self):
		#TODO: Read this out of the device
		#TODO: What about over/under sized bins
		return self.GetOptimalBinEdges()

	def GetOptimalBinEdges(self):
		nBins = 16
		dMin  = 10**((80        ) / 32)
		dMax  = 10**((80+3*nBins) / 32)
#		dMin, dMax, nBins = 300, 10000, 16
#		print("OPS", nBins, dMin, dMax)
		edges = np.logspace(np.log10(dMin), np.log10(dMax), nBins+1)
		return edges

	def ReadDateAndTime(self):
		s = self.exchange('RSDATETIME')
		print(s)

	def ReadChannelSetupData(self):
		s = self.exchange('RMODECHSETUP')
		print(s)
		return s

	def WriteChannelSetupData(self, edges=None):
		if edges is None:
			edges = self.GetOptimalBinEdges() / 1000
		s = "WMODECHSETUP %d,"% (edges.shape[0]-1) + ','.join("%.3f" % d for d in edges) + ','
		s = self.exchange(s)
		print(s)
		return s

	def ReadUnitMeasurements(self):
		s = self.exchange('RMUNITMEAS')
		values = [float(v) for v in s.split(',')]
		v = self.UnitMeasurementsType(*values)
		return v

	def ReadFaultMessages(self):
		s = self.exchange('RMMESSAGES')
		s1, s2 = s.split('\r\n\r\n')
		#print(repr(s1), repr(s2))
		mStatus = s1
		#There is a trailing comma that needs to be stripped here
		values = [int(v) for v in s2[0:-1].split(',')]
		v = self.FaultMeasurementsType(mStatus, *values)
		return v

	def ReadUserCalibrationSetupData(self):
		s = self.exchange('RMODEUSERCAL')
		values = [eval(v) for v in s.split(',')]
		v = self.UserCalSetupType(*values)
		return v

	def ReadCurrentMeasurement(self):
		s = self.exchange('RMMEAS')
		#Line  0: Time, ?, ?
		#Line  1: 16 dC       values w/ trailing comma
		#Line  2: 16 dN       values w/ trailing comma
		#Line  3: 16 dN/dD    values w/ trailing comma
		#Line  4: 16 dN/dLogD values w/ trailing comma
		#Line  5: 16 dM       values w/ trailing comma
		#Line  6: 16 dM/dD    values w/ trailing comma
		#Line  7: 16 dM/dLogD values w/ trailing comma
		#Line  8: 16 Total dC, Total dN, Total dM
		#Line  9: Sampled > bin 16 ??
		#Manual shows lines 8 and 9 reversed

		parts = s.split('\r\n')
#		for i, p in enumerate(parts):
#			print(i, repr(p))
		ss = parts[4][0:-1]
		dNdLogD = [float(s) for s in ss.split(',')]
		#print(dNdLogD)
		#print()
		return dNdLogD

	def StartMeasurement(self):
		s = self.exchange('MSTART')
		return s

	def StopMeasurement(self):
		s = self.exchange('MSTOP')
		return s

	def ReadLoggingModeSetUpData(self):
		s = self.exchange("RMODELOG")
		print(s)
#		for p in s.split(','):
#			print(p)

	def WriteLoggingModeSetUpData(self, startTime="12:00", startDate="1/1/2014",
			sampleLength="0:1:0", numberOfSamples=1, numberOfSets=1,
			repeatInterval="0:0:1", useStartTime=0, useStartDate=0,
			loggingEnabled=0, logToSingleFile=0, surveyMode=0,
			keepPumpRunning=1):
		args = ','.join(str(s) for s in [startTime, startDate, sampleLength,
							numberOfSamples, numberOfSets,
							repeatInterval, useStartTime, useStartDate,
							loggingEnabled, logToSingleFile, surveyMode,
							keepPumpRunning])
		#print(args)
		s = self.exchange("WMODELOG " + args)
		return s
		#0:0,0/0/0,0:1:0,1,1,0:0:1,0,0,0,0,0,1,

	def CheckFaultState(self, f):
		"""Test if a set of "FaultMessages" Indicates a Real Problem"""
		return np.any(f[1:10])

	def FormatFaultMessages(self, f):
		"""String representation of fault status, ignoring OK items"""
		s = ', '.join("%s=%s" % (f._fields[i], v) for i,v in enumerate(f[1:10],1) if v != 0)
		return s


if __name__ == "__main__":
	import time

	d = OPS3330(host='169.254.110.157', port=3602, verbosity=1)
	#d = OPS3330(host='COM19', port=3602, verbosity=1)
#		edges = d.GetOptimalBinEdges()
#		d.WriteChannelSetupData()
	try:
		#d.ReadDateAndTime()
		d.ReadChannelSetupData()
		#d.ReadUnitMeasurements()
		d.ReadUserCalibrationSetupData()
		#d.ReadLoggingModeSetUpData()
		#d.WriteLoggingModeSetUpData(startTime="13:42", startDate="5/16/2014",
		#				sampleLength="0:0:1",numberOfSamples=9959, numberOfSets=0,
		#				repeatInterval="0:2:46")
		#for i in range(5):
		#	#d.ReadCurrentMeasurement()
		#	print(d.ReadUnitMeasurements())
		#	print(d.ReadFaultMessages())
		#	print()
		#	time.sleep(1)
	finally:
		d.close()