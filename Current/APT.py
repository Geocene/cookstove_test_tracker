from __future__ import absolute_import, division, print_function	#, unicode_literals

import sys
import numpy as np
import serial
import SerialTask

class APT(SerialTask.SerialTask):
	def __init__(self, port='COM10', verbosity=0):
		if port is None  or  port == '':
			self.fd = None
			SerialTask.SerialTask.__init__(self, self.fd)
		else:
			self.fd = serial.Serial(port, baudrate=9600,
					bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
					timeout=1)
			SerialTask.SerialTask.__init__(self, self.fd)
		self.verbosity = verbosity

		#Indexed by gain
		self.analogCalibration = np.ones((2), dtype= np.float)

		#Indexed by hardware channel number and gain
		self.pressureCalibration = np.ones((8,2), dtype=np.float)
		self.rawNoLoadPressure = np.zeros((8,2), dtype=np.int16)
		#TODO: Eliminate this
		#self.rawNoLoadPressure[:,1] = [-330, -300, -280, -120, -202, 140, -300, -243]

		if self.IsReal():
			self.loadCalibrations()
#		self.updateNoLoadPressures()

	def loadCalibrations(self):
		#This is relatively fast
		#print("APT: Reading Calibrations")
		for gain in [0,1]:
			self.analogCalibration[gain] = \
					self.getCalibrationValue(0, gain, extAnalog=True)
			for hwChan in range(8):
				self.pressureCalibration[hwChan, gain] = \
					self.getCalibrationValue(hwChan, gain, extAnalog=False)

	def updateNoLoadPressures(self, hwChanList=None, gainList=None):
		"""API here really should allow some independent control
		   of channel and gains, eg use channel,gain pairs.
		"""
		# This takes about 1 second per channel read
		#print("APT: Reading No Load Pressures")
		if hwChanList is None: hwChanList=range(8)
		if gainList is None: gainList=[0,1]
		#print("APT Zero", hwChanList, gainList)
		for hwChan in hwChanList:
			#print("%d" % hwChan, end=' ')
			for gain in gainList:
				self.rawNoLoadPressure[hwChan, gain] = \
					self.getRawNoLoadPressure(hwChan, gain)
				#print("%5d" % self.rawNoLoadPressure[hwChan, gain], end=' ')
			#print()

	def close(self):
		self.fd.close()

	def readWord16(self, cmdByte):
		if self.verbosity > 0:
			print("APT: Command %02x -> " % cmdByte, end='')

		value = 0
		for i in range(2):
			s = chr(cmdByte)
			if sys.version_info >= (3,0):
				s = s.encode('Latin-1')
			self.fd.write(s)
			c = self.fd.read(1)
			if c == b'':
				raise RuntimeError("No Reply for Byte %d" % i)
				print("No Reply for Byte %d" % i)
				#value = 0xffff
				#break
			#if self.verbosity > 0:
			#	print(" %02x" % ord(c), end='')
			value = (value << 8) | ord(c)
			# Remaining bytes are triggered by writing a 0xCC
			cmdByte = 0xCC
		if self.verbosity > 0:
			print(" = %04x" % value, end=' ')
		return value

	def readWord32(self, cmdByte):
		if self.verbosity > 0:
			print("APT: Command %02x -> " % cmdByte, end='')

		value = 0
		for i in range(4):
			s = chr(cmdByte)
			if sys.version_info >= (3,0):
				s = s.encode('Latin-1')
			self.fd.write(s)
			c = self.fd.read(1)
			if c == b'':
				raise RuntimeError("No Reply for Byte %d" % i)
			if self.verbosity > 0:
				print(" %02x" % ord(c), end='')
			value = (value << 8) | ord(c)
			# Remaining bytes are triggered by writing a 0xCC
			cmdByte = 0xCC
		if self.verbosity > 0:
			print(" = %08lx" % value)
		return value


	def getRawValue(self, hwChan, loGain=False, extAnalog=False, readType=0):
		cmdByte = hwChan
		if loGain: cmdByte |= 0x08
		if extAnalog: cmdByte |= 0x10
		cmdByte |= readType << 5
		reply = self.readWord16(cmdByte)
		sign = reply & 0x8000
		loBattery = reply & 0x4000
		# For some reason, things are different for the no-load pressure
		mask = 0x3FFF if readType == 1 else 0x0FFF
		value = reply & mask
		if sign: value = -value
		#print(value)
		return value

	def getCalibrationValue(self, hwChan, loGain=False, extAnalog=False):
		""""Return the calibration value for a particular
		hardware channel, gain and pressure/analog combination.
		The hwChannel must be 0 for the pressure.
		"""
		readType = 2

		cmdByte = hwChan
		if loGain: cmdByte |= 0x08
		if extAnalog: cmdByte |= 0x10
		cmdByte |= readType << 5

		value = self.readWord32(cmdByte)
		#Convert BCD to regular integer by interpreting its hex representation
		#TODO: Figure out a cleaner way to do this
		#print(hex(value))
		value = int("%07x" % value)
		#print(value / 1E6)
		return value / 1E6

	def getRawPressure(self, hwChan, loGain=False):
		return self.getRawValue(hwChan, loGain, extAnalog=False, readType=0)

	def getRawNoLoadPressure(self, hwChan, loGain=False):
		return self.getRawValue(hwChan, loGain, extAnalog=False, readType=1)

	def getRawAnalogInput(self, hwChan, loGain=False, readType=0):
		return self.getRawValue(hwChan, loGain, extAnalog=True, readType=readType)


	def GetPressure(self, physicalChan, gain):
		#For our unit physical channel 1..8 map to hardware channel 7..0
		hwChan = 8-physicalChan
		raw = self.getRawPressure(hwChan, gain)
		raw0 = self.rawNoLoadPressure[hwChan, gain]
		cal = self.pressureCalibration[hwChan, gain]
		p = (raw - raw0/10.0) * cal
		scale = 2 if gain else 10
		return p / scale

	def UpdateNoLoadPressure(self, physicalChan, gain):
		#For our unit physical channel 1..8 map to hardware channel 7..0
		hwChan = 8-physicalChan
		self.updateNoLoadPressures([hwChan], [gain])

	def GetAnalogInput(self, physicalChan, gain):
		#TODO: Figure out this mapping
		chanMap = (-1, 3, 2, 1, 0, 7, 6, 5, 4)
		hwChan = chanMap[physicalChan]
		raw = self.getRawAnalogInput(hwChan, gain)
		cal = self.analogCalibration[int(gain)]
		v = raw * cal
		scale = 1000 if gain else 10000
		return v / scale

if __name__ == "__main__":
	d = APT('COM10', verbosity=0)
	gain = 1
	try:
		#d.updateNoLoadPressures(gainList=[gain])
		#while 1:
		#	#for chan in range(1,9):
		#	#	print("%7.1f" % d.GetPressure(chan, gain), end=' ')
		#	#print("     ", end=' ')
		#	for chan in [1]:
		#		v = d.GetAnalogInput(chan, 1)
		#		RH = -34.33 + 34.681 * v
		#		print("%7.3f %7.3f" %  (v, RH), end=' ')
		#	print()



		for i in range(1,9):
			print("Chan %d" % i, end=' ')
			for gain in [0,1]:
				print("%6d" % d.GetPressure(i,gain), end=' ')
				print("%8.6f" % d.getCalibrationValue(i,gain), end=' ')
#				print("%8.6f" % d.GetCalibrationValue(i,gain, extAnalog=True), end=' ')
			print()

#		cal = d.GetCalibrationValue(chan=1,loGain=True, extAnalog=True)
#		print(cal)
#		while 1:
#			for i in range(1,9):
#				print("%6d" % d.GetPressure(i,0), end=' ')
#				#print("%8.3f" % ((cal*d.GetAnalogInput(i,1))/1000.0), end=' ')
#			print()

##		d.GetPressure(2, loGain=True)
##		d.GetPressure(2, loGain=True)
##		d.GetNoLoadPressure(6, loGain=False)
#		#d.GetAnalogInput(3, loGain=True)
	finally:
		d.close()
