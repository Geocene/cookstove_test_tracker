from __future__ import absolute_import, division, print_function	#, unicode_literals

import time
import wx
#import wx.lib.buttons
import buttons

import numpy as np

class StaticFloat (wx.StaticText):
	def __init__(self, parent, id=-1, value=None, pos=(-1,-1), size=(-1,-1),
				 style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE, format="%g",
				 name='StaticFloat'):
		wx.StaticText.__init__(self, parent, id, "", pos, size, style, name)
		self._format = format
		self.wasInAlarm = False
		self.SetAlarmLimits(None, None)
		self.SetValue(value)

	def SetAlarmLimits(self, loAlarm, hiAlarm):
		#print('SetAlarmLimits', loAlarm, hiAlarm)
		if loAlarm is None:
			loAlarm = -1e100
		if hiAlarm is None:
			hiAlarm =  1e100
		self.alarmLimits = [loAlarm, hiAlarm]

	def SetFormat(self, format):
		self._format = format
		self.SetValue(self.GetValue())

	def GetValue(self):
		return self._value

	def SetValue(self, value):
		self._value = value

		if value == None:
			self.SetLabel('')
		elif np.isnan(value)  or  np.isinf(value):
			self.SetLabel('')
		else:
			self.SetLabel(self._format % value)

			inAlarm = not (self.alarmLimits[0] <= self._value <= self.alarmLimits[1])
			if not inAlarm:
				if self.wasInAlarm:
					self.SetForegroundColour(wx.BLACK)
					#self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))
					self.SetBackgroundColour(wx.Colour(192,192,192))
			else:
				if not self.wasInAlarm:
					#self.SetForegroundColour(wx.WHITE)
					#self.SetForegroundColour(wx.Colour(192,192,192))
					#self.SetBackgroundColour(wx.Colour(0,128,0))
					self.SetBackgroundColour(wx.YELLOW)
			self.wasInAlarm = inAlarm
		self.Refresh()


class FloatCtrl (wx.TextCtrl):
	def __init__(self, parent, id=-1, value=0, pos=(-1,-1), size=(50,-1),
				 style=wx.TE_RIGHT, format="%g"):
		wx.TextCtrl.__init__(self, parent, id, "", pos, size, style)
		self._format = format
		self.SetValue(value)

	def SetFormat(self, format):
		self._format = format
		self.SetValue(self.GetValue())

	def GetValue(self):
		#print(repr(wx.TextCtrl.GetValue(self)))
		return float(wx.TextCtrl.GetValue(self))

	def SetValue(self,value):
		#self.SetLabel(self._format % value)
		wx.TextCtrl.SetValue(self, self._format % value)


class RoundedIndicator(wx.PyControl):
#	self._indicators = []

	def __init__(self, parent, id, label, size):
		wx.PyControl.__init__(self, parent, id, pos=(0,0), size=size, style=wx.NO_BORDER)

		self._latchedValue = None
		self._toolTipObject = wx.ToolTip("OK")
		#This seeme to be ignored on MSW!  The manual says otherwise
		self._toolTipObject.SetMaxWidth(-1)
		self.SetToolTip(self._toolTipObject)

		self.SetValue(0)
		self.SetLabel(label)
#		self._colours = [wx.GREEN, wx.YELLOW, wx.RED]
		self._colours = [wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE), wx.RED, wx.RED]

#		self._indicators.append(self)
#		self._state = False
#		self._timer = wx.Timer(self, -1)
#		self._timer.Start(1000)

		self.Bind(wx.EVT_PAINT, self.OnPaint)
#		self.Bind(wx.EVT_TIMER, self.OnTimer, self._timer)
		self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)

	def SetValue(self, value, toolTip=None):
		#print("SetValue: %s %s %s" % (self.GetLabel(), value, toolTip))
		self._value = value
		self._toolTip = toolTip if toolTip is not None else str(value)
		if self._latchedValue is None  or  value > self._latchedValue:
			self._latchedValue = value
			self._latchedToolTip = self._toolTip
		self.UpdateToolTipString()
		self.Refresh()

	def GetValue(self):
		return self._value

#	def GetLatchedValue(self):
#		return self._latchedValue

	def UpdateToolTipString(self):
		#TODO: Use SetToolTip(wx.ToolTip(s)) to allow long tool tips
#		self.SetToolTipString("%s\n  Current=%d\n  Latched=%d" % (self.GetLabel(), self._value, self._latchedValue))
		s = u"Current: %s\nLatched: %s" % (self._toolTip, self._latchedToolTip)
#		self.SetToolTipString(s)
		self._toolTipObject.SetTip(s)
		#This seeme to be ignored on MSW!  The manual says otherwise
		self._toolTipObject.SetMaxWidth(-1)

	def OnClearLatch(self, evt):
		self._latchedValue = self._value
		self._latchedToolTip = self._toolTip
		self.UpdateToolTipString()
		self.Refresh()

	def OnRightDown(self, evt):
		menu = wx.Menu()
		item = menu.Append(-1, "Clear Latch")
		if self._value >= self._latchedValue:
			item.Enable(False)
		menu.Bind(wx.EVT_MENU, self.OnClearLatch, item)
#		item = menu.Append(-1, "Set OK")
#		menu.Bind(wx.EVT_MENU, lambda evt: self.SetValue(0, "OK"), item)
#		item = menu.Append(-1, "Set Warning")
#		menu.Bind(wx.EVT_MENU, lambda evt: self.SetValue(1, "ErrorConcidence=1"), item)
#		item = menu.Append(-1, "Set Error")
#		menu.Bind(wx.EVT_MENU, lambda evt: self.SetValue(2, "ErrorConcidence=2"), item)
		self.PopupMenu(menu)

#	def OnTimer(self, evt):
#		self._state = not self._state
#		self.Refresh()

	def DoGetBestSize(self):
		"""
		Overridden base class virtual.  Determines the best size of the
		button based on the label and bezel size.
		"""

		label = self.GetLabel()

		dc = wx.ClientDC(self)
		dc.SetFont(self.GetFont())
		retWidth, retHeight = dc.GetTextExtent(label)
		#print('DoGetBestSize',wx.Size(retWidth, retHeight))

		# 75 = minimum width, 20 is minimum total extra space horizontally
		# 26 = minimum height, 6 is minimum total extra space vertically
		constant1 = 20
		constant2 = 6
		retWidth = max(retWidth+constant1, 75)
		retHeight = max(retHeight+constant2, 26)

		#print('DoGetBestSize',wx.Size(retWidth+constant1, retHeight+constant2))
		return wx.Size(retWidth+constant1, retHeight+constant2)

	def OnPaint(self, evt):
		""" Handles the wx.EVT_PAINT event for L{RoundedIndicator). """

		dc = wx.BufferedPaintDC(self)
		gc = wx.GraphicsContext.Create(dc)

		# Fill the entire widget with the parent's background color
		dc.SetBackground(wx.Brush(self.GetParent().GetBackgroundColour()))
		dc.Clear()

		# These fudge factors make it match an XP native button
		x, y, width, height = self.GetClientRect()
		x, y, width, height = x+1, y+1, width-2, height-3
		#width = (width//2 - 1)*2

		fg = self.GetForegroundColour()
		if 0:	# Concentric RoundedRectangles: Latched on inside
			gc.SetPen(wx.Pen(fg))
			gc.SetBrush(wx.Brush(self.GetFillColour(False)))
			gc.DrawPath(self.GetPath(gc, x, y, width, height, height/2))

			gc.SetPen(wx.NullPen)
			gc.SetBrush(wx.Brush(self.GetFillColour(True)))
			gc.DrawPath(self.GetPath(gc, x+8, y+4, width-16, height-2*4+1, (height-2*2)//2))
		else:	# Single RoundedRectangle: Latched on Right Half
			path = self.GetPath(gc, x, y, width, height, height/2-1)
			#The +1 in the clip limits is because border is outside the path rectangle
			gc.Clip(x,y, width//2,height+1)
			gc.SetPen(wx.Pen(fg))
			gc.SetBrush(wx.Brush(self.GetFillColour(False)))
			gc.DrawPath(path)

			gc.ResetClip()
			gc.Clip(x+width//2,y, (width+1)//2+1,height+1)
			gc.SetBrush(wx.Brush(self.GetFillColour(True)))
			gc.DrawPath(path)

			gc.ResetClip()

		font = gc.CreateFont(self.GetFont(), fg)
		gc.SetFont(font)
		label = self.GetLabel()
		tw, th = gc.GetTextExtent(label)

		gc.DrawText(label, (width-tw)/2 + 3, (height-th)/2+1)

	def GetPath(self, gc, x, y, w, h, r):
		""" Returns a rounded Rectangle GraphicsPath. """

		path = gc.CreatePath()
		path.AddRoundedRectangle(x, y, w, h, r)
		path.CloseSubpath()
		return path

	def GetFillColour(self, inner):
		return self._colours[self._latchedValue if inner else self._value]

class StopWatchButton(buttons.Button):
	def __init__(self, parent, id, label, *args,  **kwargs):
		try:
			self._useExternalTimer = kwargs['useExternalTimer']
			del kwargs['useExternalTimer']
		except KeyError:
			self._useExternalTimer = False
		buttons.Button.__init__(self, parent, id, "0:00", *args, **kwargs)
		self.SetPeriod(1000*60)
		if not self._useExternalTimer:
			self.timer = wx.Timer(self, -1)
			self.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)
		self.Bind(wx.EVT_BUTTON, self.OnButton)
		self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
		#self.Reset()

	def GetPeriod(self):
		return self.period

	def SetPeriod(self, period):
		self.period = period

	def Reset(self):
		self.startTime = time.time()
		offColour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
		offColour = self.DarkColour(offColour, 20)
		self._offColours = wx.WHITE, offColour
		self.Refresh()

	#TODO: This does not handle pause time right when the timer is stopped
	# and restarted without being reset
	# Also, a reset does nothing until the test restarts
	def Start(self, reset=False):
		assert reset
#		if reset:
		self.Reset()
		if not self._useExternalTimer:
			self.timer.Start(998)

	def Stop(self):
		if not self._useExternalTimer:
			self.timer.Stop()

	def OnTimer(self, evt):
		if hasattr(self, 'startTime'):
			t = int(round(time.time() - self.startTime))
			self.SetLabel("%d:%02d" % (t // 60, t % 60))
			if t >= self.period:
				self.SetOffColour(wx.YELLOW, 15)
			self.Refresh()
		evt.Skip()

	def OnButton(self, evt):
		self.Reset()
		evt.Skip()

	def OnRightDown(self, evt):
		menu = wx.Menu()
		for item, fct in [("Set Period",	self.OnSetPeriod)]:
#						  ("Reset",			lambda evt: self.Reset()),
#						  ("Start",			lambda evt: self.Start()),
#						  ("Stop",			lambda evt: self.Stop()),
#						 ]:
			id = wx.NewId()
			menu.Append(id, item, item)
			wx.EVT_MENU(menu, id, fct)
		self.PopupMenu(menu)
		menu.Destroy()

	def OnSetPeriod(self, evt):
		n = wx.GetNumberFromUser("Enter period in seconds", "", "Stop Watch",
				self.GetPeriod(), min=1, max=1000*60)
		if n != -1:
			self.SetPeriod(n)

"""
class StatusBar(wx.StatusBar):
	def __init__(self, *args, **kargs):
		wx.StatusBar.__init__(self, *args, **kargs)
		#vColor = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUBAR)
		#self.SetBackgroundColour(vColor)

		self.initColors()
		self.styles = None
		self.foregrounds = None
		self.backgrounds = None
		#TODO: Can this change while running ?
		self.hasGrip = (self.GetWindowStyle() & wx.ST_SIZEGRIP) != 0

		self.Bind(wx.EVT_PAINT, self.onPaint)
		self.Bind(wx.EVT_SYS_COLOUR_CHANGED, self.onSysColorChanged)

	def initColors(self):
		self.mediumShadowPen = wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DSHADOW))
		self.hilightPen = wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DHILIGHT))

	def SetStatusStyles(self, styles):
		#assert styles is None  or  len(styles) == self.GetFieldsCount()
		wx.StatusBar.SetStatusStyles(self, styles)
		self.styles = styles

	def SetStatusForegrounds(self, foregrounds):
		assert foregrounds is None  or  len(foregrounds) == self.GetFieldsCount()
		self.foregrounds = foregrounds

	def SetStatusBackgrounds(self, backgrounds):
		assert backgrounds is None  or  len(backgrounds) == self.GetFieldsCount()
		self.backgrounds = backgrounds

	def onSysColorChanged(self, evt):
		self.InitColors()

	def onPaint(self, evt):
		dc = wx.PaintDC(self)
		self.draw(dc)

	def draw(self, dc):
		dc.Clear()
#		dc.SetTextForeground(wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT))
		for field in range(self.GetFieldsCount()):
			self.drawField(dc, field)
		if self.hasGrip:
			self.drawGrip(dc)

	def drawField(self, dc, field):
		# The last field rectangle ends differently than it does on Win2K, but it is OK
		r = self.GetFieldRect(field)

		style = wx.SB_NORMAL if self.styles == None else self.styles[field]
		if style != wx.SB_FLAT:
			# Right and bottom lines
			dc.SetPen(self.mediumShadowPen if style == wx.SB_RAISED else self.hilightPen)
			dc.DrawLine(r.x + r.width, r.y,              r.x + r.width, r.y + r.height)
			dc.DrawLine(r.x          , r.y + r.height,   r.x + r.width, r.y + r.height)

			# Left and top lines
			dc.SetPen(self.hilightPen if style == wx.SB_RAISED else self.mediumShadowPen)
			dc.DrawLine(r.x,           r.y + r.height,   r.x, r.y)
			dc.DrawLine(r.x,           r.y,              r.x + r.width,  r.y)

		self.drawFieldText(dc, field)

	def drawFieldText(self, dc, field):
		leftMargin = 2

		# Check all this on XP
		r = self.GetFieldRect(field)
		text = self.GetStatusText(field)
		x, y = dc.GetTextExtent(text)
		xPos = r.x + leftMargin
		yPos = int(((r.height - y) // 2 ) + r.y + 0.5)

		dc.SetClippingRegion(r.x, r.y, r.width, r.height)
		if self.backgrounds is not None  and self.backgrounds[field] is not None:
			#TODO: Is there a better way to do this ?
			oldPen = dc.GetPen()
			oldBrush = dc.GetBrush()
			dc.SetBrush(wx.Brush(self.backgrounds[field]))
			dc.DrawRectangle(r.x, r.y, r.x+r.width, r.y + r.height)
			dc.SetBrush(oldBrush)
			dc.SetPen(oldPen)
		if self.foregrounds is None  or  self.foregrounds[field] is None:
			dc.DrawText(text, xPos, yPos)
		else:
			oldForeground = dc.GetTextForeground()
			dc.SetTextForeground(self.foregrounds[field])
			dc.DrawText(text, xPos, yPos)
			dc.SetTextForeground(oldForeground)
		dc.DestroyClippingRegion()

	def drawGrip(self, dc):
		# Draw in the Grip [Not in 2.8.11 code]
		r = self.GetFieldRect(self.GetFieldsCount()- 1)
		#TODO: The values of 25 and 20 here are somewhat arbitrary
		x = r.x + r.width + 25
		y = r.y
		w = 20

		for i in range(3):
			dc.SetPen(self.hilightPen)
			dc.DrawLine(x, y + r.height,  x+w, y + r.height - w)
			x += 2
			dc.SetPen(self.mediumShadowPen)
			dc.DrawLine(x, y + r.height,  x+w, y + r.height - w)
			x += 2

	def GetFieldRect(self, field):
		r = wx.StatusBar.GetFieldRect(self, field)
		#TODO: Why is this needed ? Win2K issue ?
		r.height -= 1
		return r
"""

class StatusBar(wx.StatusBar):
	def __init__(self, *args, **kwargs):
		wx.StatusBar.__init__(self, *args, **kwargs)

		self.overlays = [None]

		self.Bind(wx.EVT_SIZE, self.OnSize)
		self.Bind(wx.EVT_CLOSE, self.OnClose)

	def SetFieldsCount(self, n):
		wx.StatusBar.SetFieldsCount(self, n)
		if n > len(self.overlays):
			self.overlays += [None] * (n - len(self.overlays))
		self.overlays = self.overlays[0:n]
		#print self.overlays

	def SetStatusText(self, text, field=0, foreground=None, background=None):
		if foreground is None  and  background is None:
			self.SetOverlay(field, None)
			wx.StatusBar.SetStatusText(self, text, field)
		else:
			self.SetTextOverlay(field, text, foreground, background)

	def SetOverlay(self, field, widget=None):
		if self.overlays[field] is not None:
			self.overlays[field].Destroy()
		self.overlays[field] = widget
		if widget is not None:
			self.Reposition()
		#print self.overlays

	def SetTextOverlay(self, field, msg, foreground=None, background=None):
		w = wx.StaticText(self, -1, msg)
		if foreground is not None:
			if isinstance(foreground, (str, unicode)):
				foreground = wx.NamedColour(foreground)
			w.SetForegroundColour(foreground)
		if background is not None:
			if isinstance(background, (str, unicode)):
				background = wx.NamedColour(background)
			w.SetBackgroundColour(background)
		self.SetOverlay(field, w)

	def OnClose(self, evt):
		#print 'StatusBar.OnClose'
		#Without this we get wxSize events during the close process that cause problems
		self.Unbind(wx.EVT_SIZE)
		evt.Skip()

	def OnSize(self, evt):
		#print 'StatusBar.OnSize', evt.GetSize()
		self.Reposition()
		evt.Skip()

	def Reposition(self):
		#print 'reposition',
		#TODO: Can we get into a state where self.GetFieldsCount() != len(self.overlays)?
#		for field in range(self.GetFieldsCount()):
#			if self.overlays[field] is not None:
		for field, widget in enumerate(self.overlays):
			#print field,
			if widget is not None:
				r = self.GetFieldRect(field)
				# All these fudge factors are probably XP Theme dependent
				# They are certainly different from 2K to XP
				widget.SetPosition((r.x+4, r.y+2))
				widget.SetSize((r.width-8, r.height-2))
		#print
