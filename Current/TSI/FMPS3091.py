#
#
#
from __future__ import absolute_import, division, print_function

import sys
import time
from collections import namedtuple

import serial
import numpy as np

try:
	from SerialTask import SerialTask
except ImportError:
	class SerialTask:
		def __init__(self, fd, handle):
			pass

class FMPS3091(SerialTask):
	# There are two different RDR7 record types.  The first is a numpy structured
	# array and the second is a namedtuple.  Numpy expects to have an an array
	# at the top level, meaning everyting needs to be indexed with an extra [0]
	# as there is only one of these objects.  I use np to do the read and then
	# convert to a namedtuple afterwords to avoid the extra indexing.
	RDR7dtype = [
		('UCode',				'|S1'			),
		('PackageSize',			'<u2'			),
		('CheckSum',			'<3u2'			),
		('ElapsedTime',			'<u2'			),
		('InstrumentStatus',	'<u2'			),
		('InstrumentError',		'<u8'			),
		('Data',				'<(10,33)f4'	),
		('ErrorCodes',			'<10u4'			),
		('ResetCodes',			'<10u4'			),
		('SheathTemperature',	'<i2'			),	#??? u2
		('AbsolutePressure',	'<i2'			),	#??? u2
		('AnalogInput1',		'<10u2',		),
		('AnalogInput2',		'<10u2',		),
		('Elm',					'<(10,22)u4'	),
		('CR',					'|S1'			)
	]
	RDR7Type = namedtuple('RDR7Type', [name for name,fmt in RDR7dtype])

	StatusRecordType = namedtuple('StatusRecord',
				'ErrorCode1 ErrorCode2 StatusCode ' +
				'SheathFlow SampleFlow ChargerFlow ExtractionFlow AbsolutePressure ' +
				'AnalyzerVoltageTop AnalyzerVoltageMiddle AnalyzerVoltageBottom ' +
				'SheathFlowTemp  '
				'NegChargerCurrent PosChargerCurrent NegChargerVoltage PosChargerVoltage ' +
				'AnalogInput1 AnalogInput2')

	#As of 2014.04.04, COM10 is Octopus Connector 4
	def __init__(self, port='COM10', verbosity=0):
#		print('FMPS391', port)
		if port is None  or  port == '':
			self.fd = None
			SerialTask.__init__(self, self.fd, None)
		else:
			self.fd = serial.Serial(port, baudrate=38400,
					bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
					timeout=2.5)
			self.fd.write(b"RDR,0\r")
			self.fd.flushInput()
			SerialTask.__init__(self, self.fd, None)

		self.verbosity = verbosity


	def close(self):
		self.fd.close()

	def readline(self, eol=b'\n'):
		assert isinstance(eol, bytes)
		s = b''
		while 1:
			#TODO: This device mixes ASCII and binary.  I get errors sometimes
			#when this sees binary data.  Need to clean it up somehow to
			#work w/ Python 3.x, which will require a decode here.
			c = self.fd.read(1)
			if c == b'':
				break
			s += c
			if s.endswith(eol):
				break
		if sys.version_info >= (3,0):
			s = s.decode('Latin-1')
		return s

	# Multiple lines, if present, are separated by \r's, and there are two
	# \r's at the end
	def exchange(self, cmd, eol=b'\r\r'):
		self.fd.flushInput()
		if self.verbosity > 0:
			print(time.clock())
			print("FMPS3091:Write %s" % cmd)
		s = cmd + '\r'
		if sys.version_info >= (3,0):
			s = s.encode('Latin-1')
		self.fd.write(s)
		reply = self.readline(eol)
		if self.verbosity > 0:
			print(time.clock())
			print("FMPS3091:Read %r" % reply)
		#Strip eol
		reply = reply[0:-len(eol)]
		return reply

	def GetBinEdges(self):
		#TODO: Deal with under/over size bin, if one exists
		#Setup for 33 bins, spaced at 32/2 bins per decade.
		#Need to understand the oversize bin later
		nBins = 33
		dMin  = 10**((24        ) / 32)
		dMax  = 10**((24+2*nBins) / 32)
#		print("FMPS", nBins, dMin, dMax)
		edges = np.logspace(np.log10(dMin), np.log10(dMax), nBins+1)
		edges[-1] = np.inf
		return edges

	def ReadTemperature(self):
		#w/o the ,# at the end this returns multiple lines
		#The entire set of lines is terminated by an empty line,
		#meaning two \r's in a row.  This is also true of the
		#ReadPressure command and probably others as well!!
		#Only returns a
		self.exchange("RT,#")

	def ReadPressure(self):
		self.exchange("RP,#")

	def ReadAnalogInput(self):
		self.exchange("RAI,#")

	def ReadSEM(self):
		#Returns an empty string
		self.exchange("SEM")

	def SetSDS(self, n):
		#Return ?
		self.exchange("SDS,%s" % n)

	def SetFlow(self, mode):
		if True or mode == 'on':
			return self.exchange("SF,%s" % mode, b"\r")
		else:
			#There is a serious issue about buffer flushing when the program
			#ends.  This the last command executed in the program.
			#Simply ignore the return value for now
			#self.fd.flushInput()
			self.fd.write(b"SF,off\r")
			return "?"

	def ZeroElectrometers(self):
		reply = self.exchange("SELM,ZERO", eol=b'\r\r')
		print("FMPS3091: Zero Electrometers#1", reply)
		time.sleep(0.2)
		reply = self.exchange("YES", eol=b'\r')
		print("FMPS3091: Zero Electrometers#2", reply)
		for i in range(60):
			reply = self.readline(eol=b"\r")
			if reply.endswith('\r'):
				reply = reply[0:-1]
			print("FMPS3091: Zero Electrometers#3", reply)
			if reply == 'OK':
				break
		else:
			print("FMPS3091: Zero Electrometers timeout")

	def ReadRSR(self):
		reply = self.exchange("RSR,#", eol=b'\r')
		values = [int(s) if i < 2 else float(s) for i,s in enumerate(reply.split(','))]
		v = self.StatusRecordType(*values)
		return v

	def ReadRDR4(self):
		#Returns an empty string
		self.exchange("RDR,4")
		for i in range(20):
			reply = self.readline('\r')
			#Strip \r at end.
			reply = reply[0:-1]
			if self.verbosity > 0:
				print("FMPS3091:Read %r" % reply)
		self.exchange("RDR,0")
		self.fd.flushInput()

	def ReadRDR3(self):
		self.fd.flushInput()
		self.fd.write(b"RDR,3\r")
		for i in range(5):
#			print("Record")
			bytes = self.fd.read(3226)

#			print(len(bytes))
##			print('%s' % bytes)
#			for byte in bytes[0:10]:
#				print("%02x" % ord(byte), end=' ')
#			print("")

#			for group in range(10):
##				print("Group %2d:" % group)
#				n = 21 + 4*33*group
#				v = struct.unpack("<33f",bytes[n:n+4*33])
#				#Manual says these are dNdLogP, but they are really dN.
#				#The 16 is 32 bins divided by 2 decades
#				#Last bin always seems to have zero in it
##				for vi in v:
##					print("%6.0f" % 16*vi, end=' ')
##				print()
#			print()
		dNdLogP = np.frombuffer(bytes, np.float32, 330, 21)
		dNdLogP.shape = (33,10)
		print(dNdLogP)

		self.fd.write(b"RDR,0\r")
		self.fd.flushInput()

	def ReadRDR7(self):
		N = 2346
		self.fd.flushInput()
		self.fd.write(b"RDR,7\r")
		bytes = self.fd.read(N)
		self.fd.write(b"RDR,0\r")

#			print(len(bytes))
#			print('%s' % bytes)
#			for byte in bytes[0:10]:
#				print("%02x" % ord(byte), end=' ')
#			print("")

#			for group in range(10):
##				print("Group %2d:" % group)
#				n = 21 + 4*33*group
#				v = struct.unpack("<33f",bytes[n:n+4*33])
#				for vi in v:
#					print("%6.0f" % (vi*16), end=' ')
#				print()
#				print(sum(v))
#			print()

#		print(len(bytes))
		if len(bytes) != N:
			print("FMPS3091: Wrong buffer length for RDR,7: %d bytes" % len(bytes))
			self.fd.write(b"RDR,0\r")
			self.fd.flushInput()
			dNdLogDp = np.zeros(33, np.float32)
			return dNdLogDp

		#Empirically, the checksum seems to be the total of all the bytes
		#starting after the checksum itself, and not including the terminating
		#carriage return.

		if 1:
			d = np.frombuffer(bytes, dtype=self.RDR7dtype)
			v = self.RDR7Type(*d[0])
			assert v.PackageSize == N, 'FMPS3091 RDR7 Package size mismatch'
			sum1 = np.sum(np.frombuffer(bytes, np.uint8)[9:-1])
			sum2 = ((v.CheckSum[2] * 65536) + v.CheckSum[1]) * 65536 + v.CheckSum[0]
			assert sum1 == sum2, 'FMPS3091 RDR7 Checksum mismatch'
			assert v.CR == b'\r', 'FMPS3091 RDR7 termination character wrong'
			dNdLogDp = v.Data.mean(axis=0)
			#TODO: Deal w/ oversize bin
			dNdLogDp *= 16
			v = v._replace(SheathTemperature=v.SheathTemperature/10.0,
						   AbsolutePressure =v.AbsolutePressure/10.0,
						   Data=dNdLogDp)
		else:
			sum1 = np.sum(np.frombuffer(bytes, np.uint8)[9:-1])
			packageSize = np.frombuffer(bytes, np.int16,  1,  1)
			checksum    = np.frombuffer(bytes, np.uint8,  6,  3)
			sum2 = ((checksum[2] * 256) + checksum[1]) * 256 + checksum[0]
			assert sum1 == sum2, 'FMPS3091 Checksum mismatch'
			assert packageSize == N, 'FMPS3091 Package size mismatch'

			elapsedTime = np.frombuffer(bytes, np.int16,  1,  9)[0]
			instStatus  = np.frombuffer(bytes, np.int16,  1, 11)[0]
			instError   = np.frombuffer(bytes, np.int64,  1, 13)[0]

			dNdLogDp = np.frombuffer(bytes, np.float32, 330, 21)
			dNdLogDp.shape = (10,33)
			dNdLogDp = dNdLogDp.mean(axis=0)
			#TODO: Deal w/ oversize bin
			dNdLogDp *= 16

			errorCodes = np.frombuffer(bytes, np.int32,   10, 21+330*4)
			resetCodes = np.frombuffer(bytes, np.int32,   10, 21+330*4+40)
			sheathTemp = np.frombuffer(bytes, np.int16,    1, 21+330*4+40+40)[0] / 10.0
			absPress   = np.frombuffer(bytes, np.int16,   1, 21+330*4+40+40+2)[0] / 10.0
	#		print('FMPS', sum, sum2, elapsedTime, hex(instStatus), instError, errorCodes, resetCodes, sheathTemp, absPress)

		#Flush the 'OK\r' reply from the RDR,0
		ok = self.readline(b'\r')
		assert ok == 'OK\r'
		#print("RDR,0 -> %r" % ok)

		#return dNdLogDp
		return v

if __name__ == "__main__":
	import time

	d = FMPS3091('COM4', verbosity=1)
	time.sleep(1)
	d.fd.flushInput()
	try:
		print(d.SetFlow("on"))
		time.sleep(5)
#		d.ZeroElectrometers()
		#d.fd.write("RDR,0\r")
		#d.fd.write("RDR,0\r")
		#d.ReadPressure()
		#d.ReadTemperature()
		#d.ReadPressure()
		#d.ReadTemperature()
		#d.ReadAnalogInput()
		#d.ReadSEM()
		#d.ReadRDR4()
		#d.SetSDS("OFF")
		for i in range(5):
			v = d.ReadRDR7()
			print(v)
		#for i in range(4):
		#	#time.sleep(1)
		#	print(d.ReadRDR7())
		#	print(d.ReadRSR())
		#	print(time.clock())
#			#	print()
		print(d.SetFlow("off"))

	finally:
		print("finally")
		#d.fd.write("RDR,0\r")
		#d.fd.write("RDR,0\r")
		#d.SetSDS("OFF")
		#time.sleep(1)
		d.fd.flushInput()
		d.close()

