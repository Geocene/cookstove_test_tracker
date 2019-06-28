#
#
#
from __future__ import absolute_import, division, print_function
from collections import namedtuple

import sys
import serial
import numpy as np

try:
	from SerialTask import SerialTask
except ImportError:
	class SerialTask:
		def __init__(self, fd, handle):
			pass

class APS3321(SerialTask):
	#God Only Knows what the last two of these values means.  It is not in the manual.
	YRecordType = namedtuple('YRecord', 'BaroPress TotalFlow SheathFlow A0 A1 D0 D1 D2 '
									'LaserPower LaserCurrent SheathPumpVoltage TotalPumpVoltage '
									'InletTemp BoxTemp gok1 gok2')

	DRecordType = namedtuple('DRecord', 'ANX tIndex status stime dtime '
									'evt1 evt3 evt4 total counts')

	#As of 2014.04.04, COM9 is Octopus Connector 3
	def __init__(self, port='COM9', verbosity=0):
#		print('APS3321', port)
		self.verbosity = verbosity
		if port is None  or  port == '':
			self.fd = None
			SerialTask.__init__(self, self.fd, None)
		else:
			self.fd = serial.Serial(port, baudrate=9600,
					bytesize=serial.SEVENBITS, parity=serial.PARITY_EVEN,
					timeout=0.5)
			SerialTask.__init__(self, self.fd, None)

		self.errorStrings = ['Laser Fault',
							 'Total Flow out of range',
							 'Sheath Flow out of range',
							 'Excessive sample concentration (alarm)',
							 'Accumulator clipped (i.e. > 65535)',
							 'Autocal failed',
							 'Internal temperature < 10 degrees C',
							 'Internal temperature > 45 degrees C',
							 'Detector voltage more than +/- 10% Vb',
							 'Reserved (unused)']


	def close(self):
		self.fd.close()

	def write(self, cmd):
		if self.verbosity > 0:
			print("APS3321:Write %s" % cmd)
		s = cmd + '\r'
		if sys.version_info >= (3,0):
			s = s.encode('Latin-1')
		self.fd.write(s)

	def readline(self, eol=b'\n'):
		s = b''
		while 1:
			c = self.fd.read(1)
			if c == b'':
				break
			s += c
			if s.endswith(eol):
				break
		if sys.version_info >= (3,0):
			s = s.decode('Latin-1')
		if self.verbosity > 0:
			print("APS3321:Read  %r" % s)
		return s

	def exchange(self, cmd, fct):
		self.write(cmd)
		reply = self.readline(b'\r')
		#Strip \r at end.
		reply = reply[0:-1]
		#print("APS", cmd, repr(reply))
		return fct(reply)

	def GetBinEdges(self):
		#Setup for 52 evenly spaced bins
		nBins = 52
		dMin  = 10**((86        ) / 32)
		dMax  = 10**((86+1*nBins) / 32)
#		print("APS", nBins, dMin, dMax)
#		dMin, dMax, nBins = 523.0, 20535.51244, 51
		edges = np.logspace(np.log10(dMin), np.log10(dMax), nBins+1)
		#Adjust initial bin to be 8 times wider
		edges[0] = 10 ** ((86-7) / 32)
		return edges

	def SetModeAndSampleTime(self, mode, t):
		self.fd.flushInput()
		modes = {'A':0, 'S':1, 'C':2}
		s = "SMT%d,%d" % (modes[mode], t)
		r = self.exchange(s, str)
		#print("SetModeAndSampleTime", repr(s), repr(r))
		return r

	def SetPumps(self, total, sheath):
		self.fd.flushInput()
		s = "SP%d,%d" % (total, sheath)
		r = self.exchange(s, str)
		#print("SetPumps", repr(s), repr(r))
		return r

	def StartStop(self, n):
		self.fd.flushInput()
		s = "S%d" % n
		r = self.exchange(s, str)
		return r

	def StartMeasurement(self):
		return self.StartStop(1)

	def StopMeasurement(self):
		return self.StartStop(0)

#	def Go(self, n):
#		self.fd.flushInput()
#		s = self.exchange("G%d"%n, str)
#		assert(self.fd.read(1) == '\n')
#		return s

	def ReadAerosolFlow(self):
		return self.exchange("RQA", float)

	def ReadSheathFlow(self):
		return self.exchange("RQS", float)

	def ReadTotalFlow(self):
		return self.exchange("RQT", float)

	def ReadVersion(self):
		return self.exchange("RV", str)

#	def ReadAccumulator(self, bin1=0, bin2=1023):
#		self.write("R%d,%d" % (bin1, bin2))
#		#Reply is bare \n
#		c = self.fd.read(1)
#		values = []
#		for bin in range(bin1, bin2+1):
#			s = self.readline()
#			values.append(int(s))
#		#print(values)
#		return values

	def ReadRecord(self, c):
		s = self.exchange('RR%s' % c, str)
		#print(s)
		v = s.split(',')
#		print(len(v)
#		print(v)
		return v

	def ReadYRecord(self):
		s = self.exchange('RRY', str)
		#print(s)
		values = s.split(',')
		cksum = sum([ord(c) for c in s[4:]])
		#print(hex(cksum))
		if len(values) != 18  or int(values[0],16) != cksum  or  values[1] != 'Y':
			raise RuntimeError('APS3321: Illegal Y Record: %r' % (s))
		#TODO: D0, D1, D2 and possibly gok2 should probably be integers here
		yRecord = self.YRecordType(*[float(v) for v in values[2:]])
		#print(yRecord)
		return yRecord

	def ReadDRecord(self):
		"""
		Read a D Record
			 0: Checksum (hex)
			 1: D
			 2: ANX (str)
			 3: tindex
			 4: status (hex)
			 5: stime
			 6: dtime
			 7: evt1
			 8: evt3
			 9: evt4
			10: total
			11: undersized bin count
			12: first regular bin count
		Only items 0 through 10 are guaranteed to exist.  Record stops
		at last non-zero item
		"""
		s = self.exchange('RRD', str)
		values = s.split(',')
		cksum = sum([ord(c) for c in s[4:]])
		if len(values) < 11 or int(values[0],16) != cksum  or  values[1] != 'D':
			raise RuntimeError('APS3321: Illegal D Record: %r' % (s))
		# counts includes undersized bin!!
		counts = self.ExtractValues(values[11:], 52)
		items = [values[2], int(values[3]), int(values[4],16)] + [int(v) for v in values[5:11]] + [counts]
		dRecord = self.DRecordType(*items)
		return dRecord

	def ExtractValues(self, rawItems, n):
		#Convert string items to integers, with empty meaning zero
		counts = [int(s) if len(s) > 0 else 0 for s in rawItems]
		#Pad to n bins, as trailing size bins with all zero in them are truncated
		counts2 = np.zeros(n, np.int32)
		counts2[0:len(counts)] = counts
		return counts2

	def FormatStatusValue(self, code):
		items = []
		for i, s in enumerate(self.errorStrings):
			if code & (1 << i):
				items.append(s)
				code &= ~(1 << i)
		if code != 0:
			items.append("0x%04x" % i)
		return ', '.join(items)

if __name__ == "__main__":
	import time

	d = APS3321('COM5', verbosity=1)
	try:
		#print(d.ReadVersion())
		#print(d.Go(1))
		#print(d.Go(0))
		#print(d.Go())
		#print(d.ReadAccumulator(0,1023))
		#print(d.ReadRecord('A'))
		#print(d.ReadRecord('B'))
		#print(d.ReadRecord('C'))
#		print(d.ReadYRecord())

		d.SetPumps(True, True)

		d.SetModeAndSampleTime('S', 1)

		d.StartMeasurement()
		time.sleep(5)
		d.StopMeasurement()

		for i in range(5):
			flow = d.ReadAerosolFlow()
			dRecord = d.ReadDRecord()

			counts = dRecord.counts
			dr = dRecord
			print(flow, dr.evt1, dr.evt3, dr.evt4, dr.total, counts[0:10])


			# Sample time is involved here
			binWidth = 1/32.0
			flow = 1
			conc = [60*c/flow/1000.0/binWidth for c in counts[0:]]
			#conc[0] *= 8
			print(['%.2f' % v for v in conc[0:10]])
			print()
#			time.sleep(1)

	finally:
		d.close()
