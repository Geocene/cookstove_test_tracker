from __future__ import absolute_import, division, print_function	#, unicode_literals

import time
import threading

import numpy as np

if 1:
	import cb
else:
	def doSlowImport():
		print("Start import")
		import cb as _cb
		print("Import complete")
		global cb
		cb = _cb

	loader = threading.Thread(None, target=doSlowImport)
	loader.start()
	print("continuing w/o import being complete")

class CBW:
	def __init__(self,board):
		self._board = board
		self._values = [0]*3
		self._lock = threading.Lock()

#		if Simulation.Simulation:
#			self._values = [0]*3
#		else:
#			self._dioBase = cb.GetConfig(cb.BOARDINFO, board, 3, cb.BIBASEADR)

#			self.hBuf = cb.WinBufAlloc(10000)

#			# Need to do this or we get a port configuration error
#			# Unfortunately, it also resets the outputs all to 0
#			# Upon initial boot, all will be inputs, but the external
#			# devices pull them to zero.  If they are already zero,
#			# it is safe to change them.  If not, they must have already
#			# been set since hardware power up.

#			if (cb.DIn(self._board, cb.FIRSTPORTA ) == 0 and
#				cb.DIn(self._board, cb.FIRSTPORTB ) == 0 and
#				cb.DIn(self._board, cb.FIRSTPORTCL) == 0 and
#				cb.DIn(self._board, cb.FIRSTPORTCH) == 0):

#				#print "Setting all ports to output\n"
#				cb.DConfigPort(self._board, cb.FIRSTPORTA,  cb.DIGITALOUT)
#				cb.DConfigPort(self._board, cb.FIRSTPORTB,  cb.DIGITALOUT)
#				cb.DConfigPort(self._board, cb.FIRSTPORTCL, cb.DIGITALOUT)
#				cb.DConfigPort(self._board, cb.FIRSTPORTCH, cb.DIGITALOUT)


	def Lock(self):
		"""Lock()

		Lock A/D for multithread access
		"""
		self._lock.acquire()

	def Unlock(self):
		"""Unlock()

		Release thread lock
		"""
		self._lock.release()

	def GetVoltage(self, chan, mux, avgCount=0):
		if Simulation.Simulation:
			return 0.0

#		if mux is not None  and  mux >= 0:
#			chan = (chan+1)*16 + mux
#		sum = 0
#		for i in range(avgCount):
#			counts = cb.AIn(self._board,chan,cb.BIP10VOLTS)
#			sum += counts
#		counts = sum / avgCount

		if mux is None:
			self.Lock()
			#TODO: Do I want BLOCKIO and BURSTMODE here?  Check old C code
			data = cb.AInScan(self._board,chan,chan,avgCount,100000,
#					cb.BIP10VOLTS,self.hBuf,0)
					cb.BIP10VOLTS,self.hBuf,cb.BLOCKIO)
			values = cb.WinBufToArray(self.hBuf,0,avgCount)
			self.Unlock()
			array = np.fromstring(values, np.uint16)
			array = array * 20.0 / 65535 - 10.0
			voltage = np.sum(array) / len(array)
		else:
			chan = (chan+1)*16 + mux
			self.Lock()
			counts = cb.AIn(self._board, chan, cb.BIP10VOLTS)
			self.Unlock()
			voltage = (counts-32768) * 10.0 / 32768
#		print "%3d %6d %8.3f" % (chan,counts,voltage)
		return voltage

#	def PutVoltage(self,chan,value):
#		self.Lock()
#		pass
#		self.Unlock()

	def PutValue(self,chan,value):
		self.Lock()
		if not Simulation.Simulation:
			cb.AOut(self._board,chan,cb.NOTUSED,value)
		self.Unlock()

# Avoid using DBinOut since they require the port to be configured
# at each program startup

#	def ClrBit(self,port,bit):
#		self.Lock()
#		cb.DBitOut(self._board,cb.FIRSTPORTA,port*8+bit,0)
#		self.Unlock()

#	def SetBit(self,port,bit):
#		self.Lock()
#		cb.DBitOut(self._board,cb.FIRSTPORTA,port*8+bit,1)
#		self.Unlock()

#	def TestBit(self,port,bit):
#		self.Lock()
#		value = cb.DBitIn(self._board,cb.FIRSTPORTA,port*8+bit)
#		self.Unlock()
#		return value


	def GetPort(self,port):
		if Simulation.Simulation:
			return self._values[port]
		else:
			return cb.InByte(self._board,self._dioBase+port)

	def PutPort(self,port,value):
		if Simulation.Simulation:
			self._values[port] = value
		else:
			cb.OutByte(self._board,self._dioBase+port,value)

	def ClrBit(self,port,bit):
#		print "CBW.ClrBit               %20.6f" % time.clock()
		mask = 1 << bit
		self.Lock()
		self.PutPort(port,self.GetPort(port) & ~mask)
		self.Unlock()
#		print "CBW.ClrBit               %20.6f\n" % time.clock()

	def SetBit(self,port,bit):
#		print "CBW.ClrBit               %20.6f" % time.clock()
		mask = 1 << bit
		self.Lock()
		self.PutPort(port,self.GetPort(port) |  mask)
		self.Unlock()
#		print "CBW.SetBit               %20.6f\n" % time.clock()

	def TestBit(self,port,bit):
		mask = 1 << bit
		value = self.GetPort(port)
		return ((value & mask) != 0)

	def TIn(self, chan, scale=cb.CELSIUS, options=cb.FILTER):
#	def TIn(self, chan, scale=None, options=None):
#		if scale is None: scale = cb.CELSIUS
#		if options is None: options = cb.FILTER
		temp = cb.TIn(self._board, chan, scale, options)
		return temp

	#loChan and hiChan are inclusive, the MCC way
	def TInScan(self, loChan, hiChan, scale=cb.CELSIUS, options=cb.FILTER):
#	def TInScan(self, loChan, hiChan, scale=None, options=None):
#		if scale is None: scale = cb.CELSIUS
#		if options is None: options = cb.FILTER
		temps = cb.TInScan(self._board, loChan, hiChan, scale, options)
		return temps

if __name__ == "__main__":
	import os
	import msvcrt

	def logger(dev):
		fileName = raw_input("Enter filename: ")
		pathName = "C:\\Users\\Gadgil Lab Stoves\\Desktop\\Dropbox\\75C Lab Dropbox Folder\\USB-TC-AI\\" + fileName
		if os.path.exists(pathName):
			print("File already exists.  Please delete first")
			return
		f = open(pathName, "w")
		print("Press any key to stop")
		while not msvcrt.kbhit():
			T = dev.TInScan(0,2)
			s = time.strftime("%H:%M:%S", time.localtime(time.time()))
			s += "\t%5.2f\t%5.2f\t%5.2f" % 	tuple(T)
			print(s)
			f.write(s + "\n")
			time.sleep(0.98)
		f.close()

	while 1:
		if globals().get('cb', None) is not None:
			print("\n")
			break
		print(".", end='')
	d = CBW(0)
	logger(d)
#	for i in range(4):
#		print("%d %g" % (i, d.TIn(i)))
#	print(d.TInScan(0,3))

