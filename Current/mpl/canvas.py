from __future__ import (absolute_import, print_function, division, unicode_literals)

import wx

class FigureCanvas(wx.Window):
	def __init__(self, parent, id, figure):
		wx.Window.__init__(self, parent, id)
		self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
		self.figure = figure
		self.figure.canvas = self

		self.Bind(wx.EVT_PAINT, self.OnPaint)
		self.Bind(wx.EVT_SIZE, self.OnSize)

	def draw(self):
		self.Refresh()

	def OnSize(self, evt):
		self.Refresh()

	def OnPaint(self, evt):
		dc = wx.AutoBufferedPaintDC(self)
		#This is the way to set the background colour w/AutoBufferedPaintDC
		dc.SetBackground(wx.Brush(wx.Colour(192,192,192)))
		dc.Clear()
		x, y, w, h = self.GetClientRect()
		self.figure.setGeometry(x, y, w, h)
		self.figure.draw(dc)
