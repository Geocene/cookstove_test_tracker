import ctypes
#mport NIDAQmx as ni

int8 = ctypes.c_byte
uInt8 = ctypes.c_ubyte
int16 = ctypes.c_short
uInt16 = ctypes.c_ushort
int32 = ctypes.c_long
uInt32 = ctypes.c_ulong
float32 = ctypes.c_float
float64 = ctypes.c_double
int64 = ctypes.c_longlong
uInt64 = ctypes.c_ulonglong
bool32 = uInt32

TaskHandle = uInt32
STRING = ctypes.c_char_p

def errcheck (result, func, args):
	print 'errCheck', result, args
	if result != 0:
		raise RuntimeError(result)
	return args

if 0:
	prototype = ctypes.WINFUNCTYPE(uInt32, STRING, ctypes.POINTER(TaskHandle))
	paramflags = ((1, 'name', ''),  (3, 'Handle', 0))
	CreateTask = prototype(("DAQmxCreateTask", ctypes.windll.nicaiu), paramflags)
	CreateTask.errcheck = errcheck
else:
	CreateTask = ctypes.windll.nicaiu.DAQmxCreateTask
	CreateTask.argtypes = [STRING, ctypes.POINTER(TaskHandle)]
	CreateTask.errcheck = errcheck

#def CreateTask(taskName=""):
#	task = ni.TaskHandle()
#	xxx = ni.DAQmxCreateTask(ni.STRING(taskName),task)
#	print xxx
#	return xxx
#	#return task

#def StartTask(task):
#	return ni.DAQmxStartTask(task)


#def GetErrorString(errCode):
#	p = ctypes.create_string_buffer(2048)
#	status = ni.DAQmxGetErrorString(errCode,p,ctypes.sizeof(p))
#	if status != 0:
#		return 'Cannot get error string'
#	return p.value

task = CreateTask('TaskXXX', TaskHandle())
print 'task',task
#code =  StartTask(task)
#print code
#print GetErrorString(code)
