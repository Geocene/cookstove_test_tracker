from __future__ import absolute_import, print_function

import sys
import time
import traceback

import ctypes

import numpy

_lib = ctypes.windll.nicaiu

uInt8					= ctypes.c_ubyte
int16					= ctypes.c_short
uInt16					= ctypes.c_ushort
int32					= ctypes.c_int
uInt32					= ctypes.c_uint
uInt64					= ctypes.c_ulonglong
float64 				= ctypes.c_double
char_p					= ctypes.c_char_p
bool32					= ctypes.c_int
TaskHandle				= ctypes.c_uint
PYOBJ					= ctypes.py_object

PTR						= ctypes.POINTER
REF						= ctypes.byref

DoneEventCB				= ctypes.CFUNCTYPE(int32, TaskHandle, int32, PYOBJ)
EveryNSamplesEventCB	= ctypes.CFUNCTYPE(int32, TaskHandle, uInt32, uInt32, PYOBJ)
SignalEventCB			= ctypes.CFUNCTYPE(int32, TaskHandle, int32, PYOBJ)

typemap = {
	int16	: numpy.int16,
	int32	: numpy.int32,
	uInt8	: numpy.uint8,
	uInt16	: numpy.uint16,
	uInt32	: numpy.uint32,
	float64	: numpy.float64
}

#
# import all symbals from nidaqmx that start with DAQmx_ or DAQmx, and
# add them to this module's namespace, but with out the prefix.
# Warning, symbols like DAQmx_10_SECONDS would be inaccessable in the
# normal way.  Fortunately, there do not seem to be any of those.
# Being paranoid, I am leaving in the check for the time being

d = globals()

try:
	from . import nidaqmx
except ValueError as e:
	#This kludge allows test.py to run in the same folder as this file
	if e.message == 'Attempted relative import in non-package':
		import nidaqmx
	else:
		raise

for name in dir(nidaqmx):
	if   name.startswith('DAQmx_'):
		d[name[6:]] = getattr(nidaqmx,name)
		c = name[6]
		assert 'A'<=c<='Z' or 'a'<=c<='z' or c== '_','%s is bad'%name
	elif name.startswith('DAQmx'):
		d[name[5:]] = getattr(nidaqmx,name)
		c = name[5]
		assert 'A'<=c<='Z' or 'a'<=c<='z' or c== '_','%s is bad'%name
del nidaqmx
del c, d


class Error(Exception):
	def __init__(self,errCode,errString,extErrString):
		self.errCode = errCode
		self.errString = errString
		self.extErrString = extErrString

	def __str__(self):
		return str((self.errCode,self.errString))

	def GetExtendedErrorString(self):
		return self.extErrString



def errcheck(result,func,args):
#	print dir(func)
#	print func._flags_
#	print func.paramflags
	if result != 0:
		print(args)
#		print result, args
#		print dir(func)
#		print func.argtypes
#		print func._argtypes_
#		print func.restype
#		print func._restype_
		raise Error(result,GetErrorString(result),GetExtendedErrorInfo())

#
# Code adapted from ctypes.decorators.stdcall, for fixed return type and
# dll, and automatic function name mangling in most cases (by prefixing
# 'DAQmx' to the Python method name.

def DAQmx (argtypes, apiName=None, restype=None, dll=_lib):
	"""DAQmx(argtypes, apiName=None, restype=None, dll=_lib) -> decorator.

	The decorator, when applied to a function, attaches an '_api_'
	attribute to the function.  Calling this attribute calls the
	function exported from the dll, using the MS '__stdcall' calling
	convention.

	argtypes - list of argument types
	apiName  - Name of C function (defaults to 'DAQmx' + function name
	restype - result type (None means error checked int32)
	dll - name or instance of a dll
	"""

	def decorate(func):
		if isinstance(dll, str):
			# this call should cache the result
			this_dll = ctypes.CDLL(dll)
		else:
			this_dll = dll
		if apiName is None:
			name = 'DAQmx' + func.__name__ #func.func_name
		else:
			name = apiName
		restype2 = int32 if restype is None else restype
		prototype = ctypes.WINFUNCTYPE(restype2, *argtypes)
		if name == 'DAQmxCreateTask':
#			print 'DAQmxCreateTask'
			paramflags = (1, 'taskname', None), (3, 'task', None)
			api = prototype((name, this_dll), paramflags)
		else:
			api = prototype((name, this_dll))
		if restype is None:
			api.errcheck = errcheck
		func._api_ = api
		return func
	return decorate


@DAQmx([int32, char_p, uInt32], restype=int32)
def GetErrorString(errCode):
	p = ctypes.create_string_buffer(2048)
	status = GetErrorString._api_(errCode,p,ctypes.sizeof(p))
	if status != 0:
		return 'Cannot get error string'
	return p.value

@DAQmx([char_p, uInt32], restype=int32)
def GetExtendedErrorInfo():
	p = ctypes.create_string_buffer(2048)
	status = GetExtendedErrorInfo._api_(p,ctypes.sizeof(p))
	if status != 0:
		return 'Cannot get extended error info'
	return p.value


# Perhaps this should be indented here, which means it would need to have
# the indenting stripped off before being used.

_roPropertyTemplate = \
				  """
@DAQmx([TaskHandle, PTR(%(proptype)s)])
def Get%(name)s (self):
	value = %(proptype)s()
	Task.Get%(name)s._api_(self, REF(value))
	return value.value

%(name)s =  property(Get%(name)s, None, None, %(docString)r)
"""

_rwPropertyTemplate = \
				  """
@DAQmx([TaskHandle, PTR(%(proptype)s)])
def Get%(name)s (self):
	value = %(proptype)s()
	Task.Get%(name)s._api_(self, REF(value))
	return value.value

@DAQmx([TaskHandle])
def Reset%(name)s (self):
	self.Reset%(name)s._api_(self)

@DAQmx([TaskHandle, %(proptype)s])
def Set%(name)s (self, value):
	if value is None:
		Task.Reset%(name)s_._api_(self)
	else:
		Task.Set%(name)s._api_(self, value)

%(name)s =  property(Get%(name)s, Set%(name)s, None, %(docString)r)
"""
#LOGGING = True



#def Property(function):
#   keys = 'Get', 'Set', 'Del'
#   func_locals = {'doc':function.__doc__}
#   def probeFunc(frame, event, arg):
#       if event == 'return':
#           locals = frame.f_locals
#           func_locals.update(dict((k,locals.get(k)) for k in keys))
#           sys.settrace(None)
#       return probeFunc
#   sys.settrace(probeFunc)
#   function()
#   return property(**func_locals)


class Task(object):
#	__slots__ = ['_task']
	_idMap = {}

	def __init__(self, taskName='', existing=False):
		if taskName is not None:
			if not existing:
				self.Create(taskName.encode('ASCII'))
			else:
				self.Load(taskName.encode('ASCII'))
		# Setup so passing a Task() object to ctypes passes the TaskHandle
		self._as_parameter_ = self._task

		#TODO: Need to remove deleted tasks from this dictionary
		Task._idMap[self._task.value] = self

#		print 'Creating new task: %s ID=%08lx' % (self, self._task.value)

	def __str__(self):
		p = ctypes.create_string_buffer(2048)
		status = _lib.DAQmxGetTaskName(self, p, ctypes.sizeof(p))
		return 'DAQmx.Task(%r)' % p.value

	def __repr__(self):
		return str(self)

	@staticmethod
	def GetTask(id):
		return Task._idMap[id]

	#TODO: All these functions to something like  Task.fct._api_(...)
	# I need a better way get the _api_ object from the current function in a class

	# Task Configuration and Control

	@DAQmx([char_p, PTR(TaskHandle)], apiName='DAQmxCreateTask')
	def Create(self,taskName):
		task = TaskHandle()
		Task.Create._api_(taskName,REF(task))
		self._task = task
		return task

	@DAQmx([char_p, PTR(TaskHandle)], apiName='DAQmxLoadTask')
	def LoadTask(self,taskName):
		task = TaskHandle()
		Task.Load._api_(taskName,REF(task))
		self._task = task
		return task

	@DAQmx([TaskHandle, char_p], apiName='DAQmxAddGlobalChansToTask')
	def AddGlobalChans(self, chanNames):
		Task.AddGlobalChansToTask._api_(self, chanNames)

	@DAQmx ([TaskHandle], apiName='DAQmxClearTask')
	def Clear(self):
		Task.Clear._api_(self)

	@DAQmx ([TaskHandle, PTR(bool32)], apiName='DAQmxIsTaskDone')
	def IsDone(self):
		done = bool32()
		Task.IsDone._api_(self, REF(done))
		return done.value

	@DAQmx ([TaskHandle], apiName='DAQmxStartTask')
	def Start(self):
		Task.Start._api_(self)

	@DAQmx ([TaskHandle], apiName='DAQmxStopTask')
	def Stop(self):
		Task.Stop._api_(self)

	# Task Configuration and Control / Events

	@DAQmx ([TaskHandle, uInt32, DoneEventCB, PYOBJ])
	def RegisterDoneEvent(self, options, cbFunc, cbData):
		Task.RegisterDoneEvent._api_(self, options, cbFunc, cbData)

	@DAQmx ([TaskHandle, int32, uInt32, uInt32, EveryNSamplesEventCB, PYOBJ])
	def RegisterEveryNSamplesEvent(self, eventType, nSamples, options, cbFunc, cbData):
		Task.RegisterEveryNSamplesEvent._api_(self, eventType, nSamples, options, cbFunc, cbData)

	@DAQmx ([TaskHandle, int32, uInt32, SignalEventCB, PYOBJ])
	def RegisterSignalEvent(self, signalID, options, cbFunc, cbData):
		Task.RegisterSignalEvent(self,  signalID, options, cbFunc, cbData)

	# Task Configuration and Control / Advanced

	@DAQmx ([TaskHandle, uInt32, char_p, int32], apiName='DAQmxGetNthTaskChannel')
	def GetNthChannel(self, index):
		buffer = ctypes.create_string_buffer(2048)
		Task.GetNthChannel._api_(self, index, buffer, ctypes.sizeof(buffer))
		return buffer.value

	@DAQmx ([TaskHandle, int32], apiName='DAQmxTaskControl')
	def Control (self, action):
		Task.Control._api_(self, action)



	# Channel Configuration/Creation / Create Analog Input Channels

	#TODO: CreateAIAccelChan

	@DAQmx ([TaskHandle, char_p, char_p, int32, float64, float64, int32, int32, float64, char_p])
	def CreateAICurrentChan(self, physChan, chanName, terminalConfig, minVal, maxVal, units=Val_Volts, shuntResistorLoc=Val_Internal, extshuntResistor=0.0, customScaleName=None):
		Task.CreateAICurrentChan._api_(self,physChan,chanName,terminalConfig,minVal,maxVal,units,shuntResistorVal,customVal,ScaleName)

	@DAQmx ([TaskHandle, char_p, char_p, int32, float64, float64, int32, float64, float64, char_p])
	def CreateAIFreqVoltageChan(self, physChan, chanName, terminalConfig, minVal, maxVal, units=Val_Volts, thresholdLevel=0.0,hysteresis=0.0, customScaleName=None):
		Task.CreateAIFreqVoltage._api_(self,physChan,chanName,terminalConfig,minVal,maxVal,units,thresholdValue,hysteresis,customVal,ScaleName)

	#TODO: CreateAIMicrophoneChan
	#TODO: CreateAIResistanceChan
	#TODO: CreateAIRTDChan
	#TODO: CreateAIStrainGaugeChan
	#TODO: CreateAITempBuiltinSensorChan
	@DAQmx ([TaskHandle, char_p, char_p, float64, float64, int32, int32, int32, float64, char_p])
	def CreateAIThrmcplChan(self, physChan, chanName, minVal, maxVal, units, tcType, cjcSource=Val_BuiltIn, cjcValue=0.0, cjcChannel=""):
		if isinstance(units, str):
			units = {'C':Val_DegC, 'F':Val_DegF, 'K':Val_Kelvins, 'R':Val_DegR}[units]
		if isinstance(tcType, str):
			tcType={'J':Val_J_Type_TC, 'K':Val_K_Type_TC, 'N':Val_N_Type_TC,
					'R':Val_R_Type_TC, 'S':Val_S_Type_TC, 'T':Val_T_Type_TC,
					'B':Val_B_Type_TC, 'E':Val_E_Type_TC}[tcType]
		Task.CreateAIThrmcplChan._api_(self,
					physChan.encode('ASCII'),chanName.encode('ASCII'),
					minVal,maxVal,units,tcType,cjcSource,cjcValue,
					cjcChannel.encode('ASCII'))
	#TODO: CreateAIThrmstrChanIex
	#TODO: CreateAIThrmstrChanVex

	@DAQmx ([TaskHandle, char_p, char_p, int32, float64, float64, int32, char_p])
	def CreateAIVoltageChan(self, physChan, chanName, terminalConfig, minVal, maxVal, units=Val_Volts, customScaleName=None):
		Task.CreateAIVoltageChan._api_(self,
					physChan.encode('ASCII'),chanName.encode('ASCII'),terminalConfig,minVal,maxVal,units,customScaleName)

	#TODO: CreateAIVoltageChanWithExcit
	#TODO: CreateAIPosLVDTChan
	#TODO: CreateAIPosRVDTChan


	# TODO: Create TEDS Analog Input Channels


	# Channel Configuration/Creation / Create Analog Output Channel

	@DAQmx ([TaskHandle, char_p, char_p, float64, float64, int32, char_p])
	def CreateAOCurrentChan(self, physChan, chanName, minVal, maxVal, units=Val_Amps, customScaleName=None):
		Task.CreateAOCurrentChan._api_(self,physChan,minVal,maxVal,units,customScaleName)

	@DAQmx ([TaskHandle, char_p, char_p, float64, float64, int32, char_p])
	def CreateAOVoltageChan(self, physChan, chanName, minVal, maxVal, units=Val_Volts, customScaleName=None):
		Task.CreateAOVoltageChan._api_(self,physChan,chanName,minVal,maxVal,units,customScaleName)

	# Channel Configuration/Creation / Create Digital Input Channels

	@DAQmx ([TaskHandle, char_p, char_p, int32])
	def CreateDIChan(self, lines, namesToAssignToLines, lineGrouping):
		Task.CreateDIChan._api_(self,lines,namesToAssignToLines,lineGrouping)

	# Channel Configuration/Creation / Create Digital Output Channels

	@DAQmx ([TaskHandle, char_p, char_p, int32])
	def CreateDOChan(self, lines, namesToAssignToLines, lineGrouping):
		Task.CreateDOChan._api_(self,lines,namesToAssignToLines,lineGrouping)

	# Channel Configuration/Creation / Create Counter Input Channels
	# TODO: Finish these

	@DAQmx ([TaskHandle, char_p, char_p, int32, uInt32, uInt32])
	def CreateCICountEdgesChan(self, counter, nameToAssign, edge, initialCount, countDirection):
		Task.CreateCICountEdgesChan._api_(self,counter,nameToAssign,edge,initialCount,countDirection)

	#TODO: CreateCIFreqChan
	#TODO: CreateCIPeriodChan
	#TODO: CreateCIPulseWidthChan
	#TODO: CreateCISemiPeriodChan
	#TODO: CreateTITwoEdgeSepChan
	#TODO: CreateCILinEncoderChan
	#TODO: CreateCIAngEncoderChan
	#TODO: CreaateCIGPSTimestampChan


	# Channel Configuration/Creation / Create Counter Output Channels

	@DAQmx ([TaskHandle, char_p, char_p, int32, int32, float64, float64, float64])
	def CreateCOPulseChanFreq(self,counter, nameToAssign, units, idleState, initialDelay, freq, dutyCycle):
		Task.CreateCOPulseChanFreq._api_(self,counter,nameToAssign,units,idleState,initialDelay,freq,dutyCycle)

	@DAQmx ([TaskHandle, char_p, char_p, int32, int32, int32, int32, int32])
	def CreateCOPulseChanTicks(self,counter, nameToAssign, units, idleState, initialDelay, highTicks, lowTicks):
		Task.CreateCOPulseChanTicks._api_(self,counter,nameToAssign,units,idleState,initialDelay,highTicks,lowTicks)

	@DAQmx ([TaskHandle, char_p, char_p, int32, int32, float64, float64, float64])
	def CreateCOPulseChanTime(self,counter, nameToAssign, units, idleState, initialDelay, highTime, lowTime):
		Task.CreateCOPulseChanTime._api_(self,counter,nameToAssign,units,idleState,initialDelay,highTime,lowTime)



	# Timing

	#TODO: CfgBurstHandshakingTimingExportClock
	#TODO: CfgBurstHandshakingTimingImportClock

	@DAQmx ([TaskHandle, char_p, char_p, int32, uInt64])
	def CfgChangeDetectionTiming(self,risingEdgeChan,fallingEdgeChan,sampleMode,sampsPerChan):
		Task.CfgChangeDetectionTiming._api_(self,risingEdgeChan,fallingEdgeChan,sampleMode,sampsPerChan)

	@DAQmx ([TaskHandle, int32, uInt64])
	def CfgHandshakingTiming(self, sampleMode, sampsPerChanToAcquire):
		Task.CfgHandshakingTiming._api_(self,sampleMode,sampsPerChanToAcquire)

	@DAQmx ([TaskHandle, int32, uInt64])
	def CfgImplicitTiming(self, sampleMode, sampsPerChanToAcquire):
		Task.CfgImplicitTiming._api_(self,sampleMode,sampsPerChanToAcquire)

	@DAQmx ([TaskHandle, char_p, float64, int32, int32, uInt64])
	def CfgSampClkTiming(self, source, rate, activeEdge, sampleMode, sampsToAcquire):
		Task.CfgSampClkTiming._api_(self,source,rate,activeEdge,sampleMode,sampsToAcquire)


	# Triggering

	#TODO: CfgAnlgEdgeStartTrig
	#TODO: CfgAnlgWindowStartTrig
	#TODO: CfgDigEdgeStartTrig
	#TODO: CfgDigPatternStartTrig
	#TODO: DisableStartTrig
	#TODO: CfgAnlgEdgeRefTrig
	#TODO: CfgAnlgWindowRefTrig
	#TODO: CfgDigEdgeRefTrig
	#TODO: CfgDigPatternRefTrig
	#TODO: CfgDigEdgeAdvTrig
	#TODO: DisableRefTrig

	@DAQmx ([TaskHandle, int32])
	def SendSoftwareTrigger(self, triggerID):
		Task.SendSoftwareTrigger._api_(self,triggerID)


	# Read Functions

	# Common read routine for functions that take a fillMode argument.
	# A 2-d array s always returned, even if only one channel is sampled
	# I don't really know how to handle reserved.  Right now is is never passed in or out

	# TODO: Make sure passed in readArray works properly when using background sampling
	# modes and EveryNSampleEvent callbacks.

	def _Read(self, fct, dtype, numSamplesPerChan, timeout, fillMode, readArray, arraySizeInSamps):
		numChans = self.GetNumChans()
		if numSamplesPerChan is None  or  numSamplesPerChan == -1:
			numSamplesPerChan = self.ReadAvailSampPerChan
		if readArray is None:
			if arraySizeInSamps is None:
				arraySizeInSamps = numChans * numSamplesPerChan
			readArray = (dtype * arraySizeInSamps)()
		else:
			if arraySizeInSamps is not None:
				arraySizeInSamps = len(readArray)
		sampsPerChanRead = int32()
		reserved = None
		fct._api_(self,numSamplesPerChan,timeout,fillMode,readArray,arraySizeInSamps,REF(sampsPerChanRead),reserved)

		#TODO: Decide what to return if there is no data available.
		#Currently returns a numChan x 0 array
		if sampsPerChanRead.value == 0:
			#print("samplesPerChanRead", sampsPerChanRead.value, numSamplesPerChan, arraySizeInSamps)
			values = numpy.zeros((numChans, 0), typemap[dtype])
			#values[:,:] = numpy.nan
			#print('values0', values)
			return values
			#return None
		#print('status', fct, status)

		values = numpy.array(readArray,typemap[dtype])
		if fillMode == Val_GroupByScanNumber:
			values.shape = (-1,numChans)
			values = values[0:sampsPerChanRead.value,:]
		else:
			# Is this correct for only partially filled buffers ?
			values.shape = (numChans,-1)
			values = values[:,0:sampsPerChanRead.value]
		#print('values', values)
		return values

	# Common read routine for functions that do not take a fillMode argument.
	# I assume this means only a single channel may be in the task.
	# A 1-d array is returned.
	# TODO: Deal with case of numSamplesPerChan = -1 (meaning read everything available)

	def _Read2(self, fct, dtype, numSamplesPerChan, timeout, readArray, arraySizeInSamps):
		numChans = self.GetNumChans()
		assert numChans == 1
		if readArray is None:
			if arraySizeInSamps is None:
				arraySizeInSamps = numChans * numSamplesPerChan
			readArray = (dtype * arraySizeInSamps)()
		else:
			if arraySizeInSamps is not None:
				arraySizeInSamps = len(readArray)
		sampsPerChanRead = int32()
		reserved = None
		fct._api_(self,numSamplesPerChan,timeout,readArray,arraySizeInSamps,REF(sampsPerChanRead),reserved)

		values = numpy.array(readArray,typemap[dtype])
		values = values[0:sampsPerChanRead.value]
		return values

	@DAQmx ([TaskHandle, int32, float64, bool32, PTR(float64), uInt32, PTR(int32), PTR(bool32)])
	def ReadAnalogF64(self, numSamplesPerChan, timeout, fillMode, readArray=None,arraySizeInSamps=None):
		return self._Read(Task.ReadAnalogF64,float64,numSamplesPerChan,timeout,fillMode,readArray,arraySizeInSamps)

	@DAQmx ([TaskHandle, float64, PTR(float64), PTR(bool32)])
	def ReadAnalogScalarF64(self, timeout=-1):
		value = float64()
		Task.ReadAnalogScalarF64._api_(self,timeout,REF(value),None)
		return value.value

	@DAQmx ([TaskHandle, int32, float64, bool32, PTR(int16), uInt32, PTR(int32), PTR(bool32)])
	def ReadBinaryI16(self, numSamplesPerChan, timeout, fillMode, readArray=None, arraySizeInSamps=None):
		return self._Read(Task.ReadBinaryI16,int16,numSamplesPerChan,timeout,fillMode,readArray,arraySizeInSamps)

	@DAQmx ([TaskHandle, int32, float64, bool32, PTR(int32), uInt32, PTR(int32), PTR(bool32)])
	def ReadBinaryI32(self, numSamplesPerChan, timeout, fillMode, readArray=None, arraySizeInSamps=None):
		return self._Read(Task.ReadBinaryI32,int32,numSamplesPerChan,timeout,fillMode,readArray,arraySizeInSamps)

	@DAQmx ([TaskHandle, int32, float64, bool32, PTR(uInt16), uInt32, PTR(int32), PTR(bool32)])
	def ReadBinaryU16(self, numSamplesPerChan, timeout, fillMode, readArray=None, arraySizeInSamps=None):
		return self._Read(Task.ReadBinaryU16,uInt16,numSamplesPerChan,timeout,fillMode,readArray,arraySizeInSamps)

	@DAQmx ([TaskHandle, int32, float64, bool32, PTR(uInt32), uInt32, PTR(int32), PTR(bool32)])
	def ReadBinaryU32(self, numSamplesPerChan, timeout, fillMode, readArray=None, arraySizeInSamps=None):
		return self._Read(Task.ReadBinaryU32,uInt32,numSamplesPerChan,timeout,fillMode,readArray,arraySizeInSamps)

	@DAQmx ([TaskHandle, int32, float64, PTR(float64), uInt32, PTR(int32), PTR(bool32)])
	def ReadCounterF64(self, numSamplesPerChan, timeout, readArray=None,arraySizeInSamps=None):
		return self._Read2(Task.ReadCounterF64,float64,numSamplesPerChan,timeout,readArray,arraySizeInSamps)

	@DAQmx ([TaskHandle, float64, PTR(float64), PTR(bool32)])
	def ReadCounterScalarF64(self, timeout=-1):
		value = float64()
		Task.ReadCounterScalarF64._api_(self,timeout,REF(value),None)
		return value.value

	@DAQmx ([TaskHandle, float64, PTR(uInt32), PTR(bool32)])
	def ReadCounterScalarU32(self, timeout=-1):
		value = uInt32()
		Task.ReadCounterScalarU32._api_(self,timeout,REF(value),None)
		return value.value

	@DAQmx ([TaskHandle, int32, float64, PTR(float64), uInt32, PTR(int32), PTR(bool32)])
	def ReadCounterU32(self, numSamplesPerChan, timeout, readArray=None,arraySizeInSamps=None):
		return self._Read2(Task.ReadCounterU32,uInt32,numSamplesPerChan,timeout,readArray,arraySizeInSamps)


	# TODO:
	# This one is funny as the number of bytes/sample varies
	#	@DAQmx ([TaskHandle, int32, float64, bool32, PTR(uInt8), uInt32, PTR(int32), PTR(int32), PTR(bool32)]
	#	def ReadDigitalLinesself, numSamplesPerChan, timeout, fillMode, readArray=None, arraySizeInBytes=None):
	#		pass

	@DAQmx ([TaskHandle, float64, PTR(uInt32), PTR(bool32)])
	def ReadDigitalScalarU32(self, timeout=-1):
		value = uInt32()
		Task.ReadDigitalScalarU32._api_(self, timeout, REF(value), None)
		return value.value

	@DAQmx ([TaskHandle, int32, float64, bool32, PTR(uInt8), uInt32, PTR(int32), PTR(bool32)])
	def ReadDigitalU8(self, numSamplesPerChan, timeout, fillMode, readArray=None, arraySizeInSamps=None):
		return self._Read(Task.ReadDigitalU8,uInt8,numSamplesPerChan,timeout,fillMode,readArray,arraySizeInSamps)

	@DAQmx ([TaskHandle, int32, float64, bool32, PTR(uInt16), uInt32, PTR(int32), PTR(bool32)])
	def ReadDigitalU16(self, numSamplesPerChan, timeout, fillMode, readArray=None, arraySizeInSamps=None):
		return self._Read(Task.ReadDigitalU16,uInt16,numSamplesPerChan,timeout,fillMode,readArray,arraySizeInSamps)

	@DAQmx ([TaskHandle, int32, float64, bool32, PTR(uInt32), uInt32, PTR(int32), PTR(bool32)])
	def ReadDigitalU32(self, numSamplesPerChan, timeout, fillMode, readArray=None, arraySizeInSamps=None):
		return self._Read(Task.ReadDigitalU32,uInt32,numSamplesPerChan,timeout,fillMode,readArray,arraySizeInSamps)

	#TODO:
	#	@DAQmx ([TaskHandle, uInt32, char_p, int32], api="DAQmxGetNthTaskReadChannel")
	#	def GetNthReadChannel (TaskHandle taskHandle, uInt32 index, bufferSize);

	#TODO:	ReadRaw


	# Write Functions

	# Common write function for functions that have a dataLayout argument.
	# Must be fixed for multiple channels.
	# Is this best way to handle numSampsPerChan?

	def _Write(self,fct,dtype,numSampsPerChan,autoStart,timeout,dataLayout,writeArray):
		numChans = self.GetNumChans()
		#assert numChans == 1
		if numSampsPerChan is None:
			numSampsPerChan = len(writeArray) / numChans
		numItems = numChans * numSampsPerChan

		#TODO: When would we need a cast here?
		# There should be a better way than an element by element copy to do this
		# even when we need the cast operation
		writeBuffer = (dtype * numItems)()
		for i in range(numItems):
			writeBuffer[i] = writeArray[i]
		#print(dtype, writeBuffer)
		sampsPerChanWritten = int32()
		reserved = None
		fct._api_(self,numSampsPerChan,autoStart,timeout,dataLayout,writeBuffer, REF(sampsPerChanWritten),reserved)
		return sampsPerChanWritten.value

	@DAQmx ([TaskHandle, int32, bool32, float64, bool32, PTR(float64), PTR(int32), PTR(bool32)])
	def WriteAnalogF64(self,numSampsPerChan,autoStart,timeout,dataLayout,writeArray):
		return self._Write(Task.WriteAnalogF64,float64,numSampsPerChan,autoStart,timeout,dataLayout,writeArray)

	@DAQmx ([TaskHandle, bool32, float64, float64, PTR(bool32)])
	def WriteAnalogScalarF64(self,autoStart,timeout,value):
		Task.WriteAnalogScalarF64._api_(self, autoStart, timeout, value, None)

	@DAQmx ([TaskHandle, int32, bool32, float64, bool32, PTR(int16), PTR(int32), PTR(bool32)])
	def WriteBinaryI16(self,numSampsPerChan,autoStart,timeout,dataLayout,writeArray):
		return self._Write(Task.WriteBinaryI16,int16,numSampsPerChan,autoStart,timeout,dataLayout,writeArray)

	@DAQmx ([TaskHandle, int32, bool32, float64, bool32, PTR(uInt16), PTR(int32), PTR(bool32)])
	def WriteBinaryU16(self,numSampsPerChan,autoStart,timeout,dataLayout,writeArray):
		return self._Write(Task.WriteBinaryU16,uInt16,numSampsPerChan,autoStart,timeout,dataLayout,writeArray)

	#TODO: WriteCtrFreq

	@DAQmx ([TaskHandle, bool32, float64, float64, float64, PTR(bool32)])
	def WriteCtrFreqScalar(self,autoStart,timeout,frequency,dutyCycle):
		return Task.WriteCtrFreqScalar._api_(self,autoStart,timeout,frequency,dutyCycle,None)

	#TODO: WriteCtrTicks

	@DAQmx ([TaskHandle, bool32, float64, uInt32, uInt32, PTR(bool32)])
	def WriteCtrTicksScalar(self,autoStart,timeout,highTicks,lowTicks):
		return Task.WriteCtrTicksScalar._api_(self,autoStart,timeout,highTicks,lowTicks,None)

	#TODO: WriteCtrTime

	@DAQmx ([TaskHandle, bool32, float64, float64, float64, PTR(bool32)])
	def WriteCtrTimeScalar(self,autoStart,timeout,highTime,lowTime):
		return Task.WriteCtrTimeScalar._api_(self,autoStart,timeout,highTime,lowTime,None)

	#TODO: WriteDigitalLines

	@DAQmx ([TaskHandle, bool32, float64, uInt32, PTR(bool32)])
	def WriteDigitalScalarU32(self,autoStart,timeout,value):
		Task.WriteDigitalScalarU32._api_(self, autoStart, timeout, value, None)

	@DAQmx ([TaskHandle, int32, bool32, float64, bool32, PTR(uInt8), PTR(int32), PTR(bool32)])
	def WriteDigitalU8(self,numSampsPerChan,autoStart,timeout,dataLayout,writeArray):
		return self._Write(Task.WriteDigitalU8,uInt8,numSampsPerChan,autoStart,timeout,dataLayout,writeArray)

	@DAQmx ([TaskHandle, int32, bool32, float64, bool32, PTR(uInt16), PTR(int32), PTR(bool32)])
	def WriteDigitalU16(self,numSampsPerChan,autoStart,timeout,dataLayout,writeArray):
		return self._Write(Task.WriteDigitalU16,uInt16,numSampsPerChan,autoStart,timeout,dataLayout,writeArray)

	@DAQmx ([TaskHandle, int32, bool32, float64, bool32, PTR(uInt32), PTR(int32), PTR(bool32)])
	def WriteDigitalU32(self,numSampsPerChan,autoStart,timeout,dataLayout,writeArray):
		return self._Write(Task.WriteDigitalU32,uInt32,numSampsPerChan,autoStart,timeout,dataLayout,writeArray)

	#TODO: WriteRaw

	# Export HW Signal
	@DAQmx ([TaskHandle, int32, char_p])
	def ExportSignal(self, signalID, outputTerminal):
		Task.ExportSignal(self, signalID, outputTerminal)


	# Scale Configuration

	#TODO: CalculateReversePolyCoeff
	#TODO: CreateLinScale
	#TODO: CreateMapScale
	#TODO: CreatePolynomialScale
	#TODO: CreateTableScale


	# Internal Buffer Configuration

	@DAQmx ([TaskHandle, uInt32])
	def CfgInputBuffer(numSampsPerChan):
		Task.CfgInputBuffer._api_(self,numSampsPerChan)

	@DAQmx ([TaskHandle, uInt32])
	def CfgOutputBuffer(numSampsPerChan):
		Task.CfgOutputBuffer._api_(self,numSampsPerChan)


	# Advanced Functions

	#TODO: WaitForNextSampleClock

	@DAQmx ([TaskHandle, float64], apiName='DAQmxWaitUntilTaskDone')
	def WaitUntilDone(self, timeout=-1):
		Task.WaitUntilDone._api_(self,timeout)

	#TODO:  Many more go here

	# System Configuration

	#TODO: SetAnalogPowerUpStates
	#TODO: SetDigitalPowerUpStates

	# Error Handling
	# These are not members of the class `Task'

	# Properties
	@DAQmx ([TaskHandle, PTR(int32)], apiName='DAQmxGetTaskNumChans')
	def GetNumChans(self):
		numChans = int32()
		Task.GetNumChans._api_(self,REF(numChans))
		return numChans.value
	NumChans = property(GetNumChans, None, None, 'Number of channels')

	_properties = (
#		('NumChans',			'int32',	'Number of channels'			),
		('ReadAvailSampPerChan','uInt32',	'Num. available samples/chan'),
		('SampClkMaxRate',		'float64',	'Maximum sample clock rate'		),
	)
	for _name, _type, _doc  in _properties:
		exec(_roPropertyTemplate % {'name':_name, 'proptype':_type, 'docString':_doc})


	_properties = (
		('AIConvRate',			'float64',	'Analog input conversion rate'	),
		('ReadAutoStart',		'bool32',	'Read autostart'				),
		('SampClkRate',			'float64',	'Sample clock rate'				),
		('SampQuantSampMode',	'int32',	'Sample quantity sample mode'	),
		('SampTimingType',		'int32',	'Sample timing type'			),
	)

	for _name, _type, _doc  in _properties:
		exec(_rwPropertyTemplate % {'name':_name, 'proptype':_type, 'docString':_doc})
	del _name, _type, _doc
	del _properties

del _roPropertyTemplate, _rwPropertyTemplate




if __name__ == "__main__":
	import time
	import numpy

	#TODO: Need way to map the task id back to a task object somehow
	#probably with a static dictionary within class Task.

	def OnTaskDone(task, status, data):
		print('OnTaskDone %08x %5d %s' % (task,status,data))
		return 0

	def OnNSamples(task,eventType,nSamples,data):
		data[0] += nSamples
		print('OnNSamples %08x %5d %6d %6d %10.6f' % (task,eventType,nSamples,data[0], time.clock()-data[1]))
		return 0

	tasks = []

	data = [0,0]		# Make external to task so tht it does not disappear too fast

	# Create a single task, measuring two channels at 2000 Hz for
	# 5000 samples/channel.  A callback is made every 1000 samples and at
	# sample completion.
	def Test1 ():
		start = time.clock()
		print('Creating task')
		task1 = Task('AI Task')
		tasks.append(task1)
		print('Configuring Channels')
		task1.CreateAIVoltageChan("dev3/ai0:1", "", Val_RSE, 0, 5)
		print('Task1 Channels',task1.GetNthChannel(1), task1.GetNthChannel(2))
		#task1.SampTimingType = Val_SampClk
		#task1.SampClkRate = 2000
		#task1.SampQuantSampMode = Val_FiniteSamps
		task1.CfgSampClkTiming(None, 2000, Val_Rising, Val_FiniteSamps, 5000)

		task1.RegisterEveryNSamplesEvent(Val_Acquired_Into_Buffer, 1000, 0, OnNSamples, data)
		task1.RegisterDoneEvent(0, OnTaskDone, data)

		data[0] = 0
		data[1] = start
		# Seemingly the A/D conversion processes starts now, and the ReadAnalogF64
		# routine simply collects the first 5000 measurements made ?
		# How are they buffered?  Continues to run until Stop() is called.
		# AutoStart works if there are no callbacks setup.
		# In FiniteSamps mode it stops automatically after stated sample count.
		print('Starting task',time.clock()-start)
		task1.Start()
		print('Starting read',time.clock()-start)
		time.sleep(5)
		#print task1.ReadAvailSampPerChan
		values = task1.ReadAnalogF64(-1, -1, Val_GroupByChannel)
		print('Read Complete',values.shape,values.mean(axis=1))
		print('Explicitly stopping task',time.clock()-start)
		task1.Stop()


	# Create a single task, continuously measuring 2 channels at 2000 Hz.
	# The buffer size is the larger of the value specificed (5000) and the
	# minimum for that sample rate (10000).
	def Test2 ():
		start = time.clock()
		print('Creating task')
		task1 = Task('AI')
		tasks.append(task1)
		print('Configuring Channels 2',time.clock()-start)
		task1.CreateAIVoltageChan("dev1/ai0:1", "", Val_RSE, 0, 5)
		print('Task1 Channels',task1.GetNthChannel(1), task1.GetNthChannel(2))
		task1.CfgSampClkTiming(None, 2000, Val_Rising, Val_ContSamps, 5000)

		print('Starting task',time.clock()-start)
		task1.Start()
		print('Starting read',time.clock()-start)
		for i in range(5):
			time.sleep(1)
			# This simply reads all available data
			values = task1.ReadAnalogF64(-1, -1, Val_GroupByChannel)
			print('Read Complete', time.clock()-start, values.shape ,values.mean(axis=1))
		print('Explicitly stopping task',time.clock()-start)
		task1.Stop()


	def Test3():
		start = time.clock()
		print('Creating tasks', '%.3f' % (time.clock()-start))
		task1 = Task('AI Task')
		task2 = Task('AO Task')
##		task3 = Task('DI Task')
##		task4 = Task('DO Task')
		task5 = Task('CI Task')
		for task in [task1, task2, task5]:
			tasks.append(task)

		print('Configuring channels', '%.3f' % (time.clock()-start))
		task1.CreateAIVoltageChan("dev1/ai0:1", "", Val_RSE, 0, 5)
		task2.CreateAOVoltageChan("dev1/ao0", "", 0, 5)
#		task2.SampTimingType = Val_OnDemand
#		task2.CfgSampClkTiming(None,1000,Val_Rising,Val_FiniteSamps,1000)
##		task3.CreateDIChan("dev3/port0", "", Val_ChanForAllLines)
#3		task4.CreateDOChan("dev3/port1", "", Val_ChanForAllLines)
		task5.CreateCICountEdgesChan("dev1/ctr0", "", Val_Falling, 0, Val_CountUp)


		# The default is Val_OnDemand, which is effectively free running
		task1.SampTimingType = Val_SampClk
		#print task1.SampClkMaxRate
		task1.SampClkRate = 1000
#		task1.CfgSampClkTiming(None,2000,Val_Rising,Val_FiniteSamps,10000)

		#print task1.AIConvRate
		# task1.AIConvRate = 10000

		# This essentially stops the task after each command, rather than
		# having it free run, as with the default Val_ContSamps, where it
		# continues to sample between calls.  Naturally that messes up
		# the test mode where the D/A output must be set before reading the
		# feedback.  Another way is to stop the task after each sample.
		task1.SampQuantSampMode = Val_FiniteSamps

#		print task1.NumChans, task2.NumChans, task3.NumChans

#		print('Starting tasks', '%.3f' % (time.clock()-start))
#		task1.Start()
#		task2.Start()
#		task3.Start()
#		task4.Start()
#		task5.Start()

#		time.sleep(0.5)

		print('Sample Loop', '%.3f' % (time.clock()-start))
		for i in range(0,10):
			vo = (5*i/10.0, 5*i/10.0)
			# On the USB-6008 this seems to always truncate down to
			# the next integral voltage value.  Apparently the device
			# does not support any buffered output modes at all, so
			# I am not sure why this works at all.
#			task2.WriteAnalogF64(None,True,-1,Val_GroupByScanNumber,
#					[[vo[0]] * 50])
#			task2.WriteBinaryI16(None,True,-1,Val_GroupByScanNumber,
#				[[int(vo[0]*800), int(vo[1]*800)] * 5])
			task2.WriteAnalogScalarF64(True,-1,vo[0])
#				task2.WaitUntilDone()

			values = task1.ReadBinaryU16(100,-1,Val_GroupByScanNumber)
#			task1.WaitUntilDone()
#			task1.Stop()

			# These factors were determined empirically. They seem stable
			# (at least after a long warmup)
			avg1 = (values.mean(axis=0) - 32278) / 3145.0

			#t = time.clock()
			#values = task1.ReadAnalogF64(100,-1,Val_GroupByChannel)
			#task1.Stop()
			#t = time.clock() - t
			#avg2 = values.mean(axis=1)

			time.sleep(0.05)

#			doBits = i;
#			task4.WriteDigitalScalarU32(True,-1,doBits)
 ##			diBits = task3.ReadDigitalScalarU32() & 0x03
			diBits = 0

##			task4.WriteDigitalU32(None,True,-1,Val_GroupByScanNumber,range(20))
			ctr = task5.ReadCounterScalarU32()

			#print values
			#print task5.ReadCounterScalarF64(), task5.ReadCounterScalarU32()
			print('%6.3f  %6.3f   %6.3f %6.3f  %6.3f %6.3f   %02lx %5d %5.3f' % 
				  (vo[0], vo[1],  avg1[0], avg1[1], avg2[0], avg2[1], diBits, ctr, t))

			#time.sleep(1)


	print('New Run')
	start = time.clock()
	try:
		try:
			#Test1()
			#Test2()
			Test3()
		except Error as e:
			print
			#print 'DAQmx Error:',e.errCode
			#print
			#print '***Error String***'
			#print e.errString
			#print
			print('***Extended Error String***')
			print(e.extErrString)
			print
			#print '***Traceback***'
			#traceback.print_exc(file=sys.stderr)
		except RuntimeError as e:
			pass
	finally:
			# Clearing tasks automatically stops them first
			# time.sleep(1)
			print('Clearing tasks', '%.3f' % (time.clock()-start))
			for task in tasks:
				task.Clear()

