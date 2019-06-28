"""
CAI.py

Classes abstracting the California Analytical ... Instrument set.


Warning - There are some unresolved issues attempting to hide the
differences between single and multi-channel instruments and some
of this code is not properly tested in both situations.
"""

from __future__ import absolute_import, division, print_function	#, unicode_literals

import sys
import time
import socket
import serial

import SerialTask

class Error(Exception):
	def __init__(self,code,msg,cmd,reply):
		self._code = code
		self._msg = msg
		self._cmd = cmd
		self._reply = reply

	def __str__(self):
		return str((self._code,self._msg,self._cmd,self._reply))


class Analyzer(SerialTask.SerialTask):
	def __init__(self, host=None, port=None, verbosity=0):
		if host is None  or  host == '':
			self.fd = None
		else:
			self.connect(host, port)
			#TODO: This won't work when done in connect at the moment
			SerialTask.SerialTask.__init__(self, self.fd)
		self._Verbosity = verbosity
		self._LastStatus = None
		self._errorList = []
		self._errorMsgs = []

	def connect(self, host, port):
#		try:
#			self._socket.settimeout(0.25)
#			self._socket.connect((host,port))
#			self._socket.settimeout(5.0)
#			return True
#		except socket.timeout:
#			print('Socket Timeout', host,port)
#			return False
		#Serial Octopus Cable Connector 7
		#host is com port
		self.fd = serial.Serial(host, baudrate=9600,
					bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
					#Need long timeout due to calibration save issues
					timeout=5.5)
#		print('connected')


	def close(self):
#		self._socket.close()
		self.fd.close()

	def read(self,maxLen=1000):
#		return self._socket.recv(maxLen)
		STX, ETX = b'\x02', b'\x03'
		s = b''
		while 1:
			c = self.fd.read(1)
			if c == b'':
				break
			s += c
			if c == ETX:
				break
		if sys.version_info >= (3,0):
			s = s.decode('Latin-1')
		return s

	def write(self,packet):
#		self._socket.send(packet)
		if sys.version_info >= (3,0):
			packet = packet.encode('Latin-1')
		self.fd.write(packet)

	def SendCommand(self,cmd):
		STX, ETX = chr(0x02), chr(0x03)
		if self._Verbosity > 1:
			print('Send: ',STX + ' ' + cmd + ETX)
		#self._socket.send(STX + ' ' + cmd + ETX)
		self.write(STX + ' ' + cmd + ETX)		#TODO: unicode .decode('ASCII'))

	def SimpleCommand(self,cmd,chan=0,args=None,ignoreStatus=False):
		STX, ETX = chr(0x02), chr(0x03)
		cmd1 = cmd + ' K%d' % chan
		if args is not None:
			cmd1 += ' ' + args
		self.SendCommand(cmd1)
		reply = self.read()

		if self._Verbosity > 1:
			print('Cmd:',cmd1)
			print('Reply:',repr(reply))

#		if reply[0:2] != STX+' '  or  reply[-1] != ETX:
		if reply[0:2] != STX+'_'  or  reply[-1] != ETX:
			raise Error(-1,'Malformed reply (STX and/or ETX missing)',cmd1,reply)
		if reply[2:6] != cmd:
			raise Error(-2,'Function '+cmd+' Unknown',cmd1,reply)

		status = int(reply[7])
		value  = reply[9:-1]

		# I am not completely sure that this is the proper test.
		# The manual is not totally clear.  I am erring on the side
		# of caution (extra errors, rather than too few)

		if value[-2:] == 'SE':
			raise Error(-3,'Syntax Error',cmd1,reply)
		if value[-2:] == 'DF':
			raise Error(-4,'Data Format Error',cmd1,reply)
		if value[-2:] == 'BS':
			raise Error(-5,'Analyzer is busy',cmd1,reply)
		if value[-2:] == 'OF':
			raise Error(-6,'Analyzer is offline (Manual Mode)',cmd1,reply)

		# These errors are not protocol problems, but rather operator
		# setup information.  Note handling of new status 0 when there
		# was a previous status:
		if status != self._LastStatus:
#			print 'Error status change'
			self._LastStatus = status
			self._errorList = self.GetErrorStatus()
			self._errorMsgs = self.GetErrorText(self._errorList)
			#print 'Errors',self._errorMsgs
			# if not ignoreStatus:
			#	print 'Error Status Change:', status
			#	for error in self.GetErrorStatus():
			#		print '  ',self.errorCodeDict[error]

		return value

	# Return all the "interesting" information from one gas analyzer.
	# Data is in the form:
	#	((errorState1,errorState2, ...),
	#	 ((range[0], rangeLimit[0], autoRange[0], value[0]),
	#	  (range[1], rangeLimit[1], autoRange[1], value[1]))

	def Update(self):
		values = []
		for i in range(1):
			range = self.GetRange()
			rangeLimit = self.GetRangeLimit(range)
			autoRange = int("SARE" in self.GetNormalDeviceStatus())
			value = self.Analyzers[0].GetMeasuredConcentrationValues()[0]
			values.append((range,rangeLimit,autoRange,value))

	def GetMeasuredConcentrationValues(self,chan=0):
		reply = self.SimpleCommand('AKON',chan)
		return [float(value) for value in reply.split()]

	# Return the measuring range as an integer (1..4)
	def GetRange(self,chan=0):
		return int(self.SimpleCommand('AEMB',chan)[1])

	# Return the measuring range limit for one particular range
	def GetRangeLimit(self,chan=0,range=0):
		if not range:
			range = self.GetRange()
		reply = self.SimpleCommand('AMBE',chan, 'M%d' % range)
		return float(reply.split()[1])

	# Return all the measuring range limits as an array
	def GetRangeLimits(self,chan=0):
		reply = self.SimpleCommand('AMBE',chan)
		return [None] + [float(item) for item in reply.split()[1::2]]

	def GetNormalDeviceStatus(self,chan=0):
		return self.SimpleCommand('ASTZ',chan).split()

	def GetErrorStatus(self):
		reply = self.SimpleCommand('ASTF',0,None,ignoreStatus=True)
		return [int(value) for value in reply.split()]

	def GetSystemTime(self):
		s = self.SimpleCommand('ASYZ',0)
		t = time.mktime((
			int(s[0:2])+2000, int(s[2:4]), int(s[4:6]),
			int(s[7:9]), int(s[9:11]), int(s[11:13]),-1,-1,-1))
		return t

	def GetFlowRates(self,chan=0):
		reply = self.SimpleCommand('ADUF',chan)
		return [float(value) for value in reply.split()]

	def GetPressures(self,chan=0):
		reply = self.SimpleCommand('ADRU',chan)
		return [float(value) for value in reply.split()]

#	def GetTemperature(self,chan=0,range=1):
#		reply = self.SimpleCommand('ATEM',chan,"%d" % range)
#		return float(reply)

	def GetTemperatures(self,chan=0):
		reply = self.SimpleCommand('ATEM',chan)
		return [float(value) for value in reply.split()]


	def Reset(self):
		self.SimpleCommand('SRES')

	def Pause(self):
		self.SimpleCommand('SPAU')

	def Standby(self,chan=0):
		self.SimpleCommand('STBY',chan)

	def ManualMode(self):
		self.SimpleCommand('SMAN')

	def RemoteMode(self):
		self.SimpleCommand('SREM')

	def SetAutoRangeOn(self,chan=0):
		self.SimpleCommand('SARE',chan)

	def SetAutoRangeOff(self,chan=0):
		self.SimpleCommand('SARA',chan)

	def SetRange(self,chan=0,range=1):
		self.SimpleCommand('SEMB',chan,'M%d' % range)

	def StartMeasuring(self):
		self.SimpleCommand('SMGA')


	def StartUDP(self):
		self.SimpleCommand('SUDP',0,'ON')

	def StopUDP(self):
		self.SimpleCommand('SUDP',0,'OFF')

	def SetUDPStreamingParameters(self,port,rate,cmd):
		cmd = cmd.replace(' ','_')
		self.SimpleCommand('EUDP',0,'%d %g A - %s' % (port,rate,cmd))


	def GetErrorText(self, errorCodes):
#		return [self.errorCodeDict.get(n,'Unknown Error: %d' % n) for n in errorCodes]
		msgs = []
		for n in errorCodes:
			s = self.errorCodeDict.get(n,'Unknown Error: %d' % n)
			if not s.startswith('-'):
				msgs.append(s)
		return msgs



class MODEL600_HCLD(Analyzer):
	errorCodeDict = {
		 1: 'Sample Pressure Failure',
		 2: 'Air Pressure Failure',
		 3: 'Oven Temp Failure',
		 4: 'Converter Temp Failure',
		 5: 'Pump Temp Failure',
		 6: 'Diode Temp Failure',
		 7: 'Cell Temp Failure',
		 8: '-Peltier Gas Temp Failure',
		 9: '-O2 Temp Failure',  #'Reaction Chamber Temp Failure',
		10: 'EPC Coil Sample Failure',
		11: 'EPC Coil Air Failure',
		12: 'Range Overflow',
		13: 'ADC Range Overflow',
		14: 'ADC Range Underflow',
		15: 'Range 1 is not calibrated',
		16: 'Range 2 is not calibrated',
		17: 'Range 3 is not calibrated',
		18: 'Range 4 is not calibrated',
		19: 'Reaction Chamber Pressure',
		20: 'Low Concentration Warning',
		21: 'High Concentration Warning',
		22: 'NH3 Converter Temp Failure',
		23: 'dummy text for RTC',
		24: 'General Alarm',
		26: 'Cal Alarm',
	}

	def SetDryMeasurment(self):
		self.SimpleCommand('SDRY')

	def SetWetMeasurmentMode(self):
		self.SimpleCommand('SWET')

class MODEL600_DualO2(Analyzer):
	errorCodeDict = {
	}

class MODEL600_HFID(Analyzer):
	errorCodeDict = {
		 1: 'No Flame',
		 2: 'Sample Pressure Failure',
		 3: 'Air Pressure Failure',
		 4: 'Fuel Pressure',
		 5: 'Air Inject Pressure Failure',  #'Burner Temp Failure',
		 6: 'Fuel Inject Pressure Failure', #'Oven Temp Failure',
		 7: 'Filter Temp Failure',          #'Cutter Temp Failure',
		 8: 'Burner Temp Failure',          #'Pump Temp Failure',
		 9: 'Oven Temp Failure',            #'EPC Coil Sample Failure',
		10: 'Cutter Temp Failure',          #'EPC Coil Air Failure',
		11: 'Pump Temp Failure',            #'EPC Coil Fuel Failure',
		12: 'EPC Coil Sample Failure',      #'Range Overflow',
		13: 'EPC Coil Air Failure',         #'ADC Range Overflow',
		14: 'EPC Coil Fuel Failure',        #'ADC Range Underflow',
		15: 'EPC Coil Air Inject Failure',  #'Analyzer is not calibrated'
		16: 'EPC Coil Fuel Inject Failure',
		17: 'Range Overflow',
		18: 'ADC Range Overflow',
		19: 'ADC Rabge Underflow',
		20: 'Range 1 is not calibrated',
		21: 'Range 2 is not calibrated',
		22: 'Range 3 is not calibrated',
		23: 'Range 4 is not calibrated',
		24: 'Low concentration Warning',
		25: 'High concentration Warning',
		26: 'dummy text for RTC',
		27: 'General Alarm',
		29: 'Cal Alarm',
	}

class MODEL602P_NDIR(Analyzer):
	errorCodeDict = {
		 1: 'Flow 1 Failure',
		 2: 'Flow 2 Failure',
		 3: 'Flow 3 Failure',
		 4: 'External Analog 1 Failure',
		 5: 'External Analog 2 Failure',
		 6: 'Pressure Failure',
		 7: 'Temperature Failure',
		 8: 'Channel 1 Not Calibrated',
		 9: 'Channel 2 Not Calibrated',
		10: 'Channel 3 Not Calibrated',
		11: 'Ch1: Low conc. Warning',
		12: 'Ch2: Low conc. Warning',
		13: 'Ch3: Low conc. Warning',
		14: 'Ch1: High conc. Warning',
		15: 'Ch2: High conc. Warning',
		16: 'Ch3: High conc. Warning',
		17: 'Ch1: Temperature!',
		18: 'Ch2: Temperature!',
		19: 'Ch3: Temperature!',
		20: 'Ch1: EPC failure',
		21: 'Ch2: EPC failure',
		22: 'Ch3: EPC failure',
		23: 'Ch1: Range Overflow',
		24: 'Ch2: Range Overflow',
		25: 'Ch3: Range Overflow',
		26: 'Ch1: ADC Range Overflow',
		27: 'Ch2: ADC Range Overflow',
		28: 'Ch3: ADC Range Overflow',
		29: 'Ch1: ADC Range Underflow',
		30: 'Ch2: ADC Range Underflow',
		31: 'Ch3: ADC Range Underflow',
		32: 'dummy text for RTC',
		33: 'General Alarm',
		34: 'In Remote',
		35: '1 Cal Alarm',
		36: '2 Cal Alarm',
		   37: '3 Cal Alarm'
	}

if __name__ == "__main__":
	def TestDualO2():
		a = MODEL600_DualO2(verbosity=1)
		a.connect("192.168.70.30", 7700)
		print('Connected')
		try:
			a.RemoteMode()
			#a.SimpleCommand('AKEN')
			#a.SimpleCommand('AXXX')
			#a.SimpleCommand('SXXX')
			a.Reset()
			a.Pause()
			a.Standby()
#			a.SetRange(4)
			print('System Time', time.ctime(a.GetSystemTime()))
			print('Measuring Range',a.GetRange())
			print('Measuring Range Limits',a.GetRangeLimits())
			print('Normal Device Status',a.GetNormalDeviceStatus())
			print('Error Status',a.GetErrorStatus())
#			print('Temperatures',a.GetTemperature(2))
#			print('Pressures',a.GetPressures())
#			print('Flow Rates',a.GetFlowRates())
#			a.SimpleCommand('SMGA')
			print(a.GetNormalDeviceStatus())
			for i in range(5):
				xx = a.GetMeasuredConcentrationValues()
				print(xx)
				xx[3] = int(xx[3])
				t = xx[3]
				print(xx, t//3600, (t//60)%60, t%60, time.time())
			a.Standby()

#				s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#				s.bind(('',7001))
#				a.SetUDPStreamingParameters(7001,1,'ASTF K0;AEMB K0;AKON K0')
#				a.StartUDP()
#				for i in range(10):
#					print s.recv(2048)
#				a.StopUDP()

		except RuntimeError as s:
			print('In exception handler')
			print(s)
			print(a.GetErrorStatus())
			print(a.GetErrorText(a.GetErrorStatus()))

		finally:
			print('In finally block')
			#a.IgnoreStatus(True)
			a.ManualMode()
			a.close()

	def TestHCLD():
		try:
			a = MODEL600_HCLD(verbosity=1)
#			a.connect("134.252.41.209",7700)
			a.connect("192.168.70.30",7700)
			print('Connected')
			try:
				a.RemoteMode()
				#a.SimpleCommand('AKEN')
				#a.SimpleCommand('AXXX')
				#a.SimpleCommand('SXXX')
				a.Reset()
				a.Pause()
				a.Standby()
				a.SimpleCommand('SNOX')
				a.SetRange(4)
				print('System Time', time.ctime(a.GetSystemTime()))
				print('Measuring Range',a.GetRange())
				print('Measuring Range Limits',a.GetRangeLimits())
				print('Normal Device Status',a.GetNormalDeviceStatus())
				print('Error Status',a.GetErrorStatus())
				print('Temperatures',a.GetTemperature(2))
				print('Pressures',a.GetPressures())
				print('Flow Rates',a.GetFlowRates())
				a.SimpleCommand('SMGA')
				print(a.GetNormalDeviceStatus())
				for i in range(5):
					xx = a.GetMeasuredConcentrationValues()
#					print xx
					xx[4] = int(xx[4])
					t = xx[4]
					print(xx, t//3600, (t//60)%60, t%60, time.time())
				a.Standby()

				s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
				s.bind(('',7001))
				a.SetUDPStreamingParameters(7001,1,'ASTF K0;AEMB K0;AKON K0')
				a.StartUDP()
				for i in range(10):
					print(s.recv(2048))
				a.StopUDP()

			except RuntimeError as s:
				print('In exception handler')
				print(s)
				print(a.GetErrorStatus())
				print(a.GetErrorText(a.GetErrorStatus()))

		finally:
			print('In finally block')
			#a.IgnoreStatus(True)
			a.ManualMode()
			a.close()

	def TestHFID():
		try:
			a = MODEL602P_NDIR(verbosity=1)
			a.connect("134.252.41.122",7700)
			try:
				a.RemoteMode()
				a.Reset()
				a.Pause()
				a.Standby()
#				a.SetRange(4)
				print('System Time', time.ctime(a.GetSystemTime()))
				print('Measuring Range',a.GetRange())
				print('Measuring Range Limits',a.GetRangeLimits())
				print('Normal Device Status',a.GetNormalDeviceStatus())
				print('Error Status',a.GetErrorStatus())
				print('Temperatures',a.GetTemperature(2))
				print('Pressures',a.GetPressures())
				print('Flow Rates',a.GetFlowRates())
				a.SimpleCommand('SMGA')
				print(a.GetNormalDeviceStatus())
				for i in range(5):
					xx = a.GetMeasuredConcentrationValues()
					t = int(xx[-1])
#					xx = xx[:-1]
					print(xx, t//3600, (t//60)%60, t%60, time.time())
				a.Standby()

#				s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#				s.bind(('',7001))
#				a.SetUDPStreamingParameters(7001,1,'ASTF K0;AEMB K0;AKON K0')
#				a.StartUDP()
#				for i in range(10):
#					print s.recv(2048)
#				a.StopUDP()

			except RuntimeError as s:
				print('In exception handler')
				print(s)
				print(a.GetErrorStatus())
				print(a.GetErrorText(a.GetErrorStatus()))

		finally:
			print('In finally block')
			#a.IgnoreStatus(True)
			a.ManualMode()
			a.close()

	def TestNDIR():
		try:
			a = MODEL602P_NDIR(verbosity=0)
			a.connect("COM13", None)
			try:
				a.RemoteMode()
				a.Reset()
				a.Pause()
				a.Standby()
#				a.SetRange(4)
				print('System Time', time.ctime(a.GetSystemTime()))
				print('Measuring Range',a.GetRange())
				print('Measuring Range Limits',a.GetRangeLimits())
				print('Normal Device Status',a.GetNormalDeviceStatus())
				print('Error Status',a.GetErrorStatus())
				print('Range1 = ',a.GetRange(1))
				print('Range2 = ',a.GetRange(2))
				print('Range3 = ',a.GetRange(3))
#				print('Temperatures',a.GetTemperature(2))
#				print('Pressures',a.GetPressures())
#				print('Flow Rates',a.GetFlowRates())
				a.SimpleCommand('SMGA')
				print(a.GetNormalDeviceStatus())
				for i in range(5):
					xx = a.GetMeasuredConcentrationValues()
					t = int(xx[-1])
#					xx = xx[:-1]
					print(xx, t//3600, (t//60)%60, t%60, time.time())
				#a.Standby()

#				s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#				s.bind(('',7001))
#				a.SetUDPStreamingParameters(7001,1,'ASTF K0;AEMB K0;AKON K0')
#				a.StartUDP()
#				for i in range(10):
#					print s.recv(2048)
#				a.StopUDP()

			except RuntimeError as s:
				print('In exception handler')
				print(s)
				print(a.GetErrorStatus())
				print(a.GetErrorText(a.GetErrorStatus()))

		finally:
			print('In finally block')
			#a.IgnoreStatus(True)
			a.ManualMode()
			a.close()

#	print()
#	print('New RunX')
#	TestHCLD()
#	TestHFID()
#	TestNDIR()
#	TestDualO2()

	import sys
	import time
	import msvcrt
	import os.path

	def logger(scale):
		fileName = raw_input("Enter filename: ")
		pathName = "C:\\Users\\Gadgil Lab Stoves\\Desktop\\Dropbox\\75C Lab Dropbox Folder\\CAI\\" + fileName
		if os.path.exists(pathName):
			print("File already exists.  Please delete first")
			return
		f = open(pathName, "w")
		print("Press any key to stop")
		while not msvcrt.kbhit():
			CO2, CO, O2, t = d.GetMeasuredConcentrationValues()
			s = time.strftime("%H:%M:%S", time.localtime(time.time()))
			s += "\t%.1f\t%.1f\t%.3f\t%.1f" % (CO2, CO, O2, t)
			print(s)
			f.write(s + "\n")
			time.sleep(0.93)
		f.close()
		msvcrt.getch()

	d = MODEL602P_NDIR('COM11', None, verbosity=1)
	#d.connect("COM13", None)
	try:
#		logger(d)
		for i in range(10):
			print(d.GetMeasuredConcentrationValues(), d.GetErrorStatus())
#x = [1, 2, 3, 29]
		#print(d.GetErrorText(x))
	finally:
		d.close()
