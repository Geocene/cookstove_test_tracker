import sys
import time
import traceback

import numpy as np

import DAQmx

tasks = []


class cbData:
	def __init__(self, startTime):
		self.done = False
		self.nSamples = 0
		self.startTime = startTime

# Create a single task, measuring four channels at 2000 Hz/channel
# for 5000 samples/channel.
# A callback is made every 1000 samples and at sample completion.
def Test1 ():
	print "Test1"

	# Callback for every N Samples
	def OnNSamples(taskID, eventType, nSamples, cbData):
		task = DAQmx.Task.GetTask(taskID) 
		cbData.nSamples += nSamples
		print 'OnNSamples %08x %s %d %6d %6d %10.6f' % (taskID, task, eventType, nSamples, cbData.nSamples, time.clock()-cbData.startTime)
		return 0

	# Callback for task done
	def OnTaskDone(taskID, status, cbData):
		task = DAQmx.Task.GetTask(taskID) 
		print 'OnTaskDone %08x %s %d %6d %10.6f' % (taskID, task, status, data.nSamples, time.clock()-cbData.startTime)
		cbData.done = True
		return 0

	start = time.clock()
	data = cbData(start)	

	print 'Creating task'
	task1 = DAQmx.Task('AI Task')
	tasks.append(task1)
	print 'Configuring Channels'
	task1.CreateAIVoltageChan("dev2/ai0:3", "", DAQmx.Val_RSE, 0, 5)
#	task1.CreateAIThrmcplChan("dev1/ai0:3", "", 0, 500,DAQmx.Val_DegC, DAQmx.Val_K_Type_TC,
#						DAQmx.Val_BuiltIn, 0, "")
	print 'Task1 Channels',task1.GetNthChannel(1), task1.GetNthChannel(2), task1.GetNthChannel(3), task1.GetNthChannel(4)
	#task1.SampTimingType = Val_SampClk
	#task1.SampClkRate = 2000
	#task1.SampQuantSampMode = Val_FiniteSamps
	task1.CfgSampClkTiming(None, 2000, DAQmx.Val_Rising, DAQmx.Val_FiniteSamps, 10000)

	# This can't go away until the task has completed so no more callbacks occur
	onNSamplesCB = DAQmx.EveryNSamplesEventCB(OnNSamples)
	onTaskDoneCB = DAQmx.DoneEventCB(OnTaskDone)
	task1.RegisterEveryNSamplesEvent(DAQmx.Val_Acquired_Into_Buffer, 1000, 0, onNSamplesCB, data)
	task1.RegisterDoneEvent(0, onTaskDoneCB, data)


	# AutoStart works if there are no callbacks setup.
	# In FiniteSamps mode it stops automatically after stated sample count.

	print 'Starting task',time.clock()-start
	task1.Start()

	print 'Waiting for task completion',time.clock()-start
	while not data.done:
		time.sleep(0.1)
		#print task1.ReadAvailSampPerChan

	print 'Reading data',time.clock()-start
	values = task1.ReadAnalogF64(-1, -1, DAQmx.Val_GroupByChannel)

	print 'Read Complete', values.shape, values.mean(axis=1)
	print 'Explicitly stopping task', time.clock()-start
	task1.Stop()




# Create a single task, continuously measuring 2 channels at 2000 Hz.
# The buffer size is the larger of the value specificed (5000) and the
# minimum for that sample rate (10000).
def Test2 ():
	print "Test2"

	start = time.clock()
	print 'Creating task'
	task1 = DAQmx.Task('AI')
	tasks.append(task1)
	print 'Configuring Channels 2', time.clock()-start
#	task1.CreateAIVoltageChan("dev1/ai0:1", "", DAQmx.Val_RSE, 0, 5)
	task1.CreateAIThrmcplChan("dev1/ai0:3", "", 0, 500, DAQmx.Val_DegC, DAQmx.Val_K_Type_TC,
						DAQmx.Val_BuiltIn, 0, "")
	print 'Task1 Channels', task1.GetNthChannel(1), task1.GetNthChannel(2)
	task1.CfgSampClkTiming(None, 2, DAQmx.Val_Rising, DAQmx.Val_ContSamps, 2)

	print 'Starting task',time.clock()-start
	task1.Start()
	print 'Starting read',time.clock()-start
	for i in range(5):
		time.sleep(1)
		# This simply reads all available data
		values = task1.ReadAnalogF64(-1, -1, DAQmx.Val_GroupByChannel)
		#print(values.shape)
		if values is None  or values.shape[1] == 0:
			print 'Read Complete', time.clock()-start, values, "None", values.shape
		else:
			print 'Read Complete', time.clock()-start, values.shape ,values.mean(axis=1)
	print 'Explicitly stopping task',time.clock()-start
	task1.Stop()




def Test3():
	print "Test3"

	start = time.clock()
	print 'Creating tasks', '%.3f' % (time.clock()-start)
	aiTask = DAQmx.Task('AI Task')
	aoTask = DAQmx.Task('AO Task')
	diTask = DAQmx.Task('DI Task')
	doTask = DAQmx.Task('DO Task')
	ciTask = DAQmx.Task('CI Task')
	for task in [aiTask, aoTask, diTask, doTask, ciTask]:
		tasks.append(task)

	#TODO: Channels around 8 don't seem to be connected.  Check wiring!!!
	print 'Configuring channels', '%.3f' % (time.clock()-start)
	aiTask.CreateAIVoltageChan("dev2/ai14:15", "", DAQmx.Val_RSE, -10, 10)
	# The default is Val_OnDemand, which is effectively free running
	aiTask.SampTimingType = DAQmx.Val_SampClk
	#print aiTask.SampClkMaxRate
	aiTask.SampClkRate = 1000
#	aiTask.CfgSampClkTiming(None,2000,Val_Rising,Val_FiniteSamps,10000)
	#print aiTask.AIConvRate
	# aiTask.AIConvRate = 10000

	aoTask.CreateAOVoltageChan("dev2/ao0:1", "", 0, 10)
#	aoTask.SampTimingType = Val_OnDemand
#	aoTask.CfgSampClkTiming(None,1000,Val_Rising,Val_FiniteSamps,1000)

	diTask.CreateDIChan("dev2/port0/line0:3", "", DAQmx.Val_ChanForAllLines)

	doTask.CreateDOChan("dev2/port0/line4:7", "", DAQmx.Val_ChanForAllLines)

	ciTask.CreateCICountEdgesChan("dev2/ctr0", "", DAQmx.Val_Falling, 0, DAQmx.Val_CountUp)


	# This essentially stops the task after each command, rather than
	# having it free run, as with the default Val_ContSamps, where it
	# continues to sample between calls.  Naturally that messes up
	# the test mode where the D/A output must be set before reading the
	# feedback.  Another way is to stop the task after each sample.
	#aiTask.SampQuantSampMode = DAQmx.Val_FiniteSamps

#		print aiTask.NumChans, aoTask.NumChans, diTask.NumChans

#		print 'Starting tasks', '%.3f' % (time.clock()-start)
#		aiTask.Start()
#		aoTask.Start()
#		diTask.Start()
#		doTask.Start()
#		ciTask.Start()

#		time.sleep(0.5)

	aiTask.Start()
	for i in range(10):
		start = time.clock()

		#vo = [5,0]
		vo = (5*i/10.0, 5*i/10.0)
		vo = np.array(vo, dtype=np.float64)
		# On the USB-6008 this seems to always truncate down to
		# the next integral voltage value.  Apparently the device
		# does not support any buffered output modes at all, so
		# I am not sure why this works at all.
#		aoTask.WriteAnalogF64(None,True,-1,Val_GroupByScanNumber,
#				[[vo[0]] * 50])
#		aoTask.WriteBinaryI16(None,True,-1,Val_GroupByScanNumber,
#			[[int(vo[0]*800), int(vo[1]*800)] * 5])
#		aoTask.WriteAnalogScalarF64(True, -1, vo[0])
		aoTask.WriteAnalogF64(1, True, -1, DAQmx.Val_GroupByScanNumber, vo)

		# Flush any old values that appeared before the D/A changed voltage
		values = aiTask.ReadAnalogF64(-1, -1, DAQmx.Val_GroupByScanNumber)

		time.sleep(0.5)

		#Check the data type for U16.  I might well have a signed value
		avg1 = [0,0]
		#values = aiTask.ReadBinaryU16(-1, -1, DAQmx.Val_GroupByScanNumber)
		#avg1 = values.mean(axis=0)
		#print(values.shape)
		#print(avg1)
		# These factors were determined empirically. They seem stable
		# (at least after a long warmup)
		#avg1 = (values.mean(axis=0) - 32278) / 3145.0
		# Values for the HCCI computer, +/- 10Volt range
		#avg1 = 2280 - values.mean(axis=0)
		

#		time.sleep(0.2)
		values = aiTask.ReadAnalogF64(-1, -1, DAQmx.Val_GroupByScanNumber)
		#print(values.shape)
		#print(values.mean(axis=0))
#		values = aiTask.ReadAnalogF64(100, -1, DAQmx.Val_GroupByChannel)
		avg2 = values.mean(axis=0)
		#print(avg2)


		diBits = diTask.ReadDigitalScalarU32()

#		doBits = i;
#		doTask.WriteDigitalScalarU32(True, -1, doBits)
		doTask.WriteDigitalU32(20, True, -1, DAQmx.Val_GroupByScanNumber, range(20))

		ctr = ciTask.ReadCounterScalarU32()

		t = (time.clock() - start) * 1000.0

		#print values
		#print ciTask.ReadCounterScalarF64(), ciTask.ReadCounterScalarU32()
		#print(avg1)
		#print(avg2)
		print '%6.3f  %6.3f   %6.3f %6.3f  %6.3f %6.3f   %02lx %5d %5.3f ms' % \
			  (vo[0], vo[1],  avg1[0], avg1[1], avg2[0], avg2[1], diBits, ctr, t)


#	for task in tasks:
#		task.Stop()


print 'New Run'
start = time.clock()
try:
	try:
		#Test1()
		#Test2()
		Test3()
	except DAQmx.Error, e:
		print
		print 'DAQmx Error:',e.errCode
		print
		print '***Error String***'
		print e.errString
		print
		print '***Extended Error String***'
		print e.extErrString
		print
		print '***Traceback***'
		traceback.print_exc(file=sys.stderr)
	except RuntimeError, e:
		pass
finally:
		# Clearing tasks automatically stops them first
		# time.sleep(1)
		print 'Clearing tasks', '%.3f' % (time.clock()-start)
		for task in tasks:
			task.Clear()

