from __future__ import absolute_import, division, print_function	#, unicode_literals

import sys
import time
import threading
import traceback

import win32event
import win32file

import ctypes
win32dll = ctypes.WinDLL('kernel32')

from serial import win32

class Cancel(Exception):
	pass

class SerialTask():
	def __init__(self, fd, handle=None):
		#This is an undocumented internal feature of PySerial on Win32
		#It might not be safe to assume the event has already been created
		#This is presumably the same as self.fd, but a copy is made here, to
		#avoid referencing a "private" name in the device namespace.
		
		#YODO: This references an private name in pyserial.  The test on
		#python version number is wrong.  It should be based on pyserial.

		if handle is None:
			if fd is None:
				handle = None
			else:
				handle = fd.hComPort if sys.version_info < (3,0) else fd._port_handle
				#print('SerialTask', handle, dir(fd))
				#print('fileno',fd.fileno())
				#print()
		self._handle = handle
		self._myfd = fd
#		self._handle = handle if handle is not None else fd.hComPort
		if fd is not None  and hasattr(fd, 'read'):
			self.oldread = fd.read
			fd.read = self.doread
		#This is needed in case we communicate with the device before the
		#thread is started
		self._cancelFlag = False
		self._stopFlag = False

#		self.hComPort = fd.hComPort
#		self._overlappedRead = fd._overlappedRead
#		self.timeout = fd.timeout
		self.StatusFlags = set()

	def IsReal(self):
		return self.fd is not None

	def SetStatusFlag(self, flag):
		if flag in self.StatusFlags:
			print('Warning: Setting already set status flag', flag, self)
		self.StatusFlags.add(flag)

	def ClearStatusFlag(self, flag):
		self.StatusFlags.remove(flag)

	def TestStatusFlag(self, flag):
		return flag in self.StatusFlags

	def Start(self, fct, *args, **kwargs):
		#print("SerialTask.Start")
		if not self.IsReal():
#			print("Start Skipped", self)
			return
		self._fct = fct
		self._args = args
		self._kwargs = kwargs
		self._thread = threading.Thread(target=self.Run)
		self._thread.start()

	def Run(self):
		self._cancelFlag = False
		self._stopFlag = False
		try:
			while not self._stopFlag:
				start = time.clock()
				try:
					self._fct(*self._args, **self._kwargs)
				except Cancel as e:
					raise
				except Exception as e:
					#print(e)
					#TODO: How to only print file line of traceback
					traceback.print_exc(file=sys.stdout)
				#print("SerialTask.Run %.3f s\n" % (time.clock()-start), end='')
		except Cancel as e:
			#print("IO Cancel Exception caught %.3f s\n" % (time.clock()-start), end='')
			pass
		#print("SerialTask Complete")

	def Stop(self, wait=True, cancelIo=False):
#		print("SerialTask.Stop", waitFlag)
		if not self.IsReal():
#			print("Stop Skipped", self)
			return
		start = time.clock()
		self._stopFlag = True
		if cancelIo  and  self._myfd is not None:
			self._cancelFlag = True
			x = win32dll.CancelIoEx(self._handle, 0)
		#print("CancelIoEx: %d\n"  % x, end='')
		if wait:
			self.Wait()
		#print("SerialTask.Stop: %.3f s %s\n" % (time.clock()-start, self), end='')

	def Wait(self):
		if not self.IsReal():
#			print("Wait Skipped", self)
			return
		if hasattr(self,'_thread'):
			self._thread.join()
			del self._thread

	def IsStopping(self):
		return self._stopFlag

	def doread(self, n):
#		print('doread %d' % n)
		s = self.oldread(n)
#		s = self.read2(n)
		#TODO: It might be better to actually look at GetLastError here
		#Even better if I can figure out why I can't successfully modify
		#the win32serial read routine.
		if self._cancelFlag:
			self._cancelFlag = False
			raise Cancel("Cancel I/O")
		return s


#    Code from serial.win32serial.py
#   Using this works, but I get a python error upon exit
#   Possibly the cleanup in win32serial is conflicting
#
#	def read2(self, size=1):
#		"""Read size bytes from the serial port. If a timeout is set it may
#		   return less characters as requested. With no timeout it will block
#		   until the requested number of bytes is read."""
#		if not self.hComPort: raise portNotOpenError
#		if size > 0:
#			win32.ResetEvent(self._overlappedRead.hEvent)
#			flags = win32.DWORD()
#			comstat = win32.COMSTAT()
#			if not win32.ClearCommError(self.hComPort, ctypes.byref(flags), ctypes.byref(comstat)):
#				raise SerialException('call to ClearCommError failed')
#			if self.timeout == 0:
#				n = min(comstat.cbInQue, size)
#				if n > 0:
#					buf = ctypes.create_string_buffer(n)
#					rc = win32.DWORD()
#					err = win32.ReadFile(self.hComPort, buf, n, ctypes.byref(rc), ctypes.byref(self._overlappedRead))
#					if not err and win32.GetLastError() != win32.ERROR_IO_PENDING:
#						raise SerialException("ReadFile failed (%r)" % ctypes.WinError())
#					err = win32.WaitForSingleObject(self._overlappedRead.hEvent, win32.INFINITE)
#					read = buf.raw[:rc.value]
#				else:
#					read = bytes()
#			else:
#				buf = ctypes.create_string_buffer(size)
#				rc = win32.DWORD()
#				err = win32.ReadFile(self.hComPort, buf, size, ctypes.byref(rc), ctypes.byref(self._overlappedRead))
#				if not err and win32.GetLastError() != win32.ERROR_IO_PENDING:
#					raise SerialException("ReadFile failed (%r)" % ctypes.WinError())
#				err = win32.GetOverlappedResult(self.hComPort, ctypes.byref(self._overlappedRead), ctypes.byref(rc), True)
#				print('overlapped read %s %d\n' % (err, win32.GetLastError()), end='')
#				if not err:
#					return bytes()
#				read = buf.raw[:rc.value]
#		else:
#			read = bytes()
#		return bytes(read)