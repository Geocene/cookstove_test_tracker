# GenericButton wxPython IMPLEMENTATION
#
# Gary Hubbard.  Heavily modified from Andrea Gavana GradientButton
#
# Andrea Gavana, @ 07 October 2008
# Latest Revision: 07 October 2008, 22.00 GMT
#
#
# TODO List
#
# 1) Anything to do?
#
#
# For all kind of problems, requests of enhancements and bug reports, please
# write to me at:
#
# andrea.gavana@gmail.com
# gavana@kpo.kz
#
# Or, obviously, to the wxPython mailing list!!!
#
#
# End Of Comments
#

"""
Description
===========

GenericButton is another custom-drawn button class which mimics Windows CE mobile
gradient buttons, using a tri-vertex blended gradient plus some ClearType bold
font (best effect with Tahoma Bold). GenericButton supports:

* Triple blended gradient background, with customizable colours;
* Custom colours for the "pressed" state;
* Rounded-corners buttons;
* Text-only or image+text buttons.

And a lot more. Check the demo for an almost complete review of the functionalities.


Supported Platforms
===================

GenericButton has been tested on the following platforms:
  * Windows (Windows XP).


Latest Revision: Andrea Gavana @ 07 October 2008, 22.00 GMT
Version 0.1

"""
from __future__ import absolute_import, division, print_function	#, unicode_literals


import wx


HOVER = 1
CLICK = 2

#TODO: wxPython 2.9:
#	wx.PyCommandEvent -> wx.CommandEvent
#	wx.PyControl -> wx.Control
# Using wx.Control on 2.8 seems to prevent DoGetBestSize from working

# TODO: Code has had bitmap part hacked out.  Perhaps it should be added back.

#TODO: Should this even be a derived type anymore?

class ButtonEvent(wx.PyCommandEvent):
#class ButtonEvent(wx.CommandEvent):
	""" Event sent from the Gradient buttons when the button is activated. """

	def __init__(self, eventType, id):
		"""
		Default class constructor.

		@param eventType: the event type;
		@param id: the event id.
		"""

		wx.PyCommandEvent.__init__(self, eventType, id)
#		wx.CommandEvent.__init__(self, eventType, id)


class GenericButton(wx.PyControl):
#class GenericButton(wx.Control):
	def __init__(self, parent, id=wx.ID_ANY, label="", pos=wx.DefaultPosition,
				 size=wx.DefaultSize, style=wx.NO_BORDER,
				  validator=wx.DefaultValidator, name="GenericButton"):
		"""
		Default class constructor.

		@param parent: the AquaButton parent.
		@param id: the button id;
		@param label: the button text label;
		@param pos: the button position;
		@param size: the button size;
		@param style: the button style (unused);
		@param validator: the validator associated to the button;
		@param name: the button name.
		"""
		wx.PyControl.__init__(self, parent, id, pos, size, style, validator, name)
#		wx.Control.__init__(self, parent, id, pos, size, style, validator, name)

		self.Bind(wx.EVT_SIZE, self.OnSize)
		self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDown)
		self.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)
		self.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeave)
		self.Bind(wx.EVT_ENTER_WINDOW, self.OnMouseEnter)
		self.Bind(wx.EVT_SET_FOCUS, self.OnGainFocus)
		self.Bind(wx.EVT_KILL_FOCUS, self.OnLoseFocus)
		self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
		self.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
		self.Bind(wx.EVT_ERASE_BACKGROUND, lambda evt: None)

		if "__WXMSW__" in wx.PlatformInfo:
			self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDouble)

	def OnSize(self, evt):
		""" Handles the wx.EVT_SIZE event for L{GenericButton}. """

		self.Refresh()
		evt.Skip()

	def OnLeftDown(self, evt):
		""" Handles the wx.EVT_LEFT_DOWN event for L{GenericButton}. """

		#print('GenericButton(%s): OnLeftDown Enabled=%s' %
		#		(self.GetLabel(), self.IsEnabled()))
		if not self.IsEnabled():
			return

		self._mouseAction = CLICK
		self.CaptureMouse()
		self.Refresh()
		evt.Skip()

	def OnLeftDouble(self, evt):
		#print('GenericButton(%s): OnLeftDouble ->' % self.GetLabel())
		self.OnLeftDown(evt)

	def OnLeftUp(self, evt):
		""" Handles the wx.EVT_LEFT_UP event for L{GenericButton}. """

		#print('GenericButton(%s): OnLeftUp Enabled=%r' %
		#		(self.GetLabel(), self.IsEnabled()))
		assert self.HasCapture()
		if not self.IsEnabled() or not self.HasCapture():
			return

		pos = evt.GetPosition()
		rect = self.GetClientRect()

		# At least on MSW I think this always needs to be true
		# It was already tested for at the top of this method anyway
		#if self.HasCapture():
		#	self.ReleaseMouse()
		self.ReleaseMouse()

		if rect.Contains(pos):
			self._mouseAction = HOVER
			self.ButtonNotify()
		else:
			# At least on MSW, I think this has already happened
			assert self._mouseAction == None
			self._mouseAction = None

		self.Refresh()
		evt.Skip()


	def OnMouseEnter(self, evt):
		""" Handles the wx.EVT_ENTER_WINDOW event for L{GenericButton}. """

		#print('GenericButton(%s): OnMouseEnter' % self.GetLabel())
		if not self.IsEnabled():
			return

		self._mouseAction = HOVER
		self.Refresh()
		evt.Skip()


	def OnMouseLeave(self, evt):
		""" Handles the wx.EVT_LEAVE_WINDOW event for L{GenericButton}. """

		#print('GenericButton(%s): OnMouseLeave' % self.GetLabel())
		self._mouseAction = None
		self.Refresh()
		evt.Skip()


	def OnGainFocus(self, evt):
		""" Handles the wx.EVT_SET_FOCUS event for L{GenericButton}. """

		#print('GenericButton(%s): OnGainFocus'% self.GetLabel())
		self._hasFocus = True
		self.Refresh()
		self.Update()
		#Do I need a skip here ?
		evt.Skip()


	def OnLoseFocus(self, evt):
		""" Handles the wx.EVT_KILL_FOCUS event for L{GenericButton}. """

		#print('GenericButton(%s): OnLoseFocus' % self.GetLabel())
		self._hasFocus = False
		self.Refresh()
		self.Update()
		#Do I need a skip here ?
		evt.Skip()


	def OnKeyDown(self, evt):
		""" Handles the wx.EVT_KEY_DOWN event for L{GenericButton}. """

		if self._hasFocus and evt.GetKeyCode() == ord(" "):
			self._mouseAction = HOVER
			self.Refresh()
		evt.Skip()


	def OnKeyUp(self, evt):
		""" Handles the wx.EVT_KEY_UP event for L{GenericButton}. """

		if self._hasFocus and evt.GetKeyCode() == ord(" "):
			self._mouseAction = HOVER
			self.ButtonNotify()
			self.Refresh()
		evt.Skip()

	def SetInitialSize(self, size=None):
		"""
		Given the current font and bezel width settings, calculate
		and set a good size.
		"""

		if size is None:
			size = wx.DefaultSize
		wx.PyControl.SetInitialSize(self, size)
#		wx.Control.SetInitialSize(self, size)

	SetBestSize = SetInitialSize


	def AcceptsFocus(self):
		"""Overridden base class virtual."""

		return self.IsShown() and self.IsEnabled()


	def GetDefaultAttributes(self):
		"""
		Overridden base class virtual.  By default we should use
		the same font/colour attributes as the native Button.
		"""

		return wx.Button.GetClassDefaultAttributes()


	def ShouldInheritColours(self):
		"""
		Overridden base class virtual.  Buttons usually don't inherit
		the parent's colours.
		"""

		return False


	def Enable(self, enable=True):
		""" Enables/disables the button. """

		wx.PyControl.Enable(self, enable)
#		wx.Control.Enable(self, enable)
		self.Refresh()


	def SetForegroundColour(self, colour):
		""" Sets the L{GenericButton} foreground (text) colour. """

		wx.PyControl.SetForegroundColour(self, colour)
#		wx.Control.SetForegroundColour(self, colour)
		self.Refresh()


	def DoGetBestSize(self):
		"""
		Overridden base class virtual.  Determines the best size of the
		button based on the label and bezel size.
		"""

		label = self.GetLabel()
		if not label:
			return wx.Size(112, 48)

		dc = wx.ClientDC(self)
		dc.SetFont(self.GetFont())
		tw, th = dc.GetTextExtent(label)
#		print('DoGetBestSize1',wx.Size(tw, th))

#		bmpWidth = bmpHeight = 0
		# 75+13 = minimum button width
		# 23+3 = minimum button height
		# Note: the Windows User Experience Interaction Guidelines
		# http://msdn.microsoft.com/en-us/library/windows/desktop/dn742402.aspx
		# has 75x23.
		# I determined 5*th//4 as the minimum horizontal space and th//2 as the
		# minimum vertical space empirically.  The later seems right, the former
		# is close, but not perfect.  I should probably be using an average character
		# width, but I don't see how to do that in wx.Widgets.
		retWidth = max(tw+5*th//4, 75+13)
		retHeight = max(th+th//2, 23+3)
#		if self._bitmap:
#			bmpWidth, bmpHeight = self._bitmap.GetWidth()+10, self._bitmap.GetHeight()
#			retWidth += bmpWidth
#			retHeight = max(bmpHeight, retHeight)

		return wx.Size(retWidth, retHeight)


	def SetDefault(self):
		""" Sets the default button. """

		tlw = wx.GetTopLevelParent(self)
		if hasattr(tlw, 'SetDefaultItem'):
			tlw.SetDefaultItem(self)


	def ButtonNotify(self):
		""" Actually sends a wx.EVT_BUTTON event to the listener (if any). """

		#print("GenericButton(%s): ButtonNotify" % self.GetLabel())
		evt = ButtonEvent(wx.wxEVT_COMMAND_BUTTON_CLICKED, self.GetId())
		evt.SetEventObject(self)
		self.GetEventHandler().ProcessEvent(evt)


class Button(GenericButton):
	""" This is the main class implementation of L{GenericButton}. """

	def __init__(self, parent, id=wx.ID_ANY, label="", pos=wx.DefaultPosition,
				 size=wx.DefaultSize, style=wx.NO_BORDER,
				 validator=wx.DefaultValidator, name="Button"):
		"""
		Default class constructor.

		@param parent: the AquaButton parent.
		@param id: the button id;
		@param label: the button text label;
		@param pos: the button position;
		@param size: the button size;
		@param style: the button style (unused);
		@param validator: the validator associated to the button;
		@param name: the button name.
		"""

		GenericButton.__init__(self, parent, id, label, pos, size, style, validator, name)

		self.Bind(wx.EVT_PAINT, self.OnPaint)

		self._mouseAction = None
		self._hasFocus = False

		self.SetLabel(label)
		self.InheritAttributes()
		self.SetInitialSize(size)

		self._penColour   = wx.Colour(0,60,116)		# This matches the Loft computer
		self._hoverColour = wx.Colour(212,212,0)	# For hover inner border
		self._focusColour = wx.Colour(0,192,255)	# For focus inner border

		self._gradient = True

		# No gradient, Empirical kludge to make sort of like Win32 buttons
		self._offColour = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
		self._offColour = self.DarkColour(self._offColour, 20)
		self._onColour  = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)

		# Top and bottom of gradient brush
		# This should be theme dependent somehow
#		self._offColours = wx.WHITE, wx.Colour(214,208,197)
#		self._onColours  = wx.WHITE, wx.Colour(230,230,224)
		self._offColours = wx.WHITE, self._offColour
		self._onColours  = wx.WHITE, self._onColour

	def DarkColour(self, color, percent):
		"""
		Return dark contrast of color. The color returned is from the scale of
		color -> black. The percent determines how dark the color will be.
		Percent = 100 return black, percent = 0 returns color.
		"""

		end_color = wx.BLACK
		rd = end_color.Red()   - color.Red()
		gd = end_color.Green() - color.Green()
		bd = end_color.Blue()   - color.Blue()
		high = 100

		# We take the percent way of the color from color -. white
		i = percent
		r = color.Red()   + ((i*rd*100)//high)//100
		g = color.Green() + ((i*gd*100)//high)//100
		b = color.Blue()  + ((i*bd*100)//high)//100

		return wx.Colour(r, g, b)

##	def LightColour(self, color, percent):
##		"""
##		Return light contrast of color. The color returned is from the scale of
##		color -> white. The percent determines how light the color will be.
##		Percent = 100 return white, percent = 0 returns color.
##		"""
##
##		end_color = wx.WHITE
##		rd = end_color.Red() - color.Red()
##		gd = end_color.Green() - color.Green()
##		bd = end_color.Blue() - color.Blue()
##		high = 100
##
##		# We take the percent way of the color from color -. white
##		i = percent
##		r = color.Red() + ((i*rd*100)//high)//100
##		g = color.Green() + ((i*gd*100)//high)//100
##		b = color.Blue() + ((i*bd*100)//high)//100
##
##		return wx.Colour(r, g, b)

	def OnPaint(self, evt):
		""" Handles the wx.EVT_PAINT event for L{GenericButton}. """
		#print("GenericButton(%s) OnPaint Enable=%d" % (self.GetLabel(), self.Enabled))

		dc = wx.BufferedPaintDC(self)
		gc = wx.GraphicsContext.Create(dc)

		# Fill the entire widget with the parent's background color
		# Note: In Windows 7, it seems to be the buttons background
		bg1 = self.GetParent().GetBackgroundColour()
		bg2 = self.GetBackgroundColour()
#		print(bg1, bg2)
#		dc.SetBackgrounx.Brush(self.GetParent().GetBackgroundColour()))
		dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
		dc.Clear()

		# These fudge factors make it match an XP native button
		x, y, width, height = self.GetClientRect()
		x, y, width, height = x+1, y+1, width-3, height-3

		#capture = wx.Window.GetCapture() == self
		# Capture goes true  at EVT_LEFT_DOWN over the button
		#         goes false at EVT_LEFT_UP no mater where that occurs
		# Toggle  flips      at EVT_LEFT_DOWN over the button followed
		#                    by EVT_LEFT_UP over the button
		# mouseAction=HOVER  after EVT_ENTER
		# mouseAction=CLICK  after EVT_ENTER and then EVT_LEFT_DOWN
		# mouseAction=None   after EVT_LEAVE or EVT_LEFT_UP
		#print('Capture: %5s  Toggle=%5s  MouseAction=%s' %
		#	(capture, self.isToggle, self._mouseAction))

		# Button parts:
		#  Background color: May be gradient filled
		#  Outer boundary: solid line surrounding entire object
		#  Hover line: solid line just inside outer boundary if hovering
		#  Focus line: dotted line just inside hover line if button has focus
		#  What about default button, if it exists?

		#TODO: Should the grayed pen color appear automatically if !enabled?
		#      The value of 150 was empirically determined.
#		penColour = self._penColour if self.Enabled else wx.Colour(150,150,150)
		penColour = wx.Colour(112,112,112) if self.Enabled else wx.Colour(150,150,150)
		pen = wx.Pen(penColour)
		if not self._gradient:
			br = wx.Brush(self.GetFillColour())
		else:
			# These gradient brushes don't seem to work Win32 colours.
			# Probably this is because of gamma correction issues, which Win32
			# which GDI+ supports but wxWindows does not seem to.
			topColour, botColour = self.GetGradientFillColours()
			br = gc.CreateLinearGradientBrush(x, y+1, x, y+height-1,
							topColour, botColour)

		gc.SetPen(pen)
		gc.SetBrush(br)
		gc.DrawPath(self.GetPath(gc, x, y, width, height, 2))

		#print(repr(self.GetLabel()), self._mouseAction, self._hasFocus)

		if self._mouseAction == HOVER:
			self.DrawInnerBorder(gc, self._hoverColour, x, y, width, height)

		# Is part of this the focus issue and part the default button issue?
		# The test for None is so having no focus colour also meens no
		# focus line.  Perhaps we need separate control over this.
		if self._hasFocus  and  self._focusColour is not None:
			gc.SetPen(wx.Pen(self._penColour, 1, wx.DOT))
			gc.StrokePath(self.GetPath(gc, x+2,y+2, width-4,height-4, 2))
			if self._mouseAction != HOVER:
				self.DrawInnerBorder(gc, self._focusColour, x, y, width, height)

		#TODO: Should the foreground color automatically change w/ enable?
		#The value 150 was empirically determined
		#fontColor = self.GetForegroundColour()
		fontColor = self.GetForegroundColour() if self.Enabled else wx.Colour(150,150,150)
		font = gc.CreateFont(self.GetFont(), fontColor)
		gc.SetFont(font)
		label = self.GetLabel()
		tw, th = gc.GetTextExtent(label)
		#print(tw, th, width, height, label)

		shadowOffset = 0
		pos_x = (width-tw)/2 + 3	# GLH added 3 2013.09.20

		#th -= 3 # fudge to match XP w/ default font: GLH changed from 4 2013.09.20
		th -= 2	 # fudget to math Win w/ default fontl GLH changed 2014.07.29
		gc.DrawText(label, pos_x + shadowOffset, (height-th)/2+shadowOffset)

	def DrawInnerBorder(self, gc, colour, x, y, width, height):
		""" Draw a hover or focus inner border """
		if colour is not None:
			gc.SetPen(wx.Pen(colour, 1, wx.SOLID))
			gc.StrokePath(self.GetPath(gc, x+1,y+1, width-2,height-2, 2))

	def GetPath(self, gc, x, y, w, h, r):
		""" Returns a rounded Rectangle GraphicsPath. """

		path = gc.CreatePath()
		path.AddRoundedRectangle(x, y, w, h, r)
		path.CloseSubpath()
		return path

	def GetFillColour(self):
		""" Return the fill color for the button """
		on = self._mouseAction == CLICK
		return self._onColour if on else self._offColour

	def GetGradientFillColours(self):
		on = self._mouseAction == CLICK
		return self._onColours if on else self._offColours

	def SetFocusColour(self, colour):
		self._focusColour = colour
		self.Refresh()

	def SetHoverColour(self, colour):
		self._hoverColour = colour
		self.Refresh()

	def SetOffColour(self, colour, gradient=15):
		#No Gradient
		self._offColour = colour
		#Gradient
		self._offColours = colour, self.DarkColour(colour, gradient)

	def SetOnColour(self, colour, gradient=15):
		#No Gradient
		self._onColour = colour
		#Gradient
		self._onColours = colour, self.DarkColour(colour, gradient)

#TODO:  It is a horrible kludge to need to have timeout= in SetValue here, just to
#		satisify a need in TimedToggleButton.  Alternative would be to repeat a bunch
#		of code from here in TimedToggleButton, to set the value, refresh and generate
#		a notification.


class ToggleButton(Button):
	def __init__(self, parent, id=wx.ID_ANY, label="", pos=wx.DefaultPosition,
				 size=wx.DefaultSize, style=wx.NO_BORDER,
				  validator=wx.DefaultValidator, name="GenericButton"):
		Button.__init__(self, parent, id, label, pos, size, style, validator, name)

		self._isChecked = False

		self.SetOnColour(wx.GREEN, 25)

		# The MS default uses a yellow/green color for hover, blue for focus
		# Using green for the toggle active color leaves the focus window with
		# a blue border, which looks bit funny.  Perhaps I should reverse this
		# pattern, at the cost of being different.
		# Instead, For now, I simply disable them for ToggleButtons
		# Still get dotted focus line, but no hover color
		# A hover color of wx.WHITE also looks OK.

#		self._hoverColour = wx.Colour(0,192,255)	# For hover inner border
#		self._focusColour = wx.Colour(212,212,0)	# For focus inner border
		self._focusColour  = None
		self._hoverColour  = None

		self.Bind(wx.EVT_BUTTON, self.OnButton)

	def GetFillColour(self):
		on = (self._mouseAction == CLICK) != self._isChecked
		return self._onColour if on else self._offColour

	def GetGradientFillColours(self):
		on = (self._mouseAction == CLICK) != self._isChecked
		return self._onColours if on else self._offColours

	def GetValue(self):
		return self._isChecked

	def SetValue(self, value, timeout=None):
		#print('ToggleButton(%s): SetValue(%s)' % (self.GetLabel(),value))
		self._isChecked = bool(value)
		self.ToggleButtonNotify(timeout)
		self.Refresh()

	def OnButton(self, evt):
		#print('ToggleButton(%s): OnToggleButton' % self.GetLabel())
		self.SetValue(not self._isChecked)
		#TODO: Should I pass this through? wx.ToggleButton does not seem to.
		#evt.Skip()

	def ToggleButtonNotify(self, timeout):
		""" Actually sends a wx.EVT_TOGGLEBUTTON event to the listener (if any). """

		#print('ToggleButton(%s): ToggleButtonNotify %s' % (self.GetLabel(), self._isChecked))
		evt = ButtonEvent(wx.wxEVT_COMMAND_TOGGLEBUTTON_CLICKED, self.GetId())
		evt.SetEventObject(self)
		evt.SetInt(int(self._isChecked))
		evt._timeout = timeout
		self.GetEventHandler().ProcessEvent(evt)


#TODO: What to do if we call Enable(False) when the TimedToggleButton is active
#		and the the timer is running? Right now, you might make it impossible to
#		turn off.


class TimedToggleButton(ToggleButton):
	def __init__(self, parent, id=wx.ID_ANY, label='', pos=wx.DefaultPosition,
				 size=wx.DefaultSize, style=wx.NO_BORDER,
				 validator=wx.DefaultValidator, name='TimedToggleButton'):
		ToggleButton.__init__(self, parent, id, label, pos, size, style, validator, name)

		self.SetupAutoToggle(0, 0, 0)

		self.timer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.OnTimer)
		self.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
		self.Bind(wx.EVT_TOGGLEBUTTON, self.OnToggleButton)

	def SetupAutoToggle(self, autoOffDelay, minDelay, maxDelay):
		""" Setup automatic shutoffs for the button. """

		self._autoOffDelay = autoOffDelay
		self._minDelay    = minDelay
		self._maxDelay    = maxDelay

	def GetDefaultTimeout(self):
		return self._autoOffDelay

	def OnRightDown(self, evt):
		if self._maxDelay != 0:
			while 1:
				msg = "Enter time in seconds to turn relay off at.\n" + \
					  "               Min=%g  Max=%g" % (self._minDelay, self._maxDelay)
				s = wx.GetTextFromUser(msg, "Auto-Off relay", str(self._autoOffDelay))
				if s == "":
					break
				try:
					v = float(s)
				except ValueError as e:
					continue
				if self._minDelay <= v <= self._maxDelay:
					self._autoOffDelay = v
					break
		evt.Skip()

	def SetValue(self, value, timeout=None):
		#print("TimedToggleButton.SetValue", value, timeout)
		ToggleButton.SetValue(self, value, timeout)

	def OnToggleButton(self, evt):
		#print('TimedToggleButton(%s): OnToggleButton' % self.GetLabel())
		self.SetupTimer(evt._timeout)
		evt.Skip()

	def SetupTimer(self, timeout=None):
		if timeout is None:
			timeout = self._autoOffDelay
		if not self._isChecked:
			self.timer.Stop()
		elif timeout > 0:
			self.timer.Start(timeout*1000, oneShot=True)

	def OnTimer(self, evt):
		if self._isChecked:
			self.SetValue(False)


if __name__ == "__main__":
	import numpy as np

	class MyFrame(wx.Frame):
		def __init__(self, parent):
			wx.Frame.__init__(self, parent, -1, "Button Test")

#			font = wx.Font(2,
#						wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL,
#						faceName='Arial')
#			self.SetFont(font)

			button1a = wx.Button(self, -1, "wxB")
			button1b = Button(self, -1, "Bg")
			button2a = wx.ToggleButton(self, -1, "wxTBg")
			button2b = ToggleButton(self, -1, "TB")
			button3a = wx.ToggleButton(self, -1, "wxTB")
			button3b = ToggleButton(self, -1, "TB")
			button4a = wx.ToggleButton(self, -1, "wxTB")
			button4b = TimedToggleButton(self, -1, "TB")
			button4b.SetupAutoToggle(1,0,10)

			buttonList = [button1a, button1b, button2a, button2b,
						   button3a, button3b, button4a, button4b]

			print(self.GetFont().GetNativeFontInfo())

			dc = wx.WindowDC(self)
			chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
			for i, button in enumerate(buttonList):
				font = wx.Font(8+2*(i//2),
							wx.FONTFAMILY_ROMAN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL,
							faceName='Segoe UI')

				dc.SetFont(font)
				te = dc.GetTextExtent(chars)
				#print(i, font.GetNativeFontInfo(), font.GetPointSize(), font.GetPixelSize(), te[0]/len(chars), te[1])

				button.SetFont(font)
#				if button.GetLabel().startswith('wx'):
#					button.SetLabel("wxButton123 " + "abc"*i)

#			buttonList = [button1a, button2a, button1b, button2b,
#						   button3a, button4a, button3b, button4b]

			sizer = wx.FlexGridSizer(rows=4, cols=2, hgap=0, vgap=0)
			for b in buttonList:
				sizer.Add(b)
			self.SetSizerAndFit(sizer)

			#for b in buttonList:
			#	print("%-20s %s" % (b.GetLabel(), b.GetSize()))

	#		for b in buttonList:
	#			b.Enable(False)

			self.Bind(wx.EVT_BUTTON, self.OnButton)
			self.Bind(wx.EVT_TOGGLEBUTTON, self.OnToggleButton)
			wx.CallLater(1000, button4b.SetValue, 1, 5)
			wx.CallLater(1, self.PrintSizes, buttonList)

		def PrintSizes(self, buttonList):
			tw = []
			bw = []
			font = self.GetFont()
			dc = wx.WindowDC(self)
			#dc.SetFont(font)
			for b in buttonList:
				dc.SetFont(b.GetFont())
				s = b.GetLabel()
				te = dc.GetTextExtent(s)
				bs = b.GetSize()
				print("%-10s %s %s" % (s, te, bs))
				if s.startswith('w'):
					tw.append(te[1])
					bw.append(bs[1])
			print(tw, bw)
			print(np.polyfit(bw, tw, 1))

		def OnButton(self, evt):
			button = evt.GetEventObject()
			#print("OnButton %s" % (button.GetLabel()))

		def OnToggleButton(self, evt):
			button = evt.GetEventObject()
			#print("OnToggleButton %s %d" % (button.GetLabel(), button.GetValue()))


	class MyApp(wx.App):
		def OnInit(self):
			self.frame = MyFrame(None)
			self.frame.Show()
			return True

	app = MyApp(False)
	app.MainLoop()
