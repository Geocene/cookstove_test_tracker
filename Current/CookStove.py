#
# CookStove.py
# LBNL Cook Stoves Project DAQ Program
#

from __future__ import absolute_import, division, print_function

import os
import sys
import time
import math
import socket
import warnings
import traceback

import serial
import numpy as np

import wx
import wx.lib.inspection
#import wx.lib.agw.infobar
#if not hasattr(wx.DCFontChanger, "__enter__"):
#	#This seems to be missing in non-Phoenix wxPython
#	wx.DCFontChanger.__enter__ = lambda self: self
#	wx.DCFontChanger.__exit__ = lambda self, exc_type, exc_val, exc_tb: False

if wx.VERSION >= (4,0):
#	print("Patch for Phoenix")
	wx.PyControl = wx.Control
	wx.EmptyBitmap = wx.Bitmap
	wx.BitmapFromImage = wx.Bitmap


import matplotlib as mpl
mpl.use('WXAgg')

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
#from matplotlib.backends.backend_wx import NavigationToolbar2Wx

#try:
#	np.ma.masked._fill_value
#except AttributeError as e:
#	print("Patching numpy error", e)
#	np.ma.masked._fill_value = 1e20

#I think all these undo matplotlib 2.0 changes.  (xy)tick.top not in 1.5
if mpl.__version__ >= "2.0":
	#print("set rcParams")
	mpl.rcParams['figure.facecolor'] = '0.75'
	mpl.rcParams['font.weight'] = 'bold'
	mpl.rcParams['axes.labelweight'] = 'bold'
	mpl.rcParams['legend.framealpha'] = None
	mpl.rcParams['xtick.direction'] = 'in'		# Alignment does not work right w/ outward going ticks
	mpl.rcParams['ytick.direction'] = 'in'
	mpl.rcParams['xtick.top'] = True
	mpl.rcParams['ytick.right'] = True

import controls, buttons, Menu, trend, logger, message, TaskList, filter
import TSI, APT, CAI, Sartorius, Magee, Alicat, PPSystems, AWS
import playback


Simulation = False
SkipTemperatures = False or Simulation

if not Simulation:
	import cbw
	from NI import DAQmx

NCOLS = 600

ID_LOGGING_START	= wx.NewId()
ID_LOGGING_STOP		= wx.NewId()

ID_MESSAGE_FILTER_START	= wx.NewId()
ID_MESSAGE_FILTER_STOP = wx.NewId()
ID_MESSAGE_TEST_START = wx.NewId()
ID_MESSAGE_TEST_STOP = wx.NewId()
ID_MESSAGE_AWS_SCALE = wx.NewId()
ID_MESSAGE_SARTORIUS_SCALE = wx.NewId()
ID_MESSAGE_USER = wx.NewId()


class UI(wx.Window):
	def __init__(self, parent):
		wx.Window.__init__(self, parent)
		self.SetBackgroundColour(wx.Colour(192,192,192))

		self.spacer = u"\u200A"	# Unicode hairspace

		toolbar = self.CreatePseudoToolbar(parent)
		self.CreateTrends()
		self.CreateConcentrationPlots()

		#StatusIndicatorsPanel
		#TODO: Ask Vi: wx.HORIZONTAL or wx.VERTICAL here
		indicatorsLayout = wx.VERTICAL
		self.CreateStatusIndicatorsPanel(indicatorsLayout)
		self.CreateTemperaturesPanel()
		valuesPanel = self.CreateValuesPanel()

		topLevel = wx.BoxSizer(wx.VERTICAL)
		topLevel.Add(toolbar, 0, wx.EXPAND)
		topLevel.Add(wx.StaticLine(self, wx.LI_HORIZONTAL), 0, wx.EXPAND)

		hSizer = wx.BoxSizer(wx.HORIZONTAL)

		# Left side of screen: dNdLogD plot and values panel
		vSizer1 = wx.BoxSizer(wx.VERTICAL)
		vSizer1.Add(self.concentrationCanvas, 2, wx.EXPAND)
		vSizer1.Add(valuesPanel, 0, wx.EXPAND|wx.LEFT, 40)
		hSizer.Add(vSizer1, 0, wx.EXPAND)

		# Center part of screen: Contour Scale, Contour and trends
		vSizer2 = wx.BoxSizer(wx.VERTICAL)
		vSizer2.AddSpacer(5)
		if indicatorsLayout == wx.HORIZONTAL:
			vSizer2.Add(self.StatusIndicatorsPanel, 0, wx.LEFT, 70)		# ~Align under trend box
			vSizer2.AddSpacer(5)
		#These scale factors correspond approximately to pixels vertically
		vSizer2.Add(self.contourScaleCanvas, 65, wx.EXPAND|wx.BOTTOM, 10)
		vSizer2.Add(self.contourCanvas, 200, wx.EXPAND|wx.BOTTOM, 20)
		vSizer2.Add(self.trend1, 200, wx.EXPAND)
		vSizer2.Add(self.trend2, 200, wx.EXPAND)
		vSizer2.Add(self.trend3, 200, wx.EXPAND | wx.BOTTOM, 5)
		#vSizer2.Add(self.infoBar, 0, wx.TOP|wx.BOTTOM|wx.EXPAND, 10)
		hSizer.Add(vSizer2, 1, wx.EXPAND)

		#Right part of screen: Indicators panel
		if indicatorsLayout == wx.VERTICAL:
			if 0:
				hSizer.Add(self.StatusIndicatorsPanel)
			else:
				xSizer = wx.BoxSizer(wx.VERTICAL)
				xSizer.Add(self.StatusIndicatorsPanel)
				xSizer.AddStretchSpacer(1)
				xSizer.Add(self.TemperaturesPanel, 0)
				hSizer.Add(xSizer, 0, wx.EXPAND)
				xSizer.AddSpacer(50)

		topLevel.Add(hSizer, 1, wx.EXPAND)

		self.SetSizer(topLevel)

		self.contourCanvas.Bind(wx.EVT_RIGHT_DOWN, parent.OnSetupPlotOptions)
		self.contourScaleCanvas.Bind(wx.EVT_RIGHT_DOWN, parent.OnSetupPlotOptions)
		self.concentrationCanvas.Bind(wx.EVT_RIGHT_DOWN, parent.OnSetupPlotOptions)
		self.trend1.Bind(wx.EVT_RIGHT_DOWN, parent.OnSetupPlotOptions)
		self.trend2.Bind(wx.EVT_RIGHT_DOWN, parent.OnSetupPlotOptions)
		self.trend3.Bind(wx.EVT_RIGHT_DOWN, parent.OnSetupPlotOptions)

#		self.add_mpl_toolbar()

	def CreatePseudoToolbar(self, parent):
		#Pseudo toolbar w/o any toolbar icons
		#Note how this uses all the bind's to the parent object.
		tb = wx.Window(self, -1)
		sizer = wx.BoxSizer(wx.HORIZONTAL)
		self.buttonList = []
		button = buttons.ToggleButton(tb, -1, 'Test')
		if wx.VERSION < (4,0):
			button.SetToolTipString("Start/Stop Test")
		else:
			button.SetToolTip("Start/Stop Test")
		button.SetOffColour(wx.RED, 15)
		button._onColour = button.DarkColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE), 15)
		button._onColours = wx.WHITE, button._onColour
		self.buttonList.append(button)
		sizer.AddSpacer(5)
		sizer.Add(button, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 10)
		self.Bind(wx.EVT_TOGGLEBUTTON, parent.OnTestButton, button)

#		button = buttons.Button(tb, -1, "Test Parameters", size=(102,26))
#		button.SetToolTipString("Enter Test Parameters")
#		self.buttonList.append(button)
#		sizer.Add(button, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 10)
#		self.Bind(wx.EVT_BUTTON, parent.OnRunTestParameters, button)

		msgButtons = [
			("Filter Start", 	parent.OnMessageFilterStart),
			("Filter Stop",		parent.OnMessageFilterStop),
			("AWS Scale",		parent.OnMessageAWSScale),
			("Sartorius Scale",	parent.OnMessageSartoriusScale),
			("User Message",	parent.OnMessageUser),
		]
		for label, callback in msgButtons:
			button = buttons.Button(tb, -1, label)
			if wx.VERSION < (4,0):
				button.SetToolTipString('Log Message "%s"' % label)
			else:
				button.SetToolTip('Log Message "%s"' % label)
			self.buttonList.append(button)
			sizer.Add(button, 0, wx.ALIGN_CENTER_VERTICAL)
			self.Bind(wx.EVT_BUTTON, callback, button)

		font = wx.Font(10, wx.FONTFAMILY_DEFAULT,
					wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False,  "Segoe UI")

		self.StopWatch = controls.StopWatchButton(tb, -1, "", useExternalTimer=True)
		if wx.VERSION < (4,0):
			self.StopWatch.SetToolTipString("Stop Watch")
		else:
			self.StopWatch.SetToolTip("Stop Watch")
		self.StopWatch.SetFont(font)
		self.StopWatch.SetPeriod(parent.StopWatchPeriod)
		sizer.Add(self.StopWatch, 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 250)

		self.TestTime = wx.StaticText(tb, -1, "", size=(100, -1), style=wx.ALIGN_CENTER_HORIZONTAL)
		if wx.VERSION < (4,0):
			self.TestTime.SetToolTipString("Test Time")
		else:
			self.TestTime.SetToolTip("Test Time")
		self.TestTime.SetLabel("0.00")
		self.TestTime.SetBackgroundColour(tb.GetBackgroundColour())
		self.TestTime.SetFont(font)
		sizer.Add(self.TestTime, 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 20)

		tb.SetSizer(sizer)
		return tb

	def CreateConcentrationPlots(self):
		# This is the instantaneous concentration plot
		#TODO: This one probably needs a minimum width 
		self.concentrationFigure = mpl.figure.Figure()

		# This is the contour plot scale
		self.contourScaleFigure = mpl.figure.Figure()

		# This is the contour concentraton trend plot
		self.contourFigure = mpl.figure.Figure()


		# Defaults are in
		# C:/Users/.../.matplotlib/matplotlibrc
		#   or
		# C:/Program Files (x86)/Python27/Lib/site-packages/matplotlib/mpl-data/matplotlibrc
		# Virgin rc file has
		# left=0.125, right=0.9, wspace=0.2, bottom=0.1, right=0.9, hspace=0.2
		self.concentrationFigure.subplots_adjust(left=0.12, right=0.98, bottom=0.12, top=0.95)
		#These are now set in the OnContourSize method
		#self.contourFigure.subplots_adjust(left=0.05, right=0.985, bottom=0.12, top=0.95)
		#self.contourFigure.subplots_adjust(left=0.05, right=0.985, bottom=0.05, top=0.95)
		#self.contourScaleFigure.subplots_adjust(left=0.05, right=0.985, bottom=0.01, top=0.38)

		self.concentrationCanvas = FigureCanvas(self, -1, self.concentrationFigure)
		self.contourCanvas = FigureCanvas(self, -1, self.contourFigure)
		self.contourScaleCanvas = FigureCanvas(self, -1, self.contourScaleFigure)

		# This is only necessary for real matplotlib, where the defaults are larger
		self.concentrationCanvas.SetMinSize((300,300))
		self.contourCanvas.SetMinSize((300,100))
		self.contourScaleCanvas.SetMinSize((300,50))

	def CreateValuesPanel(self):
		panel = wx.Window(self)#, size=(475,-1))
		panel.SetBackgroundColour(self.GetBackgroundColour())

		font = wx.Font(30, wx.FONTFAMILY_DEFAULT,
						wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False,  "Arial")
#						wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False,  "Segoe UI")
		panel.SetFont(font)

		size1 = (180, -1)
		size2 = (140, -1)
		ws = self.spacer
		self.WallTime = wx.StaticText(panel, size=size1, style=wx.TE_RIGHT)
		self.TPot = controls.StaticFloat(panel, size=size2, format="%.1f"+ws)
		self.SartoriusMass = controls.StaticFloat(panel, size=size2, format="%.1f"+ws)
		self.AWSMass = controls.StaticFloat(panel, size=size2, format='%.1f'+ws)
		self.DuctCO2 = controls.StaticFloat(panel, size=size2, format="%.0f"+ws)
		self.DilutionRatio = controls.StaticFloat(panel, size=size2, format="%.1f"+ws)
		self.AlicatFlow = controls.StaticFloat(panel, size=size2, format="%.1f"+ws)
		self.FilteredIrisFlow = controls.StaticFloat(panel, size=size2, format="%.1f"+ws)
		self.OutInDP = controls.StaticFloat(panel, size=size2, format="%.1f"+ws)
		self.Atten370 = controls.StaticFloat(panel, size=size2, format='%.1f'+ws)

		sizer = wx.GridBagSizer(vgap=5, hgap=5)
		items = [("Time", 			self.WallTime, 			None),
				 ("Pot Temp",		self.TPot,				"C"),
				 ("Sartorius",		self.SartoriusMass,		"g"),
				 ("AWS",			self.AWSMass,			"g"),
				 ("Duct CO2",		self.DuctCO2,			"ppm"),
				 ("30s DR",			self.DilutionRatio,		""),
				 ("Alicat Flow",	self.AlicatFlow,		"l/m"),
				 ('Iris Flow',		self.FilteredIrisFlow,	"CFM"),
				 (u"Out-In \u0394P",self.OutInDP,			"Pa"),
				 ("Aeth. Atten.",	self.Atten370,			"")
				]
		for row, (label, value, units) in enumerate(items):
			labelWidget = wx.StaticText(panel, -1, label)
			if label == "30s DR":
				self.DilutionRatioLabel = labelWidget
			if units is None:
				sizer.Add(labelWidget, (row,0), (1,1))
				sizer.Add(value, (row,1), (1,2), wx.ALIGN_RIGHT)
			else:
				units  = wx.StaticText(panel, -1, units)
				sizer.Add(labelWidget, (row,0), (1,2))
				sizer.Add(value, (row,2), (1,1))
				sizer.Add(units, (row,3), (1,1), wx.LEFT, 5)

		panel.SetSizer(sizer)

		cfg = wx.Config.Get()
		self.SartoriusMass.SetAlarmLimits(0, None)
		self.AWSMass.SetAlarmLimits(0, None)
#		self.TPot.SetAlarmLimits(-100,0)
		self.Atten370.SetAlarmLimits(0, cfg.ReadFloat("Alarm Limits/Maximum Aethalometer Attenuation"))
		self.FilteredIrisFlow.SetAlarmLimits(cfg.ReadFloat("Alarm Limits/Minimum Iris Flow"), None)
		self.DilutionRatio.SetAlarmLimits(cfg.ReadFloat("Alarm Limits/Minimum Dilution Ratio"),
										  cfg.ReadFloat("Alarm Limits/Maximum Dilution Ratio"))

		return panel

	def CreateStatusIndicatorsPanel(self, layout):
		panel = wx.Panel(self, -1)
		panel.SetBackgroundColour(self.GetBackgroundColour())

		self.Indicators = {}
		labels = ["FMPS3091", "APS3321", "OPS3330", "DustTrax", "Aethalometer", "CAI-602P"]
		if layout in [wx.HORIZONTAL, wx.CENTER]:
			sizer = wx.GridSizer(cols=len(labels))
		else:
			sizer = wx.BoxSizer(wx.VERTICAL)
			w1 = wx.StaticText(panel, -1, "Instrument")
			w2 = wx.StaticText(panel, -1, "Status")
			font = wx.Font(12, wx.FONTFAMILY_DEFAULT,
						wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False,
						"Arial Narrow")
			w1.SetFont(font)
			w2.SetFont(font)
			sizer.Add(w1, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.TOP, 325)
			sizer.Add(w2, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, 20)
		for label in labels:
			w = controls.RoundedIndicator(panel, -1, label, size=(-1,-1))
			self.Indicators[label] = w
			sizer.Add(w, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 10)
			if layout != wx.HORIZONTAL:
				sizer.AddSpacer(20)
		panel.SetSizer(sizer)
		self.StatusIndicatorsPanel = panel

	def CreateTemperaturesPanel(self):
#		labels = ["Flue 1", "Flue 2", "Manifold Air", "Inlet Air"]
		labels = ["Flue 1", "Flue 2", "Man. Air", "In. Air"]
		self.Temperatures = []
		panel = wx.Panel(self)
		bSizer = wx.BoxSizer(wx.VERTICAL)
		gSizer = wx.FlexGridSizer(cols=2)
		w1 = wx.StaticText(panel, -1, "Stove Temps.")
		font = wx.Font(21, wx.FONTFAMILY_DEFAULT,
						wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False,  "Arial Narrow")
		panel.SetFont(font)
		w1.SetFont(font)
		bSizer.Add(w1, 0, wx.ALIGN_CENTER_HORIZONTAL|wx.BOTTOM, 10)
		for i, label in enumerate(labels):
			w1 = wx.StaticText(panel, -1, label)
			#w1.SetBackgroundColour(wx.YELLOW)
			gSizer.Add(w1, 0, wx.EXPAND, 0)
			style = wx.TE_RIGHT
			w2 = controls.StaticFloat(panel, -1, 0.0, size=(70,-1), format='%.0f')
			w2.SetAlarmLimits(None, 2000)
			#w2.SetBackgroundColour(wx.BLUE)
			self.Temperatures.append(w2)
			gSizer.Add(w2, 0, wx.EXPAND|wx.RIGHT, 4)
		bSizer.Add(gSizer, 0, wx.EXPAND)
		panel.SetSizer(bSizer)
		self.TemperaturesPanel = panel		
		self.FlueTemp1, self.FlueTemp2, self.ManifoldAirTemp, self.InletAirTemp = self.Temperatures

	def CreateTrends(self):
		self.trend1 = trend.Trend(self, nLines=2, hideXInfo=1)
		self.trend1.SetWidth(NCOLS, 10, 6)
		self.trend1.SetLabels(["PM 2.5", "BC (880 nm)"])
		self.trend1.legendFormat[0] = "%.3f"

		self.trend2 = trend.Trend(self, nLines=4, hideXInfo=1)
		self.trend2.SetWidth(NCOLS, 10, 6)
		self.trend2.SetLabels(["CAI CO2", "CAI CO", "Dil. CO2", "Amb. CO2"])
		#self.trend2.legendFormat[0] = "%.3f"

		self.trend3 = trend.Trend(self, nLines=4)
		self.trend3.SetWidth(NCOLS, 10, 6)
		self.trend3.SetLabels(["T Pot", "T Amb", "T Duct", "RH"])
#		self.trend3.SetLabels(["Hood", "PreIris", "PostIris", "Outside"])
		self.trend3.pens = [
				wx.Pen(wx.BLUE,				3, wx.SOLID),
				wx.Pen(wx.GREEN,			0, wx.SOLID),
				wx.Pen(wx.Colour(255,75,75),0, wx.SOLID),
				wx.Pen(wx.CYAN,				0, wx.SOLID),
		]

#	def CreateInfoBar(self)
#		self.infoBar = wx.lib.agw.infobar.InfoBar(self)
#		self.infoBar.SetBackgroundColour(wx.RED)
#		self.infoBar._text.SetBackgroundColour(wx.RED)
#		No easy way to add a tool tip to a custom button
#		self.infoBar.AddButton(-1, "Hide")
#		#self.infoBar.SetShowHideEffects(wx.SHOW_EFFECT_SLIDE_TO_BOTTOM, wx.SHOW_EFFECT_SLIDE_TO_TOP)
#		#self.infoBar.SetEffectDuration(100)
#		#self.infoBar.Bind(wx.EVT_BUTTON, parent.OnHideInfoBar)

	def Update(self, **kwargs):
		for key, value in kwargs.items():
			getattr(self, key).SetValue(value)

	def UpdateWallTime(self, testRunning):
		#Note: Python 2.7 seems to require all ASCII characters for strftime argument
		self.WallTime.SetLabel(time.strftime("%H:%M:%S") + self.spacer)
		self.WallTime.SetBackgroundColour(self.GetBackgroundColour() if testRunning else wx.RED)


class CookStovesFrame(wx.Frame):
	def __init__(self):
		if wx.Display.GetCount() != 2:
			clientArea = wx.Display(0).GetClientArea()
			offset = 200
			pos = (offset,0)
			size = (clientArea[2]-offset, clientArea[3])
		else:
			display = wx.Display(1 - wx.Display.GetFromPoint((0,0)))
			pos  = display.GetClientArea()[0:2]
			size = display.GetClientArea()[2:4]
			if size[0] >  1900: size = (size[0]-200, size[1])
			#size = (2560, 1440)
			#size = (16*size[1]/9, size[1])
			if size[1] < 1000:
				clientArea = wx.Display(0).GetClientArea()
				pos = (0,0)
				size = (clientArea[2], clientArea[3])

		#disable = wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX | wx.CLOSE_BOX | wx.SYSTEM_MENU | wx.RESIZE_BORDER
		disable = 0
		wx.Frame.__init__(self, None, -1, 'DOE Cook Stoves', pos=pos, size=size,
						style=wx.DEFAULT_FRAME_STYLE & ~disable)

		cfg = wx.FileConfig("CookStoves", "LBNL Applications",
				localFilename="../CookStove.ini",
				style=wx.CONFIG_USE_LOCAL_FILE|wx.CONFIG_USE_NO_ESCAPE_CHARACTERS|wx.CONFIG_USE_RELATIVE_PATH)
		#Turning this on conflicts with the simply commenting out lines in the
		#hardware section to disable devices.  Should it be True some of the time
		#and False at other times?
		#cfg.SetRecordDefaults(True)
		wx.Config.Set(cfg)

		self.LoadConfig()

		fileName = wx.Config.Get().Read("Playback/File", "")
		if fileName == "":
			self.Playback = None
		else:
			try:
				self.Playback = playback.Playback(fileName)
			except BaseException as e:
				print(e)
				self.Playback = None

		self.ActiveDilutionRatio = 30

		self.CreateMenu()
		#self.CreateToolBar()
		#self.CreateStatusBar()

		#Need this for the case where there is no menu
		aTable = wx.AcceleratorTable([
					(wx.ACCEL_NORMAL,  wx.WXK_F10, wx.ID_EXIT),
				])
		self.SetAcceleratorTable(aTable)

		self.ui = UI(self)
		self.ui.contourScaleCanvas.Show(self.ViewContourScale)
		self.ui.StatusIndicatorsPanel.Show(self.ViewStatusIndicators)

		self.ui.contourCanvas.Bind(wx.EVT_SIZE, self.OnContourSize)
		self.ui.contourScaleCanvas.Bind(wx.EVT_SIZE, self.OnContourScaleSize)

		#ico = wx.Icon('1414804198_86715.ico', wx.BITMAP_TYPE_ICO)
		ico = wx.Icon('1414804562_131936.ico', wx.BITMAP_TYPE_ICO)
		self.SetIcon(ico)

	def Initialize(self):
		self.stopTasks = TaskList.TaskList()
		self.waitTasks = TaskList.TaskList()

		self.SetTrendLimits()

		self.isLogging = False
		self.SetupInstruments()
		self.SetupLogging()
		self.OnLoggingStart(None)

		self.Bind(wx.EVT_CLOSE, self.OnClose)

		self.TestRunning = False
		self.TestStartTime = None

		self.UserName = ""
		self.StoveType = ""
		self.ColdStartFilterID = ""
		self.HotStartFilterID = ""
		self.SimmerFilterID = ""

		self.SetupContourValues()
		self.SetupFigures()
		self.UpdateUI()

		self.timer = wx.Timer(self, -1)
		self.Bind(wx.EVT_TIMER, self.OnTimer)
		self.Bind(wx.EVT_TIMER, self.ui.StopWatch.OnTimer)

		self.APT.SetStatusFlag('zero')
		self.DilutedSBA5.SetStatusFlag('zero')
		self.AmbientSBA5.SetStatusFlag('zero')
		self.DustTraxZeroRequested = False
		self.FMPS3091PumpOn = False

		self.StartInstruments()

	def CreateMenu(self):
		menuBar = Menu.MenuBar(
			Menu.Menu("&File",
#				Menu.NormalItem(wx.ID_NEW,
#					"&New\tCtrl+N", "Create a new file",
#					None, None),
#				Menu.NormalItem(wx.ID_OPEN,
#					"&Open\tCtrl+O", "Open an existing file",
#					None, None),
#				Menu.NormalItem(wx.ID_CLOSE,
#					"&Close", "Close document",
#					None, None),
#				Menu.NormalItem(wx.ID_SAVE,
#					"&Save\tCtrl+S", "Save document",
#					None, None),
#				Menu.NormalItem(wx.ID_SAVEAS,
#					"&Save As", "Save document with new name",
#					None, None),
#				Menu.Separator(),
				Menu.NormalItem(wx.ID_EXIT,	"E&xit\tF10", "Exit Program",
					self.OnFileExit, None),
			),

#			Menu.Menu("&Run",
#				Menu.NormalItem(ID_LOGGING_START,"&Start Logging", "Start Logging",
#					self.OnLoggingStart, self.OnUpdateUILoggingStart),
#				Menu.NormalItem(ID_LOGGING_STOP,"Sto&p Logging", "Stop Logging",
#					self.OnLoggingStop, self.OnUpdateUILoggingStop),
#			),

			Menu.Menu("&View",
#				Menu.NormalItem(wx.NewId(), "&Info Bar\tF1", "Display Info Bar",
#					self.OnShowInfoBar, None),
				Menu.NormalItem(wx.NewId(), "APT Values ...", "APT Values",
					self.OnViewAPTValues, None),
				Menu.NormalItem(wx.NewId(), "Flow Rates ...\tCtrl-F", "Flow Rates",
					self.OnViewFlowRates, None),
				Menu.NormalItem(wx.NewId(), "Diluted SBA5 Values ...", "Diluted SBA5 Values",
					self.OnViewDilutedSBA5Values, None),
				Menu.NormalItem(wx.NewId(), "Ambient SBA5 Values ...", "Ambient SBA5 Values",
					self.OnViewAmbientSBA5Values, None),
				Menu.NormalItem(wx.NewId(), "Aethalometer Values ...", "Aethalometer Values",
					self.OnViewAethalometerValues, None),
				Menu.NormalItem(wx.NewId(), "Alicat Values ...", "Alicat Values",
					self.OnViewAlicatValues, None),
				Menu.Separator(),
				Menu.CheckedItem(wx.NewId(), "Contour Scale", "Toggle Contour Scale on/off",
					self.OnViewContourScale, self.OnUpdateUIViewContourScale),
				Menu.CheckedItem(wx.NewId(), "Status Indicators", "Toggle Status Indicators on/off",
					self.OnViewStatusIndicators, self.OnUpdateUIViewStatusIndicators),
				Menu.Separator(),
				Menu.CheckedItem(wx.NewId(), "1 sec DilutionRatio", "1 second Dilution Ratio",
					self.OnViewDilutionRatio01, self.OnUpdateUIViewDilutionRatio01),
				Menu.CheckedItem(wx.NewId(), "15 sec DilutionRatio", "15 second Dilution Ratio",
					self.OnViewDilutionRatio15, self.OnUpdateUIViewDilutionRatio15),
				Menu.CheckedItem(wx.NewId(), "30 sec DilutionRatio", "30 second Dilution Ratio",
					self.OnViewDilutionRatio30, self.OnUpdateUIViewDilutionRatio30),
			),

			Menu.Menu("&Setup",
				Menu.NormalItem(wx.NewId(), "&Plot Options ...", "Setup Plot Options",
					self.OnSetupPlotOptions, None),
			),

			# These need ID_MESSAGE values only if we ever restore the
			# standard toolbar, which needs to share widget id's with the
			# menu item.  Otherwise, I could use -1 here.
			Menu.Menu("&Messages",
				Menu.NormalItem(ID_MESSAGE_FILTER_START, "Filter Start", "Record Filter Start Event",
					self.OnMessageFilterStart, self.OnUpdateUILogMessage),
				Menu.NormalItem(ID_MESSAGE_FILTER_STOP, "Filter Stop", "Record Filter Stop Event",
					self.OnMessageFilterStop, self.OnUpdateUILogMessage),
				Menu.NormalItem(ID_MESSAGE_AWS_SCALE, "AWS Scale", "AWS Scale Measurement Event",
					self.OnMessageAWSScale, self.OnUpdateUILogMessage),
				Menu.NormalItem(ID_MESSAGE_SARTORIUS_SCALE, "Sartorius Scale", "Sartorius Scale Measurement Event",
					self.OnMessageSartoriusScale, self.OnUpdateUILogMessage),
				Menu.NormalItem(ID_MESSAGE_USER, "User Specified ...", "User Specified Event",
					self.OnMessageUser,	self.OnUpdateUILogMessage),
			),
			Menu.Menu("&Operate",
				Menu.NormalItem(-1, "Test &Parameters  ...", "Set/Change Test Parameters",
					self.OnRunTestParameters, None),
				Menu.Separator(),
				Menu.NormalItem(-1, "&Tare Sartorius  ...", "Tare Sartorius",
					self.OnOperateTareSartorius, self.OnUpdateUIOperateTareSartorius),
				Menu.Separator(),
				Menu.NormalItem(-1, "&FMPS Zero Electrometers ...", "FMPS Zero Electrometers",
					self.OnOperateFMPS3091Zero, self.OnUpdateUIOperateFMPS3091Zero),
				Menu.NormalItem(-1, "&DustTrax Zero", "DustTrax Zero",
					self.OnOperateDustTraxZero, self.OnUpdateUIOperateDustTraxZero),
				Menu.Separator(),
				Menu.CheckedItem(-1, "FMPS &Pump", "Toggle Pump On/Off",
					self.OnOperateFMPSPumpOn, self.OnUpdateUIOperateFMPSPumpOn),
				Menu.Separator(),
				Menu.NormalItem(-1, "&APT Zero", "APT Zero",
					self.OnOperateAPTZero, self.OnUpdateUIOperateAPTZero),
				Menu.NormalItem(-1, "Diluted &SBA5 Zero", "Diluted SBA5 Zero",
					self.OnOperateDilutedSBA5Zero, self.OnUpdateUIOperateDilutedSBA5Zero),
				Menu.NormalItem(-1, "Ambient &SBA5 Zero", "Ambient SBA5 Zero",
					self.OnOperateAmbientSBA5Zero, self.OnUpdateUIOperateAmbientSBA5Zero),
			),
			Menu.Menu("&Help",
				Menu.NormalItem(wx.ID_ABOUT, "About ...", "About",
					self.OnHelpAbout, None),
				Menu.Separator(),
				Menu.NormalItem(-1, "Widget Inspection Tool", "Widget Inspection Tool",
					self.OnHelpInspection, None)
			),
		)
		self.SetMenuBar(menuBar.Create(self))
		#TODO: Disable menu bar
		#self.SetMenuBar(None)

	"""
	def CreateToolBar (self):
		tb = wx.ToolBar(self, style=wx.TB_FLAT)

		bg = tb.GetBackgroundColour()
		tSize = (24,24)
#
#		tb.AddLabelTool(wx.ID_NEW, "New",
#			wx.ArtProvider.GetBitmap(wx.ART_NEW, wx.ART_TOOLBAR, tSize),
#			shortHelp="New", longHelp="Create a new document")
#		tb.AddLabelTool(wx.ID_OPEN, "Open",
#			wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR, tSize),
#			shortHelp="Open", longHelp="Open an existing document")
#		tb.AddLabelTool(wx.ID_SAVE, "Save",
#			wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE, wx.ART_TOOLBAR, tSize),
#			shortHelp="Save", longHelp="Save the document")
#		tb.AddLabelTool(wx.ID_SAVEAS, "Save As",
#			wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE_AS, wx.ART_TOOLBAR, tSize),
#			shortHelp="Save As", longHelp="Save the document with a new name")

#		tb.AddSeparator()

#		tb.AddLabelTool(wx.ID_UNDO, "Undo",
#			wx.ArtProvider.GetBitmap(wx.ART_UNDO, wx.ART_TOOLBAR, tSize),
#			shortHelp="Undo", longHelp="Undo the last action")
#		tb.AddLabelTool(wx.ID_REDO, "REDO",
#			wx.ArtProvider.GetBitmap(wx.ART_REDO, wx.ART_TOOLBAR, tSize),
#			shortHelp="Redo", longHelp="Redo the previously undone action")
#
#		tb.AddSeparator()
#
#		tb.AddLabelTool(wx.ID_CUT, "Cut",
#			wx.ArtProvider.GetBitmap(wx.ART_CUT, wx.ART_TOOLBAR, tSize),
#			shortHelp="Cut", longHelp="Cut the selection and put it on the Clipboard")
#		tb.AddLabelTool(wx.ID_COPY, "Copy",
#			wx.ArtProvider.GetBitmap(wx.ART_COPY, wx.ART_TOOLBAR, tSize),
#			shortHelp="Copy", longHelp="Copy the selection and put it on the Clipboard")
#		tb.AddLabelTool(wx.ID_PASTE, "Paste",
#			wx.ArtProvider.GetBitmap(wx.ART_PASTE, wx.ART_TOOLBAR, tSize),
#			shortHelp="Paste", longHelp="Insert Clipboard contents")
#		tb.AddLabelTool(wx.ID_DELETE, "Delete",
#			wx.ArtProvider.GetBitmap(wx.ART_DELETE, wx.ART_TOOLBAR, tSize),
#			shortHelp="Delete", longHelp="Erase the selection")
#
#		tb.AddSeparator()

		id = wx.NewId()
		tb.AddLabelTool(id, "Info",
			wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, wx.ART_TOOLBAR, tSize),
			shortHelp="Dummy Icon", longHelp="Dummy Icon")
		tb.EnableTool(id, False)

#		id = wx.NewId()
#		tb.AddLabelTool(id, "Home",
#			wx.ArtProvider.GetBitmap(wx.ART_GO_HOME, wx.ART_TOOLBAR, tSize),
#			shortHelp="Go Home", longHelp="Long Go Home")
#		tb.EnableTool(id, False)

#		tb.AddLabelTool(ID_LOGGING_START, "Start",
#			self.loadIcon("go", tSize),
#			shortHelp="Start Logging", longHelp="Start Logging")
#		tb.AddLabelTool(ID_LOGGING_STOP, "Stop",
#			self.loadIcon("stop", tSize),
#			shortHelp="Stop Logging", longHelp="Stop Logging")

#		tb.AddSeparator()

		#Using same ID's as on the menu means these are enabled and disabled automatically.
		button = buttons.ToggleButton(tb, -1, 'Test')
		button.SetToolTipString("Start/Stop Test")
		button.SetOffColour(wx.RED, 15)
		button._onColour = button.DarkColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE), 15)
		button._onColours = wx.WHITE, button._onColour
		tb.AddControl(button)
		tb.AddControl(wx.Control(tb, -1, size=(3,-1),style=wx.NO_BORDER))
		tb.AddSeparator()
		self.Bind(wx.EVT_TOGGLEBUTTON, self.OnTestButton, button)

		button = buttons.Button(tb, -1, "Test Parameters", size=(102,26))
		button.SetToolTipString("Enter Test Parameters")
		tb.AddControl(button)
		self.Bind(wx.EVT_BUTTON, self.OnRunTestParameters, button)
		tb.AddControl(wx.Control(tb, -1, size=(3,-1),style=wx.NO_BORDER))
		tb.AddSeparator()

		msgButtons = [
			(ID_MESSAGE_FILTER_START, "Filter Start"),
			(ID_MESSAGE_FILTER_STOP, "Filter Stop"),
			(ID_MESSAGE_AWS_SCALE, "AWS Scale"),
			(ID_MESSAGE_SARTORIUS_SCALE, "Sartorius Scale"),
			(ID_MESSAGE_USER, "User")
		]

		for id, label in msgButtons:
			button = buttons.Button(tb, id, label)
			button.SetToolTipString('Log User Message "%s"' % label)
			msg = None if id == ID_MESSAGE_USER else label
			#Funny Python lambda hack
			self.Bind(wx.EVT_BUTTON, lambda evt,msg=msg: self.LogMessage("User", msg), button)
			tb.AddControl(button)

		tb.Realize()
		self.SetToolBar(tb)
		"""

	def loadIcon(self, fileName, tSize):
		dir = "icons/"
		kind, flag = 'png', wx.BITMAP_TYPE_PNG
		return wx.Bitmap(dir + fileName + "." + kind, flag)

	def CreateStatusBar(self):
		self.statusBar = wx.StatusBar(self)
		self.statusBar.SetFieldsCount(3)
		self.statusBar.SetStatusWidths([-1, 100, 200])
		self.SetStatusBar(self.statusBar)

	def LoadConfig(self):
		cfg = wx.Config.Get()
		self.dNdLogDMin = cfg.ReadFloat("Plot/Minimum dNdLogDp", 1e0)
		self.dNdLogDMax = cfg.ReadFloat("Plot/Maximum dNdLogDp", 1e7)
		self.CO2Max     = cfg.ReadFloat("Plot/Maximum CAI CO2", 5000)
		self.COMax     = cfg.ReadFloat("Plot/Maximum CAI CO", 750)
		self.PM25Max    = cfg.ReadFloat("Plot/Maximum PM2.5", 10)
		self.BC880Max   = cfg.ReadFloat("Plot/Maximum BC880", 3000)
		self.LinearDist = cfg.ReadInt("Plot/Linear Scale for Size Distribution", 0)
		self.LinearContour = cfg.ReadInt("Plot/Linear Scale for Contour Plot", 0)
		self.ShowContourDividers = cfg.ReadInt("Plot/Show Contour Dividers", 0)

		self.StopWatchPeriod = cfg.ReadInt("Stop Watch/Period", 5*60)

		self.ViewContourScale = cfg.ReadInt("View/Show Contour Scale", 1)
		self.ViewStatusIndicators = cfg.ReadInt("View/Show Status Indicators", 1)

	def SaveConfig(self):
		cfg = wx.Config.Get()
		cfg.WriteFloat("Plot/Minimum dNdLogDp", self.dNdLogDMin)
		cfg.WriteFloat("Plot/Maximum dNdLogDp", self.dNdLogDMax)
		cfg.WriteFloat("Plot/Maximum CAI CO2", self.CO2Max)
		cfg.WriteFloat("Plot/Maximum PM2.5", self.PM25Max)
		cfg.WriteFloat("Plot/Maximum BC880", self.BC880Max)
		cfg.WriteFloat("Plot/Maximum CAI CO", self.COMax)
		cfg.WriteInt("Plot/Linear Scale for Size Distribution", self.LinearDist)
		cfg.WriteInt("Plot/Linear Scale for Contour Plot", self.LinearContour)
		cfg.WriteInt("Plot/Show Contour Dividers", self.ShowContourDividers)

		cfg.WriteInt("Stop Watch/Period", self.ui.StopWatch.GetPeriod())

		cfg.WriteInt("View/Show Contour Scale", self.ViewContourScale)
		cfg.WriteInt("View/Show Status Indicators", self.ViewStatusIndicators)

	def SetupLogging(self):
		self.logger = logger.Logger()
		self.message = message.MessageLogger()

		# Create a short nick name to shorten these lines
		add = self.logger.AddItem

#		add("Date",					"",		"%s",	lambda : time.strftime("%m/%d/%y")	)
		add("Time",					"",		"%s",	lambda : time.strftime("%H:%M:%S")	)

		add("Stove",				"",		"%s",   lambda : self.StoveType 		)

		# MCC USB-TC-AI
		add("T Pot",				"C",	"%g",	lambda : self.TPot				)
		add("T Amb",				"C",	"%g",	lambda : self.TAmb				)
		add("T Duct",				"C",	"%g",	lambda : self.TDuct				)

		# APT
		add("P Hood",				"Pa",	"%g",	lambda : self.PHood				)
#		add("P DuctPreSample",		"Pa",	"%g",	lambda : self.PDuctPreSample	)
		add("P Unused",				"Pa",	"%g",	lambda : self.PDuctPreSample	)
		add("P DuctPostSample",		"Pa",	"%g",	lambda : self.PDuctPostSample	)
		add("P PreIris",			"Pa",	"%g",	lambda : self.PDuctPreIris		)
		add("P PostIris",			"Pa",	"%g",	lambda : self.PDuctPostIris		)
		add("P Chimney",			"Pa",	"%g",	lambda : self.PChimney			)
		add("P Outside",			"Pa",	"%g",	lambda : self.POutside			)
		add("RH",					"%",	"%g",	lambda : self.Humidity			)

		#Iris
		add("Duct Flow",			"CFM",	"%g",	lambda : self.IrisFlow			)

		#CAI
		add("Duct CO2",				"ppm",	"%g",	lambda : self.DuctCO2			)
		add("Duct CO",				"ppm",	"%g",	lambda : self.DuctCO			)
		add("Duct O2",				"%",	"%g",	lambda : self.DuctO2			)

		#SBA5
		add("SBA5 CO2",				"ppm",	"%g",	lambda : self.DilutedCO2		)

		#SBA5
		add("Ambient CO2",			"ppm",	"%g",	lambda : self.AmbientCO2		)

		# Sartorius Scale
		add("Sartorius",			"g",	"%g",	lambda : self.SartoriusMass		)

		# AWS Scale
		add("AWS",					"g",	"%g",	lambda  : self.AWSMass			)

		# Alicat
		add("Alicat",				"lpm",	"%g",	lambda  : self.AlicatFlow		)
		add("Alicat Std",			"slpm",	"%g",	lambda  : self.AlicatStdFlow	)
		add("Alicat Setpoint",		"lpm",	"%g",	lambda  : self.AlicatSetpoint	)
		add("Alicat P",				"psia",	"%g",	lambda  : self.AlicatP			)
		add("Alicat T",				"C",	"%g",	lambda  : self.AlicatT			)
		add("Alicat Gas",			"",		"%s",	lambda  : self.AlicatGas		)

		#Aethalometer
		add("BC-880",				"ug/m3","%g",	lambda : self.BC880				)
		add("BC-370",				"ug/m3","%g",	lambda : self.BC370				)
		add("Atten-880",			"",		"%g",	lambda : self.Atten880			)
		add("Atten-370",			"",		"%g",	lambda : self.Atten370			)
		add("Aeth Flow",			"l/min","%g",	lambda : self.AethFlow			)

		# DustTrak
		add("PM1",					"mg/m3","%g",	lambda : self.PM1				)
		add("PM2.5",				"mg/m3","%g",	lambda : self.PM25				)
		add("PM4",					"mg/m3","%g",	lambda : self.PM4				)
		add("PM10",					"mg/m3","%g",	lambda : self.PM10				)
		add("Total PM",				"mg/m3","%g",	lambda : self.PMTotal			)

		#Need funky default argument i=i because of how lambda expressions
		#get evaluated
		#TODO: Add undersize bin
		for i in range(len(self.dNdLogDp1)-1):		# 32 + oversize
			add("FMPS_%02d"%(i+1), 	"#/cc",	"%g",	lambda i=i: self.dNdLogDp1[i])
		add("FMPS Sheath Flow",		"lpm",	"%g",	lambda : self.FMPS3091.StatusRecord.SheathFlow)
		add("FMPS Sample Flow",		"lpm",	"%g",	lambda : self.FMPS3091.StatusRecord.SampleFlow)
		add("FMPS Charger Flow",	"lpm",	"%g",	lambda : self.FMPS3091.StatusRecord.ChargerFlow)
		add("FMPS Extraction Flow",	"lpm",	"%g",	lambda : self.FMPS3091.StatusRecord.ExtractionFlow)
		#TODO: Decide if we want to log other items, such as the status flags, ...

		for i in range(len(self.dNdLogDp2)):		# 16
			add("OPS_%02d" %(i+1),	"#/cc",	"%g",	lambda i=i: self.dNdLogDp2[i])
		add("OPS Total Flow",		"lpm",	"%g",	lambda : self.OPS3330.UnitMeasurements.TotalFlow)
		add("OPS Sheath Flow",		"lpm",	"%g",	lambda : self.OPS3330.UnitMeasurements.SheathFlow)

		#TODO: Add undersize bin
		for i in range(1,len(self.dNdLogDp3)):		# 51 + undersize
			add("APS_%02d" % i,		"#/cc","%g",	lambda i=i: self.dNdLogDp3[i])
		add("APS Total Flow",		"lpm",	"%g",	lambda : self.APS3321.YRecord.TotalFlow)
		add("APS Sheath Flow",		"lpm",	"%g",	lambda : self.APS3321.YRecord.SheathFlow)
		add("APS Aerosol Flow",		"lpm",	"%g",	lambda : self.APS3321.YRecord.TotalFlow-self.APS3321.YRecord.SheathFlow)
		add("APS sTime",			"?",	"%g",	lambda : self.APS3321.DRecord.stime)
		add("APS dTime",			"?",	"%g",	lambda : self.APS3321.DRecord.dtime)
		add("APS evt1",				"",		"%g",	lambda : self.APS3321.DRecord.evt1)
		add("APS evt3",				"",		"%g",	lambda : self.APS3321.DRecord.evt3)
		#TODO: Add evt4
		#add("APS evt4",			"",		"%g",	lambda : self.APS3321.DRecord.evt4)
		add("APS total",			"",		"%g",	lambda : self.APS3321.DRecord.total)

		add("FlueTemp1",			"",		"%g",	lambda : self.FlueTemp1)
		add("FlueTemp2",			"",		"%g",	lambda : self.FlueTemp2)
		add("ManifoldAirTemp",		"",		"%g",	lambda : self.ManifoldAirTemp)
		add("InletAirTemp",			"",		"%g",	lambda : self.InletAirTemp)


	def OnClose(self, evt):
		#TODO: Ask Vi about stopping instruments, closing stdio window!
#		if wx.MessageBox("Exit Program?", "DOE Cook Stoves",
#				style=wx.OK|wx.CANCEL|wx.ICON_EXCLAMATION) != wx.OK:
#			return
#		dlg = wx.MultiChoiceDialog(self, "Exit Program?", "DOE Cook Stoves",
#					["Keep Message Dialog Window Open", "Keep Instruments Running"],
#					style = wx.CHOICEDLG_STYLE|wx.ICON_EXCLAMATION)
#		if dlg.ShowModal() != wx.ID_OK:
#			return
#		selections = dlg.GetSelections()
#		keepWindowOpen = 0 in selections
#		keepInstrumentsRunning = 1 in selections

		self.StopSecondaryThreads()
		self.StopInstruments()
		self.SaveConfig()
		if hasattr(sys.stdout, 'frame') and  hasattr(sys.stdout.frame, 'Close'):
			sys.stdout.frame.Close()
			wx.GetApp().RestoreStdio()
		evt.Skip()

	# Reset subplots_adjust avalues to keep fixed top/bottom/left/right
	# gaps as the contour and contour scale plots change size.
	# The hTop and hBot values should really change with font size.
	def OnContourSize(self, evt):
		X0, X1 = self.ui.trend1.X0, self.ui.trend1.X1
		hTop, hBot = 6, 0		#hBot = 18 with x axis tick labels
		w, h = evt.GetSize()
		w, h = max(w, 120), max(h,30)
		self.ui.contourFigure.subplots_adjust(left=X0/w, right=1-X1/w, bottom=hBot/h, top=1-hTop/h)
		evt.Skip()

	def OnContourScaleSize(self, evt):
		X0, X1 = self.ui.trend1.X0, self.ui.trend1.X1
		hTop, hBot = 45, 0
		w, h = evt.GetSize()
		w, h = max(w, X0+X1+0), max(h,hTop+hBot+1)
		self.ui.contourScaleFigure.subplots_adjust(left=X0/w, right=1-X1/w, bottom=hBot/h, top=1-hTop/h)
		evt.Skip()

	def OnFileExit(self, evt):
		self.Close()
		evt.Skip()

	def OnViewAPTValues(self, evt):
		table = [
			( "P Hood",				lambda : "%.1f" % self.PHood,			"Pa"),
			( "P Duct Pre-Sample",	lambda : "%.1f" % self.PDuctPreSample,	"Pa"),
			( "P Duct Post-Sample",	lambda : "%.1f" % self.PDuctPostSample,	"Pa"),
			( "P Pre-Iris",			lambda : "%.1f" % self.PDuctPreIris,	"Pa"),
			( "P Post-Iris",		lambda : "%.1f" % self.PDuctPostIris,	"Pa"),
			( "P Chimney",			lambda : "%.1f" % self.PChimney,		"Pa"),
			( "P Outside",			lambda : "%.1f" % self.POutside,		"Pa"),
			( 15, 0, 0),
			( "Relative Humidity",	lambda : "%.1f" % self.Humidity,		"%"),
		]
		#TODO: See if I need to do some cleanup when the dialog exits
		#self.ViewAPTValuesDialog = self.ViewTableHelper(self, "APT Values", table)
		ViewTableHelper(self, "APT Values", table)

	def OnViewFlowRates(self, evt):
		def totalFlow():
			return np.nansum([self.FMPS3091.StatusRecord.SampleFlow, self.FMPS3091.StatusRecord.ExtractionFlow,
							  self.APS3321.YRecord.TotalFlow, -self.APS3321.YRecord.SheathFlow,
							  #self.OPS3330.UnitMeasurements.TotalFlow
							  self.AethFlow])

		table = [
			( "FMPS Sheath Flow (39.4)",	lambda : "%.3f" % self.FMPS3091.StatusRecord.SheathFlow,	"l/m"),
			( "FMPS Sample Flow (8.0)",		lambda : "%.3f" % self.FMPS3091.StatusRecord.SampleFlow,	"l/m"),
			( "FMPS Charger Flow (0.6)",	lambda : "%.3f" % self.FMPS3091.StatusRecord.ChargerFlow,	"l/m"),
			( "FMPS Extraction Flow (2.0) ",lambda: "%.3f" % self.FMPS3091.StatusRecord.ExtractionFlow,	"l/m"),
			( 15, 0, 0),
			( "OPS Total Flow (1.0)",		lambda : "%.3f" % self.OPS3330.UnitMeasurements.TotalFlow,	"l/m"),
			( "OPS Sheath Flow (1.0)",		lambda : "%.3f" % self.OPS3330.UnitMeasurements.SheathFlow,	"l/m"),
			( 15, 0, 0),
			( "APS Total Flow (5.0)",		lambda : "%.3f" % self.APS3321.YRecord.TotalFlow,			"l/m"),
			( "APS Sheath Flow (4.0)",		lambda : "%.3f" % self.APS3321.YRecord.SheathFlow,			"l/m"),
			( "APS Aerosol Flow (1.0)",		lambda : "%.3f" % (self.APS3321.YRecord.TotalFlow-self.APS3321.YRecord.SheathFlow), "l/m"),
			( 15, 0, 0),
			( "Aethalometer Flow (1.4?)",	lambda : "%.3f" % self.AethFlow,							"l/m"),
			( 15, 0, 0),
			( "Total Aerosol Flow (12.4?)",	lambda : "%.3f" % totalFlow(),								"l/m"),
			( 15, 0, 0),
			( "Alicat Flow",				lambda : "%.3f" % self.AlicatFlow,							"l/m"),
		]
		#TODO: See if I need to do some cleanup when the dialog exits
		ViewTableHelper(self, "Flow Rates", table)

	def OnViewDilutedSBA5Values(self, evt):
		table = [
			( "Zero Counts",			lambda : "%.0f" % self.DilutedSBA5info.ZeroCounts, 			""),
			( "Current Counts",			lambda : "%.0f" % self.DilutedSBA5info.CurrentCounts,		""),
			( "Measured",				lambda : "%.0f" % self.DilutedSBA5info.Measured, 			"ppm"),
			( "Average Temp",			lambda : "%.1f" % self.DilutedSBA5info.AverageTemp,			"C"),
			#( "Humidity",				lambda : "%.1f" % self.DilutedSBA5info.Humidity,			"%"),
			#( "Humidity Sensor Temp",	lambda : "%.1f" % self.DilutedSBA5info.HumiditySensorTemp,	"C"),
			( "Pressure",				lambda : "%.0f" % self.DilutedSBA5info.Pressure,			"mbar"),
			( "Detector Temp",			lambda : "%.1f" % self.DilutedSBA5info.DetectorTemp,		"C"),
			( "Source Temp",			lambda : "%.1f" % self.DilutedSBA5info.SourceTemp,			"C"),
			#TODO: Decide how to handle SBA5info.Errors, which is a string that might be long!!
#			#( "Errors",					lambda : "0x%04x" % self.DilutedSBA5info.Errors,		""),#
		]
		#TODO: See if I need to do some cleanup when the dialog exits
		#self.ViewAPTValuesDialog = self.ViewTableHelper(self, "APT Values", table)
		ViewTableHelper(self, "Diluted SBA5 Values", table)

	def OnViewAmbientSBA5Values(self, evt):
		table = [
			( "Zero Counts",			lambda : "%.0f" % self.AmbientSBA5info.ZeroCounts, 			""),
			( "Current Counts",			lambda : "%.0f" % self.AmbientSBA5info.CurrentCounts,		""),
			( "Measured",				lambda : "%.0f" % self.AmbientSBA5info.Measured, 			"ppm"),
			( "Average Temp",			lambda : "%.1f" % self.AmbientSBA5info.AverageTemp,			"C"),
			#( "Humidity",				lambda : "%.1f" % self.AmbientSBA5info.Humidity,			"%"),
			#( "Humidity Sensor Temp",	lambda : "%.1f" % self.AmbientSBA5info.HumiditySensorTemp,	"C"),
			( "Pressure",				lambda : "%.0f" % self.AmbientSBA5info.Pressure,			"mbar"),
			( "Detector Temp",			lambda : "%.1f" % self.AmbientSBA5info.DetectorTemp,		"C"),
			( "Source Temp",			lambda : "%.1f" % self.AmbientSBA5info.SourceTemp,			"C"),
			#TODO: Decide how to handle SBA5info.Errors, which is a string that might be long!!
#			#( "Errors",					lambda : "0x%04x" % self.AmbientSBA5info.Errors,		""),#
		]
		#TODO: See if I need to do some cleanup when the dialog exits
		#self.ViewAPTValuesDialog = self.ViewTableHelper(self, "APT Values", table)
		ViewTableHelper(self, "Ambient SBA5 Values", table)

	def OnViewAethalometerValues(self, evt):
		table = [
			( "Date",			lambda : "%s"	% self.AethInfo.date,	 		""),
			( "Time",			lambda : "%s"	% self.AethInfo.time,			""),
			( "conc1",			lambda : "%.0f" % self.AethInfo.conc1,			""),
			( "conc2",			lambda : "%.1f" % self.AethInfo.conc2,			""),
			( "flow",			lambda : "%.1f" % self.AethInfo.flow,			"l/m"),
			( "sz1",			lambda : "%.4f" % self.AethInfo.sz1,			""),
			( "sb1",			lambda : "%.4f" % self.AethInfo.sb1,			""),
			( "rz1",			lambda : "%.4f" % self.AethInfo.rz1,			""),
			( "rb1",			lambda : "%.4f" % self.AethInfo.rb1,			""),
			( "fract1",			lambda : "%.1f" % self.AethInfo.fract1,			""),
			( "atten1",			lambda : "%.2f" % self.AethInfo.atten1,			""),
			( "sz2",			lambda : "%.4f" % self.AethInfo.sz2,			""),
			( "sb2",			lambda : "%.4f" % self.AethInfo.sb2,			""),
			( "rz2",			lambda : "%.4f" % self.AethInfo.rz2,			""),
			( "rb2",			lambda : "%.4f" % self.AethInfo.rb2,			""),
			( "fract2",			lambda : "%.1f" % self.AethInfo.fract2,			""),
			( "atten2",			lambda : "%.2f" % self.AethInfo.atten2,			""),
		]
		#TODO: See if I need to do some cleanup when the dialog exits
		#self.ViewAPTValuesDialog = self.ViewTableHelper(self, "APT Values", table)
		ViewTableHelper(self, "Aethalometer Values", table)

	def OnViewAlicatValues(self, evt):
		table = [
			( "Gas",		lambda : "%s" % self.AlicatGas,			""),
			( "P",			lambda : "%.2f" % self.AlicatP,		 	"psia"),
			( "T",			lambda : "%.2f" % self.AlicatT,			"C"),
			( "Flow Rate",	lambda : "%.1f" % self.AlicatFlow,		"lpm"),
			( "Flow Rate",	lambda : "%.1f" % self.AlicatStdFlow,	"splm"),
			( "Setpoint",	lambda : "%.1f" % self.AlicatSetpoint,	"lpm"),
		]
		#TODO: See if I need to do some cleanup when the dialog exits
		#self.ViewAPTValuesDialog = self.ViewTableHelper(self, "APT Values", table)
		ViewTableHelper(self, "Alicat Values", table)

#	def OnShowInfoBar(self, evt):
#		self.ui.infoBar.ShowMessage("\nMy Info Message.  This is a very, very, very long message line.\nblah blah blah\n", wx.ICON_WARNING)
#
#	def OnHideInfoBar(self, evt):
#		evt.Skip()

	def OnViewContourScale(self, evt):
		self.ViewContourScale = evt.Checked()
		self.ui.contourScaleCanvas.Show(self.ViewContourScale)
		self.ui.Layout()

	def OnUpdateUIViewContourScale(self, evt):
		evt.Check(self.ViewContourScale)

	def OnViewStatusIndicators(self, evt):
		self.ViewStatusIndicators = evt.Checked()
		self.ui.StatusIndicatorsPanel.Show(self.ViewStatusIndicators)
		self.ui.Layout()

		#TODO: Disable window decorations
		#disable = wx.MAXIMIZE_BOX | wx.MINIMIZE_BOX | wx.CLOSE_BOX | wx.SYSTEM_MENU | wx.CAPTION
		#disable |= wx.RESIZE_BORDER
		#self.SetWindowStyle(self.GetWindowStyle() & ~disable)

	def OnUpdateUIViewStatusIndicators(self, evt):
		evt.Check(self.ViewStatusIndicators)

	def OnViewDilutionRatio01(self, evt):
		self.ActiveDilutionRatio = 1
		self.ui.DilutionRatioLabel.SetLabel("1s DR")
		self.ui.DilutionRatioLabel.SetBackgroundColour(wx.YELLOW)

	def OnUpdateUIViewDilutionRatio01(self, evt):
		evt.Check(self.ActiveDilutionRatio == 1)

	def OnViewDilutionRatio15(self, evt):
		self.ActiveDilutionRatio = 15
		self.ui.DilutionRatioLabel.SetLabel("15s DR")
		self.ui.DilutionRatioLabel.SetBackgroundColour(wx.YELLOW)

	def OnUpdateUIViewDilutionRatio15(self, evt):
		evt.Check(self.ActiveDilutionRatio == 15)

	def OnViewDilutionRatio30(self, evt):
		self.ActiveDilutionRatio = 30
		self.ui.DilutionRatioLabel.SetLabel("30s DR")
		self.ui.DilutionRatioLabel.SetBackgroundColour(self.ui.GetBackgroundColour())

	def OnUpdateUIViewDilutionRatio30(self, evt):
		evt.Check(self.ActiveDilutionRatio == 30)

	def OnMessageFilterStart(self, evt):
		self.LogMessage("Filter Start", ""),

	def OnMessageFilterStop(self, evt):
		self.LogMessage("Filter Stop", ""),

	def OnMessageAWSScale(self, evt):
		self.LogMessage("AWS Scale", str(self.AWSMass))

	def OnMessageSartoriusScale(self, evt):
		self.LogMessage("Sartorius Scale", str(self.SartoriusMass))

	def OnMessageUser(self, evt):
			msg = wx.GetTextFromUser("Enter User Message Text", "Log Message")
			if msg != '':
				self.LogMessage("User", msg)

	def OnUpdateUILogMessage(self, evt):
		evt.Enable(self.isLogging)

	def OnLoggingStart(self, evt):
		baseName = time.strftime("%Y%m%d-%H%M")
		folder = "..\\Data\\" if Simulation else "C:\\Users\\CookStoves\\Google Drive\\75C Lab Google Drive Folder\\Data\\"
		self.message.open(folder + "%s.txt" % baseName)
		self.logger.open(folder + "%s.csv" % baseName)
		self.logger.Start()

		self.LogMessage("System", "Logging Started")
		self.LogMessage("System", "Recording concentrations measured at instruments w/o dilution correction")

		#TODO: Oversize bin
		self.LogMessage("FMPS3091", "Bin Edges: " + ' '.join("%.3f" % v for v in self.bins1[:-1]), doecho=False)
		self.LogMessage("OPS3330",  "Bin Edges: " + ' '.join("%.2f" % v for v in self.bins2), doecho=False)
		#TODO: Undersize bin
		self.LogMessage("APS3321",  "Bin Edges: " + ' '.join("%.1f" % v for v in self.bins3[1:]), doecho=False)

		self.isLogging = True

	def OnUpdateUILoggingStart(self, evt):
		evt.Enable(not self.isLogging)

	def OnLoggingStop(self, evt):
		self.isLogging = False
		self.message.close()
		self.logger.close()

	def OnUpdateUILoggingStop(self, evt):
		evt.Enable(self.isLogging)

	def OnRunTestParameters(self, evt):
		dlg = wx.Dialog(self, -1, "Test Parameters")
		vCtr = wx.ALIGN_CENTER_VERTICAL
		style = wx.TE_RIGHT
		size = (50,-1)

		flex1 = wx.FlexGridSizer(cols=3, vgap=2, hgap=10)

		flex1.Add(wx.StaticText(dlg, -1, "Stove Type"), 0, vCtr)
		stoveType = wx.TextCtrl(dlg, -1, self.StoveType, size, style=style)
		flex1.Add(stoveType, 1, vCtr)
		flex1.Add(wx.StaticText(dlg, -1, ""), 0, vCtr)

		flex1.Add(wx.StaticText(dlg, -1, "User Name"), 0, vCtr)
		userName = wx.TextCtrl(dlg, -1, self.UserName, size, style=style)
		flex1.Add(userName, 1, vCtr)
		flex1.Add(wx.StaticText(dlg, -1, ""), 0, vCtr)

		flex1.Add(wx.StaticText(dlg, -1, "Cold Start Filter ID"), 0, vCtr)
		coldFilterID = wx.TextCtrl(dlg, -1, self.ColdStartFilterID, size, style=style)
		flex1.Add(coldFilterID, 1, vCtr)
		flex1.Add(wx.StaticText(dlg, -1, ""), 0, vCtr)

		flex1.Add(wx.StaticText(dlg, -1, "Hot Start Filter ID"), 0, vCtr)
		hotFilterID = wx.TextCtrl(dlg, -1, self.HotStartFilterID, size, style=style)
		flex1.Add(hotFilterID, 1, vCtr)
		flex1.Add(wx.StaticText(dlg, -1, ""), 0, vCtr)

		flex1.Add(wx.StaticText(dlg, -1, "Simmer Filter ID"), 0, vCtr)
		simmerFilterID = wx.TextCtrl(dlg, -1, self.SimmerFilterID, size, style=style)
		flex1.Add(simmerFilterID, 1, vCtr)
		flex1.Add(wx.StaticText(dlg, -1, ""), 0, vCtr)

		if evt is None:
			buttonSizer = dlg.CreateButtonSizer(wx.OK)
		else:
			buttonSizer = dlg.CreateButtonSizer(wx.OK | wx.CANCEL)

		topLevel = wx.BoxSizer(wx.VERTICAL)
		topLevel.Add(flex1, 0, wx.EXPAND | wx.ALL, 10)
		topLevel.AddSpacer(10)
		topLevel.Add(buttonSizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)

		dlg.SetSizerAndFit(topLevel)
		#dlg.CenterOnParent()
		#Always write on when evt is None (ie invoked by Test Start)
		if dlg.ShowModal() == wx.ID_OK  or  evt is None:
			self.UserName = userName.GetValue()
			self.StoveType = stoveType.GetValue()
			self.ColdStartFilterID = coldFilterID.GetValue()
			self.HotStartFilterID = hotFilterID.GetValue()
			self.SimmerFilterID = simmerFilterID.GetValue()
#			self.TestButton.Enable(True)
#			print("%r %r %r %r %r %r" % (self.TestName, self.StoveType, self.UserName, self.ColdStartFilterID, self.HotStartFilterID, self.SimmerFilterID))
			self.LogTestParameters()
			return True
		return False

	def OnTestButton(self, evt):
		if evt.Checked():	# Test Starting
			self.LogMessage("FilterS", self.SimmerFilterID)
			self.LogMessage("User", "Test Start")
			self.TestRunning = True
			self.TestStartTime = time.time()
			self.ui.StopWatch.Start(reset=True)
			self.OnRunTestParameters(None)
		else:				# Test Stopping
			self.LogMessage("User", "Test Stop")
			self.TestRunning = False
			self.ui.StopWatch.Stop()
			self.TestStartTime = None
			#self.ui.TestTime.SetLabel("0:00")
		self.LogMessage("Sartorius", "%.1f" % self.SartoriusMass)
		self.LogMessage("AWS", "%.1f" % self.AWSMass)
		self.LogMessage("TPot", "%.1f" % self.TPot)

	def LogTestParameters(self):
#		self.LogMessage("User", "Test Start")
		self.LogMessage("Stove", self.StoveType)
		self.LogMessage("Name", self.UserName)
		self.LogMessage("FilterC", self.ColdStartFilterID)
		self.LogMessage("FilterH", self.HotStartFilterID)

	def LogCommand(self, category, prefix, result):
		self.LogMessage(category, prefix + ': ' + result)

	def LogMessage(self, category, msg, doecho=True):
#		if msg is None:
#			msg = wx.GetTextFromUser("Enter User Message Text", "Log Message")
#			if msg == '':
#				return
		self.message.LogMessage(category, msg, doecho)

	def OnOperateTareSartorius(self, evt):
		#Note: MSW Does not show ICON_QUESTION
		if wx.MessageBox("Tare Scale ?", "Sartorius", wx.YES_NO|wx.ICON_QUESTION) == wx.YES:
			self.Sartorius.SetStatusFlag('tare')

	def OnUpdateUIOperateTareSartorius(self, evt):
		evt.Enable(not self.Sartorius.TestStatusFlag('tare'))

	def OnOperateFMPS3091Zero(self, evt):
		#Note: MSW Does not show ICON_QUESTION
		if wx.MessageBox("Zero Electrometers ?", "FMPS3091", wx.YES_NO|wx.ICON_QUESTION) == wx.YES:
			self.FMPS3091.SetStatusFlag('zero')

	def OnUpdateUIOperateFMPS3091Zero(self, evt):
		evt.Enable(not self.FMPS3091.TestStatusFlag('zero'))

	def OnOperateDustTraxZero(self, evt):
		self.DustTraxZeroRequested = True

	def OnUpdateUIOperateDustTraxZero(self, evt):
		evt.Enable(not self.DustTraxZeroRequested)
		evt.Enable(False)

	def OnOperateFMPSPumpOn(self, evt):
		if evt.GetInt():
			self.FMPS3091.SetStatusFlag('pump-on')
		else:
			self.FMPS3091.SetStatusFlag('pump-off')

	def OnUpdateUIOperateFMPSPumpOn(self, evt):
		evt.Check(self.FMPS3091PumpOn)
		evt.Enable(not self.TestRunning)

	def OnOperateAPTZero(self, evt):
		self.APT.SetStatusFlag('zero')

	def OnUpdateUIOperateAPTZero(self, evt):
		evt.Enable(not self.APT.TestStatusFlag('zero'))

	def OnOperateDilutedSBA5Zero(self, evt):
		self.DilutedSBA5.SetStatusFlag('zero')

	def OnOperateAmbientSBA5Zero(self, evt):
		self.AmbientSBA5.SetStatusFlag('zero')

	def OnUpdateUIOperateDilutedSBA5Zero(self, evt):
		evt.Enable(not self.DilutedSBA5.TestStatusFlag('zero'))

	def OnUpdateUIOperateAmbientSBA5Zero(self, evt):
		evt.Enable(not self.AmbientSBA5.TestStatusFlag('zero'))

	def OnHelpAbout(self, evt):
		info = wx.AboutDialogInfo()
		info.SetDescription("DOE Cook Stoves Lab")
		info.SetVersion(time.strftime("%m/%d/%Y", time.localtime(os.path.getmtime(sys.argv[0]))))
		info.AddDeveloper("Gary Hubbard")
		wx.AboutBox(info)

	def OnHelpInspection(self, evt):
		wx.lib.inspection.InspectionTool().Show()

	def OnSetupPlotOptions(self, evt):
		dlg = wx.Dialog(self, -1, "Setup Plotting Options")
		vCtr = wx.ALIGN_CENTER_VERTICAL
		style = wx.TE_RIGHT
		size = (50,-1)

		flex1 = wx.FlexGridSizer(cols=3, vgap=2, hgap=10)
		flex1.Add(wx.StaticText(dlg, -1, "Minimum dNdLogDp"), 0, vCtr)
		dNdLogDMin = controls.FloatCtrl(dlg, -1, self.dNdLogDMin, size, style=style, format='%.0e')
		flex1.Add(dNdLogDMin, 1, vCtr)
		flex1.Add(wx.StaticText(dlg, -1, "#/cc"), 0, vCtr)

		flex1.Add(wx.StaticText(dlg, -1, "Maximum dNdLogDp"), 0, vCtr)
		dNdLogDMax = controls.FloatCtrl(dlg, -1, self.dNdLogDMax, size, style=style, format='%.0e')
		flex1.Add(dNdLogDMax, 1, vCtr)
		flex1.Add(wx.StaticText(dlg, -1, "#/cc"), 0, vCtr)

		flex1.AddSpacer(10); flex1.AddSpacer(10); flex1.AddSpacer(10);

		flex1.Add(wx.StaticText(dlg, -1, "Linear Scale for Line Plot"), 0, vCtr)
		linear = wx.CheckBox(dlg, -1, "")
		linear.SetValue(self.LinearDist)
		flex1.Add(linear, 1, vCtr)
		flex1.Add(wx.StaticText(dlg, -1, ""), 0, vCtr)

		flex1.Add(wx.StaticText(dlg, -1, "Linear Scale for Contour Plot"), 0, vCtr)
		linear2 = wx.CheckBox(dlg, -1, "")
		linear2.SetValue(self.LinearContour)
		flex1.Add(linear2, 1, vCtr)
		flex1.Add(wx.StaticText(dlg, -1, ""), 0, vCtr)

		flex1.Add(wx.StaticText(dlg, -1, "Display Contour Dividers"), 0, vCtr)
		dividers = wx.CheckBox(dlg, -1, "")
		dividers.SetValue(self.ShowContourDividers)
		flex1.Add(dividers, 1, vCtr)
		flex1.Add(wx.StaticText(dlg, -1, ""), 0, vCtr)

		flex1.AddSpacer(10); flex1.AddSpacer(10); flex1.AddSpacer(10);

		flex1.Add(wx.StaticText(dlg, -1, "Maximum PM 2.5"), 0, vCtr)
		PM25Max = controls.FloatCtrl(dlg, -1, self.PM25Max, size=size, style=style)
		flex1.Add(PM25Max, 1, vCtr)
		flex1.Add(wx.StaticText(dlg, -1, "mg/m^3"), 0, vCtr)

		flex1.Add(wx.StaticText(dlg, -1, "Maximum BC @ 880 nm"), 0, vCtr)
		BC880Max = controls.FloatCtrl(dlg, -1, self.BC880Max, size=size, style=style)
		flex1.Add(BC880Max, 1, vCtr)
		flex1.Add(wx.StaticText(dlg, -1, "ug/m^3"), 0, vCtr)

		flex1.AddSpacer(10); flex1.AddSpacer(10); flex1.AddSpacer(10);

		flex1.Add(wx.StaticText(dlg, -1, "Maximum CAI CO2"), 0, vCtr)
		CO2Max = controls.FloatCtrl(dlg, -1, self.CO2Max, size=size, style=style)
		flex1.Add(CO2Max, 1, vCtr)
		flex1.Add(wx.StaticText(dlg, -1, "ppm"), 0, vCtr)

		flex1.Add(wx.StaticText(dlg, -1, "Maximum CAI CO"), 0, vCtr)
		COMax = controls.FloatCtrl(dlg, -1, self.COMax, size=size, style=style)
		flex1.Add(COMax, 1, vCtr)
		flex1.Add(wx.StaticText(dlg, -1, "ppm"), 0, vCtr)
		buttonSizer = dlg.CreateButtonSizer(wx.OK | wx.CANCEL)

		topLevel = wx.BoxSizer(wx.VERTICAL)
		topLevel.Add(flex1, 0, wx.EXPAND | wx.ALL, 10)
		topLevel.AddSpacer(10)
		topLevel.Add(buttonSizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)

		dlg.SetSizerAndFit(topLevel)
		dlg.CenterOnParent()
		if dlg.ShowModal() == wx.ID_OK:
			self.dNdLogDMin = dNdLogDMin.GetValue()
			self.dNdLogDMax = dNdLogDMax.GetValue()
			self.CO2Max     = CO2Max.GetValue()
			self.PM25Max    = PM25Max.GetValue()
			self.BC880Max   = BC880Max.GetValue()
			self.COMax  	= COMax.GetValue()
			self.LinearDist = linear.GetValue()
			self.LinearContour = linear2.GetValue()
			self.ShowContourDividers = dividers.GetValue()

			self.SetTrendLimits()
			self.SetupFigures()
			self.SaveConfig()

	def StopSecondaryThreads(self):
		self.stopTasks.RunAll()
		self.waitTasks.RunAll()

	def SetupInstruments(self):
		self.FMPS3091 = self.SerialInstrument("FMPS3091", TSI.FMPS3091)
		self.OPS3330  = self.TcpIpInstrument("OPS3330",  TSI.OPS3330)
		self.APS3321  = self.SerialInstrument("APS3321", TSI.APS3321)
		self.DustTrax = self.TcpIpInstrument("DustTrax",  TSI.DustTrax)

		self.Alicat   = self.SerialInstrument("Alicat", Alicat.MSeries)
		self.Sartorius= self.SerialInstrument("Sartorius", Sartorius.Combics1)
		self.APT      = self.SerialInstrument("APT", APT.APT)
		self.DilutedSBA5 = self.SerialInstrument("Diluted SBA5", PPSystems.SBA5)
		self.AmbientSBA5 = self.SerialInstrument("Ambient SBA5", PPSystems.SBA5)
		self.Aethalometer=self.SerialInstrument("Aethalometer", Magee.Aethalometer)
		self.CAI602P  = self.SerialInstrument("CAI-602P", CAI.MODEL602P_NDIR)
		self.AWS      = self.SerialInstrument("AWS", AWS.Scale)

		if not SkipTemperatures:
			print("")
			print("Connecting to MeasurementComputing Device.")
			print("If the program hangs at this point, kill it and run Instacal.")
			print("Click on Yes to run the HID Registry Update Entry.")
			print("Accept the Windows request for administrative rights.")
			print("Click Update.")
			print("Unplug and replug the USB cable Measurement Computing device atop the CAI Analyzer")
			sys.stdout.flush()
			self.USB_TC_AI = cbw.CBW(0)
			_,_,_ = self.USB_TC_AI.TInScan(0,2)
			print("")
			print("Everything is OK.  No need to run instacal")
			print("")
			print("")

		#TODO: Ini setting to disable this
		self.FlueTemp1, self.FlueTemp2, self.ManifoldAirTemp, self.InletAirTemp = [np.nan]*4

		self.TCTasks = []
		for module in range(4):
			section = "Simulation/" if Simulation else "Hardware/"
			dev = wx.Config.Get().Read(section+"NI TC %d" % (module+1), "")
			if dev == "":
				break
			task = DAQmx.Task('TC Task %d' % (module+1))
			task.CreateAIThrmcplChan(dev + "/ai0:3", "",
						0, 800, units="C", tcType="K")
			#This will run at 2.5 Hz w/ the 9211 at 4 Channel w/ CJC + ???
			sampleRate = task.SampClkMaxRate
			numSamples = 0	# This is the buffer size for Val_ContSamps
			task.CfgSampClkTiming(None, sampleRate, DAQmx.Val_Rising,
					DAQmx.Val_ContSamps, numSamples)
			task.Start()
			self.TCTasks.append(task)
		self.NITemps = np.zeros(4*len(self.TCTasks))
		self.NITemps[:] = np.nan
		if len(self.NITemps) == 4:
			self.FlueTemp1, self.FlueTemp2, self.ManifoldAirTemp, self.InletAirTemp = self.NITemps
		self.FlueTemp1, self.FlueTemp2, self.ManifoldAirTemp, self.InletAirTemp = [np.nan]*4
	
		#TODO: Decide on this pressure filter.  Would a median be better???
		self.PressureFilter=[]
		for i in range(7):
			self.PressureFilter.append(filter.MovingMean(size=None, duration=1.0))

		self.IrisFlowFilter = filter.MovingMean(size=None, duration=60)
		self.DilutionRatioFilter01 = filter.MovingMean(size=None, duration= 1)
		self.DilutionRatioFilter15 = filter.MovingMean(size=None, duration=15)
		self.DilutionRatioFilter30 = filter.MovingMean(size=None, duration=30)

		self.SetupBinEdgeDiameters()

		#Set initial values for all the inputs.
		#The -1's here are because the bin diameters are the lower edges,
		#so we need one extra to get the upper end of the last bin.
		self.dNdLogDp1 = np.zeros(len(self.bins1)-1)
		self.dNdLogDp2 = np.zeros(len(self.bins2)-1)
		self.dNdLogDp3 = np.zeros(len(self.bins3)-1)

		nan = np.nan

		# TODO: Doing this causes an error in matplotlib/transforms.py @ line 661
		# I am patching things in the SetupSizeDistributionPlot
		# Should I start with all values of zero anyway?
		self.dNdLogDp1[:] = nan
		self.dNdLogDp2[:] = nan
		self.dNdLogDp3[:] = nan

		#DustTrax
		self.PM1, self.PM25, self.PM4, self.PM10, self.PMTotal = [nan]*5

		#Aethalometer
		self.BC880, self.BC370, self.Atten880, self.Atten370, self.AethFlow = [nan]*5
		self.AethInfo = self.Aethalometer.valuesType("", "",
									np.nan, np.nan, np.nan, np.nan, np.nan,
									np.nan, np.nan, np.nan, np.nan, np.nan,
									np.nan, np.nan, np.nan, np.nan, np.nan)

		# APT
		self.PHood, self.PDuctPreSample, self.PDuctPostSample = [nan]*3
		self.PDuctPreIris, self.PDuctPostIris, self.PChimney, self.POutside = [nan]*4
		self.Humidity = nan

		#CAI
		self.DuctCO2, self.DuctCO, self.DuctO2 = [nan]*3

		#Diluted SBA5
		self.DilutedCO2 = nan
		self.DilutedSBA5info = self.DilutedSBA5.measurementType(nan, nan, nan, nan, nan, nan, nan, nan, nan, 0)

		#Ambient SBA5
		self.AmbientCO2 = nan
		self.AmbientSBA5info = self.AmbientSBA5.measurementType(nan, nan, nan, nan, nan, nan, nan, nan, nan, 0)

		# Sartorius and AWS
		self.SartoriusMass, self.AWSMass = [nan]*2

		# Alicat
		self.AlicatP, self.AlicatT, self.AlicatGas = nan, nan, "?"
		self.AlicatFlow, self.AlicatStdFlow, self.AlicatSetpoint = [nan]*3

		self.TPot, self.TAmb, self.TDuct = nan, nan, nan

		self.IrisFlow = nan
		self.FilteredIrisFlow = nan

		self.CAI602P.ErrorStatus = []

		#Data type of initial value is different from real one
		class C(): pass
		self.FMPS3091.StatusRecord = C()
		self.FMPS3091.StatusRecord.SheathFlow = nan
		self.FMPS3091.StatusRecord.SampleFlow = nan
		self.FMPS3091.StatusRecord.ChargerFlow = nan
		self.FMPS3091.StatusRecord.ExtractionFlow = nan
		self.FMPS3091.StatusRecord.ErrorCode1 = 0
		self.FMPS3091.StatusRecord.ErrorCode2 = 0

		#Data type of initial value is different from real one
		self.OPS3330.UnitMeasurements = C()
		self.OPS3330.UnitMeasurements.TotalFlow = nan
		self.OPS3330.UnitMeasurements.SheathFlow = nan

		self.APS3321.YRecord = self.APS3321.YRecordType(*([nan]*16))
		self.APS3321.DRecord = self.APS3321.DRecordType('SAX',0,0,0,0,0,0,0,0, np.array([np.nan]*52))

	def SerialInstrument(self, name, constructor, verifier=None, verbosity=0):
		section = "Simulation/" if Simulation else "Hardware/"
		port = wx.Config.Get().Read(section+name, "")
		try:
			d = constructor(port, verbosity=verbosity)
		except serial.SerialException as e:
			wx.MessageBox(str(e) + "\n\n%s disabled for this session" % name, name,
				style=wx.wx.ICON_EXCLAMATION)
			#Create a dummy device
			d = constructor("", verbosity=0)
		return d

	def TcpIpInstrument(self, name, constructor, verifier=None, verbosity=0):
		section = "Simulation/" if Simulation else "Hardware/"
		s = wx.Config.Get().Read(section+name, "")
		parts = s.split(',', 1)
		host = parts[0]
		port = 3602 if len(parts) < 2 else int(parts[1])
		#TODO: Switch to ipAddr,port in config file
		try:
			d = constructor(host, port, verbosity=verbosity)
		except (socket.error, socket.timeout) as e:
			wx.MessageBox(str(e) + "\nDevice disabled for this session", name,
				style=wx.wx.ICON_EXCLAMATION)
			#Create a dummy device
			d = constructor("", verbosity=0)
		return d

	def StartInstruments(self):
		if self.FMPS3091.IsReal():
			self.FMPS3091.fd.flushInput()
			self.LogCommand("FMPS3091", "Set Flow On",
					self.FMPS3091.SetFlow("on"))
			self.FMPS3091PumpOn = True
		if self.APS3321.IsReal():
			self.LogCommand("APS3321", "Set Mode And Sample Time",
					self.APS3321.SetModeAndSampleTime('S', 1))
			self.LogCommand("APS3321", "Turn Pumps On",
					self.APS3321.SetPumps(True, True))
			self.LogCommand("APS3321", "Start",
					self.APS3321.StartMeasurement())

		if self.OPS3330.IsReal():
			self.LogCommand("OPS3330", "Write Logging Mode Setup Data",
					self.OPS3330.WriteLoggingModeSetUpData(
						sampleLength="0:0:1",numberOfSamples=9959,
						numberOfSets=0,	repeatInterval="0:2:46"))
			#TODO: Format this better
			self.LogCommand("OPS3330", "User Calibration Setup Data",
					str(self.OPS3330.ReadUserCalibrationSetupData()))
			self.LogCommand("OPS3330", "Start",
					self.OPS3330.StartMeasurement())
			self.OPS3330.FaultMessages = self.OPS3330.ReadFaultMessages()

		if self.DustTrax.IsReal():
			self.LogCommand("DustTrax", "Start",
					self.DustTrax.StartMeasurement())
			self.DustTrax.FaultMessages = self.DustTrax.ReadFaultMessages()
#			if not SkipTemperatures  and  self.DustTrax.FaultMessages.MemoryPercentageAvailable < 90:
#				wx.MessageBox("Warning: Only %d%% memory available" %
#								self.DustTrax.FaultMessages.MemoryPercentageAvailable,
#							caption = 'DustTrax')

		if self.DilutedSBA5.IsReal():
			#TODO: LogCommand?  The error string is often mangled
			self.LogCommand("Diluted SBA5", "Set Low Alarm Limit 0", self.DilutedSBA5.SetLowAlarmLimit(0))

		if self.AmbientSBA5.IsReal():
			#TODO: LogCommand?  The error string is often mangled
			self.LogCommand("Ambient SBA5", "Set Low Alarm Limit 0", self.AmbientSBA5.SetLowAlarmLimit(0))

		self.timer.Start(998)		# TODO: Clean this up
		self.stopTasks.Insert(self.timer.Stop)

		#The rest of these are effectively no-op's when in Simulation mode
		#The cancelIo flag is true on the SBA5 and the Aethalometer because
		#they run in unpolled mode with a relatively slow read rate.  It would
		#probably be fine to have cancelIo=False on the SBA5 because it reads
		#every 1.5 seconds or so.  The code needs to be able to deal with getting
		#an unexpected record anyway, so there is really no downside to doing
		#a cancel.
		self.FMPS3091.Start(self.UpdateFMPS)
		self.stopTasks.Insert(self.FMPS3091.Stop, wait=False, cancelIo=False)
		self.waitTasks.Insert(self.FMPS3091.Wait)

		#self.OPS3330.Start(self.UpdateOPS)
		#self.stopTasks.Insert(self.OPS3330.Stop, wait=False, cancelIo=False)

		self.APS3321.Start(self.UpdateAPS)
		self.stopTasks.Insert(self.APS3321.Stop, wait=False, cancelIo=False)
		self.waitTasks.Insert(self.APS3321.Wait)

		#self.DustTrax.Start(self.UpdateDustTrax)
		#self.stopTasks.Insert(self.DustTrax.Stop, wait=False, cancelIo=False)

		self.APT.Start(self.UpdateAPT)
		self.stopTasks.Insert(self.APT.Stop, wait=False, cancelIo=True)
		self.waitTasks.Insert(self.APT.Wait)

		self.Sartorius.Start(self.UpdateSartorius)
		self.stopTasks.Insert(self.Sartorius.Stop, wait=False, cancelIo=False)
		self.waitTasks.Insert(self.Sartorius.Wait)

		self.Alicat.Start(self.UpdateAlicat)
		self.stopTasks.Insert(self.Alicat.Stop, wait=False, cancelIo=False)
		self.waitTasks.Insert(self.Alicat.Wait)

		self.CAI602P.Start(self.UpdateCAI)
		self.stopTasks.Insert(self.CAI602P.Stop, wait=False, cancelIo=False)
		self.waitTasks.Insert(self.CAI602P.Wait)

		self.Aethalometer.Start(self.UpdateAethalometer)
		self.stopTasks.Insert(self.Aethalometer.Stop, wait=False, cancelIo=True)
		self.waitTasks.Insert(self.Aethalometer.Wait)

		self.AWS.Start(self.UpdateAWS)
		self.stopTasks.Insert(self.AWS.Stop, wait=False, cancelIo=False)
		self.waitTasks.Insert(self.AWS.Wait)

		self.DilutedSBA5.Start(self.UpdateDilutedSBA5)
		self.stopTasks.Insert(self.DilutedSBA5.Stop, wait=False, cancelIo=True)
		self.waitTasks.Insert(self.DilutedSBA5.Wait)

		self.AmbientSBA5.Start(self.UpdateAmbientSBA5)
		self.stopTasks.Insert(self.AmbientSBA5.Stop, wait=False, cancelIo=True)
		self.waitTasks.Insert(self.AmbientSBA5.Wait)

	def StopInstruments(self):
		#TODO: Is this sleep necessary?
		#It is safer, as it presumably guarantees the results of all aborted
		#serial reads are now in the appropriat4e buffer to be flushed as
		#needed.
		#self.LogMessage("xxx", "Stop Instruments")
		#time.sleep(1)
		#self.LogMessage("xxx", "Sleep done")
		#It takes a 3 second sleep for the FMPS pump off to work the "normal"
		#way.  I need to investigate that.
		if self.FMPS3091.IsReal():
			self.FMPS3091.fd.flushInput()
			self.LogCommand("FMPS3091", "Set Flow Off",
					self.FMPS3091.SetFlow("off"))
			self.FMPS3091PumpOn = False
		if self.APS3321.IsReal():
			self.LogCommand("APS3321", "Turn Pumps Off",
					self.APS3321.SetPumps(False, False))
			self.LogCommand("APS3321", "Stop", self.APS3321.StopMeasurement())
		if self.OPS3330.IsReal():
			self.LogCommand("OPS3330", "Stop", self.OPS3330.StopMeasurement())
		if self.DustTrax.IsReal():
			self.LogMessage("DustTrax", "Stop", self.DustTrax.StopMeasurement())

	#def OnKeyDown(self, evt):
	#	print("OnKeyDown", evt.GetKeyCode())
	#	evt.Skip()

	#def OnKeyUp(self, evt):
	#	print("OnKeyUp", evt.GetKeyCode())
	#	evt.Skip()

	#def OnCharHook(self, evt):
	#	print("OnCharHook", evt.AltDown(), evt.ControlDown(), evt.GetKeyCode(), evt.GetRawKeyCode(), hex(evt.GetRawKeyFlags()))
	#	#evt.Skip()
	#	evt.DoAllowNextEvent()

	def OnTimer(self, evt):
		self.UpdateInputs()

		self.UpdateUI()
		if self.isLogging:
			self.logger.Write()
		evt.Skip()

	def SetupBinEdgeDiameters(self):
		self.bins1 = self.FMPS3091.GetBinEdges()
		self.bins2 = self.OPS3330.GetBinEdges()
		self.bins3 = self.APS3321.GetBinEdges()

	def UpdateInputs(self):
		if Simulation  and  self.Playback:
			self.UpdatePlaybackValues()
		elif Simulation:
			t = time.clock()
			dMean, sigma, maxVal = math.log(100), 1.5, 3e6
			f0 = 1 - np.exp(-min(t,600)/600.0)
			f1 = 1 - np.exp(-min(t,600)/400.0)
			maxVal *= min(t,600)/600
			for d,dNdLogDp in [(self.bins1, self.dNdLogDp1),
							   (self.bins2, self.dNdLogDp2),
							   (self.bins3, self.dNdLogDp3)]:
				d = np.log(np.sqrt(d[1:] * d[0:-1]))
				r = np.random.normal(1.0, 0.2, len(d))
				dNdLogDp[:] = maxVal * r * np.exp(- ((d-dMean)/sigma) ** 2)

			self.TPot = min(100, 100 * (t+120) / 600) + np.random.normal(0, 0.5)
			self.TAmb = np.random.normal(22, 2)
			self.TDuct = np.random.normal(28, 2)
			self.Humidity = np.random.normal(50, 2)
			self.PM25 = np.random.normal(5, 0.2) * f0
			self.BC880 = np.random.normal(300, 20) * f1
			self.AlicatFlow = 0
			self.AWSMass = 0
			self.DuctCO2 = np.random.normal(3500, 100) * f0
			self.DuctCO = np.random.normal(200, 10) * f1
			self.DuctO2 = np.random.normal(20, 1)
			self.DilutedCO2 = np.random.normal(self.DuctCO2/20, 5)
			self.AmbientCO2 = np.random.normal(450, 20)
			self.Atten370 = np.random.normal(12.34, 1)

			self.PDuctPostIris = np.random.normal(-138, 10)
			self.PDuctPreIris = np.random.normal(-10, 10)
			self.POutside = 1.0

			self.APS3321.YRecord = self.APS3321.YRecordType(980,5,4,0,0,0,0,0,0,0,0,0,0,0,0,0)

			dP = max(0, self.PDuctPreIris - self.PDuctPostIris)
			self.IrisFlow = self.ComputeIrisFlow(dP, P=101325, T=self.TDuct)

		if not np.isnan(self.IrisFlow):
			self.FilteredIrisFlow = self.IrisFlowFilter.AddValue(self.IrisFlow)
			#print("iris", self.IrisFlow, self.FilteredIrisFlow)

		if not SkipTemperatures:
			self.TPot, self.TAmb, self.TDuct = self.USB_TC_AI.TInScan(0,2)

		for i, task in enumerate(self.TCTasks):
			values = task.ReadAnalogF64(-1, -1, DAQmx.Val_GroupByChannel)
			if values.shape[1] > 0:
				values = np.array(values).mean(axis=-1)
				self.NITemps[i*4:i*4+4] = values
		#self.NITemps[self.NITemps > 999] = -1
		#print(self.NITemps)
		if len(self.NITemps) == 4:
			self.FlueTemp1, self.FlueTemp2, self.ManifoldAirTemp, self.InletAirTemp = self.NITemps

		if self.OPS3330.IsReal():
			self.UpdateOPS()
			if self.OPS3330.UnitMeasurements.TotalFlow < 0.7:
				self.LogMessage("OPS", str(self.OPS3330.UnitMeasurements))
			errorState = self.OPS3330.CheckFaultState(self.OPS3330.FaultMessages)
			errorMessage = self.OPS3330.FormatFaultMessages(self.OPS3330.FaultMessages)
			self.ui.Indicators['OPS3330'].SetValue(errorState, errorMessage)
			if errorState:
				self.LogMessage("OPS", errorMessage)

		#TODO: Measure how long this takes
		if self.DustTrax.IsReal():
			self.UpdateDustTrax()
			errorState = self.DustTrax.CheckFaultState(self.DustTrax.FaultMessages)
			errorMessage = self.DustTrax.FormatFaultMessages(self.DustTrax.FaultMessages)
			self.ui.Indicators['DustTrax'].SetValue(errorState, errorMessage)
			if errorState != 0:
				self.LogMessage("DustTrax", errorMessage)

		if Simulation  or  (time.clock() > 30  and  self.FMPS3091PumpOn):
			status = (self.FMPS3091.StatusRecord.ErrorCode1 << 32) | self.FMPS3091.StatusRecord.ErrorCode2
			self.ui.Indicators['FMPS3091'].SetValue(status != 0, "Status=0x%x" % status)
			if (self.FMPS3091.StatusRecord.ErrorCode1 != 0 or
				self.FMPS3091.StatusRecord.ErrorCode2 != 0):
					self.LogMessage("FPMS", str(self.FMPS3091.StatusRecord))

		if Simulation  or  time.clock() > 30:
			#This instrument takes a considerable amount of time to startup, and
			#indicates errors until it actually does.
			status = self.APS3321.DRecord.status
#			self.ui.Indicators['APS3321'].SetValue(status != 0, "Status=0x%04x" % status)
			s = self.APS3321.FormatStatusValue(status)
			self.ui.Indicators['APS3321'].SetValue(status != 0,
											'Status: '+s)
			if status != 0:
				self.LogMessage("APS3321", "Status=0x%04x: %s" % (status, s))

		#TODO: Should I also check one or both attenuations here??
		if not np.isnan(self.AethInfo.flow):
			#Can't do this until I get an Aethalometer read (up to 5 seconds)
			#TODO: Ask Vi if I should alarm on either or both attenuation values
			if abs(self.AethInfo.flow-1.4) < 0.2:
				self.ui.Indicators['Aethalometer'].SetValue(0,"")
			else:
				self.ui.Indicators['Aethalometer'].SetValue(1,"Flow Rate")

		if self.CAI602P.IsReal():
			#errorCodes = []
			errorCodes = self.CAI602P.ErrorStatus
			if len(errorCodes) == 0:
				self.ui.Indicators['CAI-602P'].SetValue(0,"")
			else:
				errText = self.CAI602P.GetErrorText(errorCodes)
				errText = '; '.join(errText)
				self.ui.Indicators['CAI-602P'].SetValue(1, errText)
				#TODO: Restore this when the CAI gets fixed
				self.LogMessage("CAI-602P", errText)

		#TODO: Ask Vi if I should alarm on the Alicat flow rate not matching setpoint

		#TODO:Ask Vi if I should alarm on the SBA5 pressure

		#TODO: Ask Vi if I should alarm on the SBA5 pressure

	def UpdatePlaybackValues(self):
		p = self.Playback
		s = p.readline()

		self.TPot = p.getvalue(float, "T Pot")
		self.TAmb = p.getvalue(float, "T Amb")
		self.TDuct = p.getvalue(float, "T Duct")

		self.PHood = p.getvalue(float, "P Hood")
		self.PDuctPreSample = p.getvalue(float, "P DuctPreSample")
		self.PDuctPostSample = p.getvalue(float, "P DuctPostSample")
		self.PDuctPreIris = p.getvalue(float,"P PreIris")
		self.PDuctPostIris = p.getvalue(float, "P PostIris")
		self.PChimney = p.getvalue(float, "P Chimney")
		self.POutside = p.getvalue(float, "P Outside")
		self.Humidity = p.getvalue(float, "RH")

		#TODO: The BDS file has a 1 for this !!! and no column header
		#self.IrisFlow = p.getvalue(float)

		self.DuctCO2 = p.getvalue(float, "CO2")
		self.DuctCO = p.getvalue(float, "CO")
		self.DuctO2 = p.getvalue(float, "O2")

		self.DilutedCO2 = p.getvalue(float, "CO2#2")

#		self.AmbientCO2 = p.getvalue(float)

		self.SartoriusMass = p.getvalue(float, "Satorious")

		self.AWSMass = p.getvalue(float, "AWS")

		self.AlicatFlow = p.getvalue(float, "Flow")
		self.AlicatStdFlow = p.getvalue(float, "StdFlow")
		self.AlicatSetpoint = p.getvalue(float, "Setpoint")
		self.AlicatP = p.getvalue(float, "Alicat P")
		self.AlicatT = p.getvalue(float, "Alicat T")
		self.AlicatGas = p.getvalue(str, "Alicat Gas")

		self.BC880 = p.getvalue(float, "BC-880")
		self.BC370 = p.getvalue(float, "BC-370")
		self.Atten880 = p.getvalue(float, "Atten-880")
		self.Atten370 = p.getvalue(float, "Atten-370")
		self.AethFlow = p.getvalue(float, "Aeth Flow")

		self.PM1 = p.getvalue(float, "PM1")
		self.PM25 = p.getvalue(float, "PM2.5")
		self.PM4 = p.getvalue(float, "PM4")
		self.PM10 = p.getvalue(float, "PM10")
		self.PMTotal = p.getvalue(float, "Total PM")

		for i in range(len(self.dNdLogDp1)-1):		# FMPS 32 + oversize bins
			self.dNdLogDp1[i] = p.getvalue(float, "FMPS_%02d" % (i+1))
		#These have no header on BDS file
		#self.FMPS3091.StatusRecord.SheathFlow = p.getvalue(float)
		#self.FMPS3091.StatusRecord.SampleFlow = p.getvalue(float)
		#self.FMPS3091.StatusRecord.ChargerFlow = p.getvalue(float)
		#self.FMPS3091.StatusRecord.ExtractionFlow = p.getvalue(float)

		for i in range(len(self.dNdLogDp2)):		# OPS 16 bins
			self.dNdLogDp2[i] = p.getvalue(float, "OPS_%02d" % (i+1))
		#These have no header info on the BDS file
		#self.OPS3330.UnitMeasurements.TotalFlow = p.getvalue(float)
		#self.OPS3330.UnitMeasurements.SheathFlow = p.getvalue(float)

		for i in range(1,len(self.dNdLogDp3)):		# APS = 51 + undersize
			self.dNdLogDp3[i] = p.getvalue(float, "APS_%02d" % i)
			
		#These have no header info on the BDS file
		#totalFlow = p.getvalue(float)
		#sheathFlow = p.getvalue(float)
		#aerosolFlow = p.getvalue(float)
		#stime = p.getvalue(float)
		#dtime = p.getvalue(float)
		#evt1 = p.getvalue(float)
		#evt3 = p.getvalue(float)
		#total = p.getvalue(float)
		#self.APS3321.YRecord = self.APS3321.YRecord._replace(TotalFlow=totalFlow, SheathFlow=sheathFlow)
		#self.APS3321.DRecord = self.APS3321.DRecord._replace(stime=stime, dtime=dtime, evt1=evt1, evt3=evt3, total=total)

		dP = max(0, self.PDuctPreIris - self.PDuctPostIris)
		self.IrisFlow = self.ComputeIrisFlow(dP, P=101325, T=self.TDuct)

	def UpdateFMPS(self):
		if self.FMPS3091.TestStatusFlag('zero'):
			self.FMPS3091.ZeroElectrometers()
			self.FMPS3091.ClearStatusFlag('zero')
			time.sleep(1)

		if self.FMPS3091.TestStatusFlag('pump-on'):
			self.FMPS3091.ClearStatusFlag('pump-on')
			self.LogCommand("FMPS3091", "Set Flow On",
					self.FMPS3091.SetFlow("on"))
			self.FMPS3091PumpOn = True

		if self.FMPS3091.TestStatusFlag('pump-off'):
			self.FMPS3091.ClearStatusFlag('pump-off')
			self.LogCommand("FMPS3091", "Set Flow Off",
					self.FMPS3091.SetFlow("off"))
			#time.sleep(1)
			#self.FMPS3091.fd.flushInput()
			self.FMPS3091PumpOn = False

		#FPMS - This runs at 1 Hz, waiting for the FMPS3091 to update
		dNdLogDp1 = self.FMPS3091.ReadRDR7().Data
		statusRecord = self.FMPS3091.ReadRSR()

		#Update non-atomic values in the main thread.
		def Update():
			self.dNdLogDp1 = dNdLogDp1
			#TODO: Find a better way than monkey patching this in
			self.FMPS3091.StatusRecord = statusRecord
		wx.CallAfter(Update)

	def UpdateOPS(self):
		#OPS - ~25 milliseconds
		#Longer now after adding the unit measurements and fault messages
		#Skip last bin, which has value for d > 10000 nm
		dNdLogDp2 = self.OPS3330.ReadCurrentMeasurement()[0:-1]
		#TODO: Avoid monkey patching here
		unitMeasurements = self.OPS3330.ReadUnitMeasurements()
		faultMessages = self.OPS3330.ReadFaultMessages()

		#Update non-atomic values in the main thread.
		def Update():
			self.dNdLogDp2 = dNdLogDp2
			#TODO: Find a better way than monkey patching this in
			self.OPS3330.UnitMeasurements = unitMeasurements
			self.OPS3330.FaultMessages = faultMessages
		wx.CallAfter(Update)

	def UpdateAPS(self):
		#APS - ~200 ms
		yRecord = self.APS3321.ReadYRecord()
		dRecord = self.APS3321.ReadDRecord()

		#32 bins/decade, 60 sec/min, 1000 cc/liter
		#Figure out the stime and dtime values issue.  Both are zero with
		#a sample time of 1 second
		dt = 1
		aerosolFlow = yRecord.TotalFlow - yRecord.SheathFlow
		#TODO: Is this the best way to deal with this?
		if aerosolFlow == 0: aerosolFlow = np.nan
		dNdLogDp3 = [32*60*c/dt/aerosolFlow/1000.0 for c in dRecord.counts]
		#dNdLogDp3[0] /= 8	# Adjust for larger bin 0

		#Update non-atomic values in the main thread.
		def Update():
			self.dNdLogDp3 = dNdLogDp3
			self.APS3321.DRecord = dRecord
			self.APS3321.YRecord = yRecord
		wx.CallAfter(Update)
		time.sleep(0.3)

	def UpdateDustTrax(self):
		#DustTrax: ~25 ms, w/ lots of jitter
		self.PM1, self.PM25, self.PM4, self.PM10, self.PMTotal = self.DustTrax.ReadCurrentMeasurements()
		#TODO: Avoid monkey patching here
		self.DustTrax.FaultMessages = self.DustTrax.ReadFaultMessages()

	def UpdateAPT(self):
		if self.APT.TestStatusFlag('zero'):
			self.LogMessage("APT", "Zero Requested")
			#TODO: Create better API for this
			for i in range(7):
				self.APT.UpdateNoLoadPressure(i+1, gain=1)
				if self.APT.IsStopping():
					return
			self.APT.ClearStatusFlag('zero')
			self.LogMessage("APT", "Zero Complete")

		#318 ms for 7 pressures and 1 analog channel
		pFiltered = []
		for i in range(7):
			p = self.APT.GetPressure(i+1,gain=1)
			pFiltered.append(self.PressureFilter[i].AddValue(p))
			if self.APT.IsStopping():
				return
		v = self.APT.GetAnalogInput(1, True)

		#Thread safe: Atomic
		self.PHood    		= pFiltered[0]
		self.PDuctPreSample = pFiltered[1]
		self.PDuctPostSample= pFiltered[2]
		self.PDuctPreIris 	= pFiltered[3]
		self.PDuctPostIris	= pFiltered[4]
		self.PChimney 		= pFiltered[5]
		self.POutside 		= pFiltered[6]
		self.Humidity 		= -34.33 + 34.681 * v

		dP = max(0, self.PDuctPreIris - self.PDuctPostIris)
		#dP = 128
		h = 252
		P = 29.95*3386 * (1-2.2477e-5 * h) ** 5.25588
		self.IrisFlow = self.ComputeIrisFlow(dP, P=P, T=self.TDuct)
		#print('Iris Flow', dP, P, self.TDuct, self.IrisFlow)

	def UpdateSartorius(self):
		if self.Sartorius.TestStatusFlag('tare'):
			self.LogMessage("Sartorius", "Tare")
			self.Sartorius.Tare()
			self.Sartorius.ClearStatusFlag('tare')

		hdr, mass, units = self.Sartorius.GetValue()
		self.SartoriusMass = mass

	def UpdateAWS(self):
		mass = self.AWS.RequestWeightData()
		#Thread safe: Atomic
		self.AWSMass = mass

	def UpdateAethalometer(self):
		v = self.Aethalometer.GetValues()
		#Thread safe: Atomic
		#Could have some updated but not others when a write occurs, but I doubt I care
		self.BC880 = v.conc1 / 1000
		self.BC370 = v.conc2 / 1000
		self.Atten880 = v.atten1
		self.Atten370 = v.atten2
		self.AethFlow = v.flow

		#Update non-atomic values in main thread
		def Update():
			self.AethInfo = v
		wx.CallAfter(Update)

	def UpdateAlicat(self):
		x = self.Alicat.GetValues()
		#Thread safe: Atomic
		#Could have some updated but not others when a write occurs, but I doubt I care
		self.AlicatP, self.AlicatT, self.AlicatGas = x.P, x.T, x.Gas
		self.AlicatFlow, self.AlicatStdFlow, self.AlicatSetpoint = x.Flow, x.StdFlow, x.Setpoint

	def UpdateCAI(self):
		#Thread safe: Atomic.
		#Could have some updated but not others when a write occurs, but I doubt I care
		self.DuctCO2, self.DuctCO, self.DuctO2, t = self.CAI602P.GetMeasuredConcentrationValues()
		self.CAI602P.ErrorStatus = self.CAI602P.GetErrorStatus()

	def UpdateDilutedSBA5(self):
		if self.DilutedSBA5.TestStatusFlag('zero'):
			#TODO: This just starts a zero operation, does not wait for it to complete
			#Should't really change 'zero' flag until it does.
			self.LogCommand("Diluted SBA5", "Zero Requested", self.DilutedSBA5.Zero())
			self.DilutedSBA5.ClearStatusFlag('zero')

		v, msg = self.DilutedSBA5.GetRecord()
		if msg is not None  and msg != '':
			if msg.startswith("Z,"):# Looks like Z,## of  ##
				parts = msg.split()
				now = int(parts[0].split(',')[1])
				max = int(parts[2])
				if (now == 0  or now == max):
					self.LogMessage("Diluted SBA5", msg)
			else:
				self.LogMessage('Diluted SBA5', repr(msg))
		if v is not None:
			#Thread safe: Atomic
			self.DilutedCO2 = v.Measured

			#Update non-atomic values in main thread
			def update():
				self.DilutedSBA5info = v
			wx.CallAfter(update)

	def UpdateAmbientSBA5(self):
		if self.AmbientSBA5.TestStatusFlag('zero'):
			#TODO: This just starts a zero operation, does not wait for it to complete
			#Should't really change 'zero' flag until it does.
			self.LogCommand("Ambient SBA5", "Zero Requested", self.AmbientSBA5.Zero())
			self.AmbientSBA5.ClearStatusFlag('zero')

		v, msg = self.AmbientSBA5.GetRecord()
		if msg is not None  and msg != '':
			if msg.startswith("Z,"):# Looks like Z,## of  ##
				parts = msg.split()
				now = int(parts[0].split(',')[1])
				max = int(parts[2])
				if (now == 0  or now == max):
					self.LogMessage("Ambient SBA5", msg)
			else:
				self.LogMessage('Ambient SBA5', repr(msg))
		if v is not None:
			#Thread safe: Atomic
			self.AmbientCO2 = v.Measured

			#Update non-atomic values in main thread
			def update():
				self.AmbientSBA5info = v
			wx.CallAfter(update)

	def ComputeIrisFlow(self, deltaP, P, T):
		# Compute Saturation pressure of H2O
		# Ref http://www.vaisala.com/Vaisala%20Documents/Application%20notes/Humidity_Conversion_Formulas_B210973EN-F.pdf
		# Temperature range -20 to 50 C
		# Return value is in Pascals

		def SaturationPressure(T):
			A = 6.116441
			m = 7.591386
			Tn = 240.7263
			PSat = A * 10 ** (m * T / (T + Tn))
			return 100 * PSat

		D  = 6 * 0.0254	# Duct diameter [m]
		D0 = 0.1164	# Orifice diameter [m]
		Cd = 0.6052	# Discharge coefficient

		A0 = 0.25 * math.pi * D0**2
		beta = D0/D

		RUniv = 8314.4621
		#mwAir = 28.965			# -> R = 287.052 where Julian had 286.9
		#mwH2O = 18.01528		# -> R = 461.522 where Julian had 461.5
		##B = mwAir/mwH2O		# 0.621967 where Julian had 0.6219907
		##print R/mwAir, R/mwH2O, mwH2O/mwAir
		#
		if 1:
			mW = 28.965
		else:
			RH = 100
			PSat = SaturationPressure(T)
			pH2O = .01 * RH * PSat
			x = pH2O / P
			mwAir, mwH2O = 28.965, 18.0
			mW = (1-x) * mwAir + x * mwH2O
			print("Molecular Weight Air", mW)
		density = P * mW / (RUniv * (T+273.15))

		Q = Cd * A0 * math.sqrt(2 * deltaP / density / (1 - beta**4))
		return Q * 60 / (0.3048**3)

		#TODO: Ask Vi as to where my ISO duct flow calculation is going astray
		#K = 375
		#deltaP = self.PDuctPreIris - self.PDuctPostIris
		#deltaP = max(deltaP, 0)
		#Q = K * math.sqrt(deltaP * 0.004014)	#Pa -> inches H2O
		#self.IrisFlow = Q

	def UpdateUI(self):
		if self.TestRunning:
			testTime = int(round(time.time() - self.TestStartTime))
			self.ui.TestTime.SetLabel("%d:%02d" % (testTime // 60, testTime % 60))

		self.UpdateContourValues()
		self.UpdateSizeDistributionFigure(self.ui.concentrationFigure)
		self.UpdateContourFigure(self.ui.contourFigure)

		self.ui.trend1.AddPoint(self.PM25, self.BC880)
		self.ui.trend2.AddPoint(self.DuctCO2, self.DuctCO, self.DilutedCO2, self.AmbientCO2)
		self.ui.trend3.AddPoint(self.TPot, self.TAmb, self.TDuct, self.Humidity)
#		self.ui.trend3.AddPoint(self.PHood, self.PDuctPreIris, self.PDuctPostIris, self.POutside)

		rawDilutionRatio = -1 if self.DilutedCO2 <= 0 else self.DuctCO2 / self.DilutedCO2
		if np.isnan(rawDilutionRatio)  or  rawDilutionRatio < 0:
			dilutionRatio01 = -1
			dilutionRatio15 = -1
			dilutionRatio30 = -1
		else:
			dilutionRatio01 = self.DilutionRatioFilter01.AddValue(rawDilutionRatio)
			dilutionRatio15 = self.DilutionRatioFilter15.AddValue(rawDilutionRatio)
			dilutionRatio30 = self.DilutionRatioFilter30.AddValue(rawDilutionRatio)
		self.ui.Update(SartoriusMass=self.SartoriusMass,
					   AWSMass=self.AWSMass,
					   TPot=self.TPot,
					   AlicatFlow=self.AlicatFlow,
#					   DilutionRatio=self.DilutionRatio30,
					   #IrisDP=self.PDuctPreIris - self.PDuctPostIris,
					   FilteredIrisFlow=self.FilteredIrisFlow,
					   OutInDP=self.POutside,
					   DuctCO2=self.DuctCO2,
					   Atten370=self.Atten370)

		self.ui.UpdateWallTime(self.TestRunning)
		if self.ActiveDilutionRatio == 1:
			self.ui.Update(DilutionRatio=dilutionRatio01)
		elif self.ActiveDilutionRatio == 15:
			self.ui.Update(DilutionRatio=dilutionRatio15)
		else:
			self.ui.Update(DilutionRatio=dilutionRatio30)

		self.ui.Update(FlueTemp1=self.FlueTemp1,
					   FlueTemp2=self.FlueTemp2,
					   InletAirTemp=self.InletAirTemp,
					   ManifoldAirTemp=self.ManifoldAirTemp)

	def SetupContourValues(self):
		#TODO: Ask Vi if I should start at 5 or 5.6234... nm
		#Bottom of FMPS to top of OPS.  Not plotting APS at all
		#TODO: Ask Vi about that

		# The contour plot has pixels at 32 bins per decade, running from
		# dMin to dMax nanometers. There is one pixel for each contour bins.
		# With dMin, dMax = 5, 10000 it has  106 rows.
		# With dMin, dMax = 5.6234, 10000 it has  104 rows.
		# There are 600 columns, 1 per second for 10 minutes.
		
		self.ContourDMin, self.ContourDMax = 5.623413252, 10000.0
		self.ContourBinWidth = math.log10(10) / 32		# 32 bins per decade
		dMin, dMax = self.ContourDMin, self.ContourDMax
		binWidth = self.ContourBinWidth
		nr = int(math.ceil(math.log10(dMax/dMin) / binWidth))
		nc = NCOLS
		self.ContourValues = np.zeros((nr, nc))
		self.ContourValues[:,:] = np.nan

	def UpdateContourValues(self):
		dMin, dMax = self.ContourDMin, self.ContourDMax
		binWidth = self.ContourBinWidth
		nr, nc = self.ContourValues.shape

		# Scroll existing data left on plot
		self.ContourValues[:, 0:nc-1] = self.ContourValues[:, 1:nc]

		# Stuff new values into the last column
		# Note: We are are ignoring the APS values completely at the moment
		# TODO: There should be a check that I don't run off the end of the
		# array because there is a d below dMin or above dMax.
		# n is the number of bins in the device, i is the row in the contour
		# that the data starts at, m is the bin width of the device as a
		# multiple of master bin width (32/decade).
		self.ContourValues[:,-1] = 0

		# This logic assumes we are start using each device at the lowest
		# possible diameter, which would not be appropriate if we ever added
		# in the APS.
		#Ask Vi if I should plot APS values between 10 and 20 um
		for name, bins, dNdLogDp in [('FMPS', self.bins1[:-1], self.dNdLogDp1[:-1]),
									 ('OPS',  self.bins2,	   self.dNdLogDp2)]:
			n = len(dNdLogDp)
			i = int(round(math.log10(bins[0]/dMin) / binWidth))
			W = math.log10(bins[-1] / bins[0]) / n / binWidth
			m = int(round(W))
			widths = np.log10(bins[1:]/bins[0:-1]) / binWidth
			deviation = max(widths) - min(widths)
			#print('%-4s bins  n=%2d  start=%2d  width=%3.1f (%d)' % (name, n, i, W, m))
			assert abs(m-W)/W < 1e-3, name+' diameter limits not an integer multiple of 1/32 decade'
			assert deviation < 1e-10, name+' bins not all the same width'
			self.ContourValues[i:i+m*n,-1] = np.repeat(dNdLogDp, m)

	def SetupFigures(self):
		self.SetupSizeDistributionFigure(self.ui.concentrationFigure)
		self.SetupContourScaleFigure(self.ui.contourScaleFigure)
		self.SetupContourFigure(self.ui.contourFigure)

	def SetupSizeDistributionFigure(self, fig):
		fig.clear()
		ax = fig.add_subplot(1,1,1)
		dMin, dMax = 5, 20000

		ax.grid(True, which='major', axis='both')

		ax.set_xscale('log')
		ax.set_xlim(dMin, dMax)
		#Must use LogFormatter for real matplotlib
		#ax.xaxis.set_major_formatter(mpl.ticker.LogFormatter())
		ax.xaxis.set_major_formatter(mpl.ticker.ScalarFormatter())
		ax.xaxis.set_minor_locator(mpl.ticker.LogLocator(subs=[2, 3, 4, 5, 6, 7, 8, 9]))

		yMin, yMax = self.dNdLogDMin, self.dNdLogDMax
		if self.LinearDist:
			ax.set_ylim(0, yMax)
			#TODO: How to make exponential formatting work here???
			#ax.yaxis.set_major_formatter(mpl.ticker.LogFormatterMathtext(labelOnlyBase=False))
			#ax.yaxis.set_major_formatter(mpl.ticker.LogFormatter(labelOnlyBase=False))
			def formatter(value, pos):
				#print("formatter1", value, pos)	
				if value == 0:
					return "0"
				e = math.floor(math.log10(value))
				v = value / 10**e
				return "%ge%d" % (v, e)
				#return "$10^%d$" % (e) if v == 1 else "$%g\cdot10^%d$" % (v, e)
			ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(formatter))
		else:
			ax.set_yscale('log')
			ax.set_ylim(yMin, yMax)

		ax.tick_params('both', length=10, width=0.5, which='major')
		ax.tick_params('both', length= 5, width=0.5, which='minor')

		ax.set_xlabel("Particle Diameter  [nm]")
		ax.set_ylabel("Concentration,  dN / dLogDp  [#/cc]")

		# Plot lines passing through the bin center diameters
		# TODO: If the dNdLogDp values are all NaNs matplotlib gives an error
		lines = []
		labels = []
		lineWidth = 1.5
		for (label, bins, dNdLogDp, color) in [
					#TODO: Decide whether to plot oversize bin
					('FMPS', self.bins1[:-1], self.dNdLogDp1[:-1], 'r'),
					('OPS',  self.bins2,      self.dNdLogDp2, 'g'),
					#TODO: Decide whether to plot undersize bin
					('APS',  self.bins3[1:],  self.dNdLogDp3[1:], 'b')]:
			centers = np.sqrt(bins[0:-1] * bins[1:])
			dNdLogDp[:] = 0
			ax.plot(centers, dNdLogDp, color=color, linewidth=lineWidth)
			labels.append(label)
			lines.append(mpl.lines.Line2D([], [], color=color, linewidth=lineWidth))
		ax.legend(lines, labels)
		fig.canvas.draw()

	def UpdateSizeDistributionFigure(self, fig):
		ax, = fig.get_axes()

		lineWidth = 2
		for i,(label, bins, dNdLogDp, color) in enumerate([
					#Label strings and colors are not used here
					#TODO: Decide whether to plot oversize bin
					('FMPS', self.bins1[:-1], self.dNdLogDp1[:-1], 'r'),
					('OPS',  self.bins2,      self.dNdLogDp2, 'g'),
					#TODO: Decide whether to plot undersize bin
					('APS',  self.bins3[1:],  self.dNdLogDp3[1:], 'b')]):
			line = ax.lines[i]
			centers = np.sqrt(bins[0:-1] * bins[1:])
			dNdLogDp = np.clip(dNdLogDp, 1e-10, 1e10)	# Eliminate negative values
			line.set_data(centers, dNdLogDp)
		fig.canvas.draw()

	def SetupContourScaleFigure(self, fig):
		fig.clear()
		nr, nc = 2, NCOLS

		A = np.zeros((nr,nc))
		A[:,:] = np.linspace(0,1, num=nc, endpoint=True)

		ax = fig.add_subplot(1,1,1)
		if self.LinearContour:
			#ax0 is for the image, linear scale
			#ax1 is for the tick marks and labels, linear scale

			cMin, cMax = 0, self.dNdLogDMax
			ax0 = ax
			cMin0, cMax0 = cMin, cMax

			ax1 = ax.twiny()	# ax0, ax1 share y axis
			ax1.set_xlim(cMin, cMax)
			def formatter(value, pos):
				if value == 0:
					return "0"
				e = math.floor(math.log10(value))
				v = value / 10**e
				s = "%de%d" % (v, e)
				#s = "$10^%d$" % (e) if v == 1 else "$%g\cdot10^%d$" % (v, e)
				#print("ContourScale", value, pos, s)
				return s
			ax1.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(formatter))
			#ax1.xaxis.set_major_formatter(mpl.ticker.LogFormatterMathtext())
			ax1.yaxis.set_major_locator(mpl.ticker.NullLocator())
		else:
			#ax0 is for the image, linear scale
			#ax1 is for the tick marks and labels, log scale

			cMin, cMax = self.dNdLogDMin, self.dNdLogDMax
			ax0 = ax
			cMin0, cMax0 = math.log10(cMin), math.log10(cMax)
			ax0.set_xlim(cMin0, cMax0)
			ax0.set_ylim(0, nr-1)

			ax1 = ax.twiny()	# ax0, ax1 share y axis
			ax1.set_xscale('log')
			ax1.set_xlim(cMin, cMax)
			ax1.xaxis.set_major_formatter(mpl.ticker.LogFormatterMathtext())
#			ax1.xaxis.set_label_position('top')
#			ax1.xaxis.set_tick_params(labelbottom='off', labeltop='on')
			ax1.set_xlabel("Concentration,  dN/dLogDp   [#/cc]")

		ax0.set_xscale('linear')
		ax0.set_xlim(cMin0, cMax0)
		ax0.set_ylim(0, nr-1)
		ax0.xaxis.set_major_locator(mpl.ticker.NullLocator())
		ax0.yaxis.set_major_locator(mpl.ticker.NullLocator())

		# Hide the ticks on the scale
		ax1.tick_params('both', length=0, width=1, which='both')

		ax0.imshow(A, extent=[cMin0, cMax0, 0, 1],
					aspect='auto',
					#cmap=mpl.cm.get_cmap('Blues'),
					#cmap=mpl.cm.gray,
					interpolation='none',
					vmin=0, vmax=1.0)
		fig.canvas.draw()

	def SetupContourFigure(self, fig):
		fig.clear()
		ax = fig.add_subplot(1,1,1)

		A = self.ContourValues
		nr, nc = A.shape
		dMin, dMax = self.ContourDMin, self.ContourDMax

		#
		# To get the tick marks to show over the contour image itself,
		# the former must be drawn first, meaning the later needs to
		# be drawn on the twin'ed axis.
		#

		# ax0 = Main axis. Linear scaled in log10 of diameter for imshow
		ax0 = ax
		ax0.set_xlim(0, nc)
		dMin0, dMax0 = math.log10(dMin), math.log10(dMax)
		ax0.set_ylim(dMin0, dMax0)
		ax0.xaxis.set_major_locator(mpl.ticker.NullLocator())
		ax0.yaxis.set_major_locator(mpl.ticker.NullLocator())
		ax0.set_xlabel("Time [seconds]")

		if self.LinearContour:
			norm = mpl.colors.Normalize(0, self.dNdLogDMax, clip=True)
			#values = np.linspace(0, self.dNdLogDMax,num=nr, endpoint=True)
			#for col in range(nc):
			#	A[:,col] = values
		else:
			norm = mpl.colors.LogNorm(self.dNdLogDMin, self.dNdLogDMax, clip=True)

		# Need to have (0, nc) instead of 0, nc-1 to get tick label at 600 ????
		ax0.imshow(A, extent=[0, nc, dMin0, dMax0],
					aspect='auto',
					origin='bottom',
					#cmap=mpl.cm.gray,
					#cmap= 'PuBu_r',
					interpolation='none',
					#interpolation='bilinear',
					norm=norm)

		# ax1 = Secondary axis.  Log scaledon for ticks and tick labels
		ax1 = ax.twinx()	# ax1, ax0 share x axis
		ax1.set_yscale('log')
		ax1.set_ylim(dMin, dMax)
		ax1.xaxis.set_major_locator(mpl.ticker.MultipleLocator(60))
		ax1.xaxis.set_minor_locator(mpl.ticker.MultipleLocator(10))
		ax1.yaxis.set_major_locator(mpl.ticker.LogLocator())
		#Which is better, exponential notation or not ?
		ax1.yaxis.set_major_formatter(mpl.ticker.FormatStrFormatter("%g"))
		#ax1.yaxis.set_major_formatter(mpl.ticker.LogFormatterMathtext())
		ax1.yaxis.set_tick_params(left=True, right=True, which='both')
		ax1.yaxis.set_tick_params(labelleft=True, labelright=False)
		ax1.set_ylabel("Particle Diameter  [nm]")
		ax1.yaxis.set_label_position('left')

		#TODO: Ask Vi about tick marks and grid
#		ax0.tick_params('both', length=20, width=1, which='major')
#		ax0.tick_params('both', length=10, width=1, which='minor')
#		ax0.grid(True, which='major', axis='both', linestyle='-', linewidth=0.5, color='#303030')

		if self.ShowContourDividers:
			for d in [self.bins2[0]]:
				ax1.axhline(d, color='#808080')
		fig.canvas.draw()

	def UpdateContourFigure(self, fig):
		ax0 = fig.axes[0]
		ax0.images[0].set_data(self.ContourValues)
		fig.canvas.draw()

	def SetTrendLimits(self):
		self.ui.trend1.SetRange(0, 0.0, self.PM25Max,     5, 2)
		self.ui.trend1.SetRange(1, 0.0, self.BC880Max,    5, 2)

		self.ui.trend2.SetRange(0, 0.0, self.CO2Max,      5, 2)
		self.ui.trend2.SetRange(1, 0.0, self.COMax,       5, 2)
		self.ui.trend2.SetRange(2, 0.0, self.COMax,       5, 2)
		self.ui.trend2.SetRange(3, 0.0, self.COMax,		  5, 2)

		self.ui.trend3.SetRange(0, 0.0, 105, 5.25, 2)	# note: non-integer number of ticks
		self.ui.trend3.SetRange(1, 0.0, 105, 5.25, 2)
		self.ui.trend3.SetRange(2, 0.0, 105, 5.25, 2)
		self.ui.trend3.SetRange(3, 0.0, 105, 5.25, 2)

		#For when trend3 shows APS information
#		self.ui.trend3.SetRange(0, -300.0, 0)
#		self.ui.trend3.SetRange(1, -300.0, 0)
#		self.ui.trend3.SetRange(2, -300.0, 0)
#		self.ui.trend3.SetRange(3, -300.0, 0)


##	def add_mpl_toolbar(self):
##		self.toolbar = NavigationToolbar2Wx(self.canvas)
##		self.toolbar.Realize()"
##		if wx.Platform == '__WXMAC__':
##			# Mac platform (OSX 10.3, MacPython) does not seem to cope with
##			# having a toolbar in a sizer. This work-around gets the buttons
##			# back, but at the expense of having the toolbar at the top
##			self.SetToolBar(self.toolbar)
##		else:
##			# On Windows platform, default window size is incorrect, so set
##			# toolbar width to figure width.
##			tw, th = self.toolbar.GetSizeTuple()
##			fw, fh = self.canvas.GetSizeTuple()
##			# By adding toolbar in sizer, we are able to put it at the bottom
##			# of the frame - so appearance is closer to GTK version.
##			# As noted above, doesn't work for Mac.
##			self.toolbar.SetSize(wx.Size(fw, th))
##			self.sizer.Add(self.toolbar, 0, wx.LEFT | wx.EXPAND)
##		# update the axes menu on the toolbar
##		self.toolbar.update()


class ViewTableHelper:
	def __init__(self, parent, name, table):

		dlg = wx.Dialog(parent, -1, name)
		vCtr = wx.ALIGN_CENTER_VERTICAL
		style = wx.TE_RIGHT
		size = (100,-1)

		font = wx.Font(16, wx.FONTFAMILY_DEFAULT,
					wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False,  "Segoe UI")

		self.widgets = {}
		flex = wx.FlexGridSizer(cols=3, vgap=2, hgap=10)
		for name, fct, units in table:
			if isinstance(name, int):
				flex.AddSpacer(name); flex.AddSpacer(0); flex.AddSpacer(0)
				continue

			w = wx.StaticText(dlg, -1, name)
			w.SetFont(font)
			flex.Add(w, 0, vCtr)

			w = wx.StaticText(dlg, -1, fct(), size=size, style=wx.ALIGN_RIGHT)
			w.SetFont(font)
			flex.Add(w, 0, vCtr)
			self.widgets[name] = w

			w = wx.StaticText(dlg, -1, units)
			w.SetFont(font)
			flex.Add(w, 0, vCtr)

		buttonSizer = dlg.CreateButtonSizer(wx.CLOSE)

		topLevel = wx.BoxSizer(wx.VERTICAL)
		topLevel.Add(flex, 0, wx.EXPAND | wx.ALL, 10)
		topLevel.AddSpacer(10)
		topLevel.Add(buttonSizer, 0, wx.ALIGN_CENTER | wx.ALL, 10)
		dlg.SetSizerAndFit(topLevel)

		self.dlg = dlg
		self.table = table
		self.timer = wx.Timer(self.dlg, -1)
		self.timer.Start(1000)
		dlg.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)

		dlg.Bind(wx.EVT_CLOSE, self.OnClose)
		dlg.Bind(wx.EVT_BUTTON, self.OnClose, id=wx.ID_CLOSE)
		dlg.Show()

	def OnTimer(self, evt):
		for name, fct, units in self.table:
			if isinstance(name, int):
				continue
			w = self.widgets[name]
			w.SetLabel(fct())

	def OnClose(self, evt):
		self.timer.Stop()
		self.dlg.Show(False)
		self.dlg.Destroy()



class App(wx.App):
	def OnInit(self):
		self.SetOutputWindowAttributes("Cook Stoves Running Messages", size=(600,300))
		self.frame = CookStovesFrame()
		try:
			self.frame.Initialize()
		except (Exception) as e:
			traceback.print_exc()
			s = ''.join(traceback.format_exception_only(type(e), e))
			if hasattr(sys.stdout, 'frame'):#  and  not Simulation:
				#This prevents the dialog window from closing until the user
				#acknowledges the error, but the dialog window can't be
				#scrolled or resized.
				wx.MessageBox(s, "Initialization error")
			self.frame.StopSecondaryThreads()
			self.RestoreStdio()
			return False
		self.frame.Show(True)
		return True

	#def FilterEvent(self, evt):
	#	evtType = evt.GetEventType()
	#	#TODO: Don't know what 10055 is, but it is w
	#	#print(wx.wxEVT_CHAR, wx.wxEVT_CHAR_HOOK, wx.wxEVT_KEY_DOWN, wx.wxEVT_KEY_UP, )
	#	if evtType == wx.wxEVT_KEY_DOWN  or  evtType == wx.wxEVT_KEY_UP:
	#		print("FilterEvent", evt.GetEventType(), evt.GetKeyCode(), evt.GetRawKeyCode())
	#	return -1;

if __name__ == "__main__":
	guiLaunch = "pythonw" in sys.executable or  "pyw" in sys.executable
#	parser = argparse.ArgumentParser(description="New Shaft Python Interface")
#	parser.add_argument("-d", "--dump", default=None,  metavar="abc",
#					   help="Filename prefix to dump Chris Carlen style Outputs")
#	parser.add_argument("-g", "--gui", type=bool,  default=guiLaunch,
#					   help="Use GUI window for console ouput")
#	parser.add_argument("fileName", type=str,  default=None, nargs='?',
#					   help="Shaft sequence or batch file (w/ @)")
#	args = parser.parse_args()

	app = App(redirect=guiLaunch)
	#app.SetCallFilterEvent(True)
	if guiLaunch:
		w,h = 475,525
		sys.stdout.frame.SetSize((w,h))
		sys.stdout.frame.SetPosition((1920-w,0))
	app.MainLoop()
