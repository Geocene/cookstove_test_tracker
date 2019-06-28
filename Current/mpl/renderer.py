from __future__ import (absolute_import, print_function, division, unicode_literals)

import numpy as np

import wx

#from .axes import Axes, Axis, XAxis, YAxis


class Bar():
	def __init__(self, x,y, width, align, linewidth, fillColor):
		self.x, self.y, self.width = x, y, width
		self.align = align
		self.lineWidth, self.fillColor = linewidth, fillColor

	def draw(self, axes, dc):
		newPen = wx.Pen(wx.BLACK, self.lineWidth, wx.SOLID)
		newBrush = wx.Brush(mapColor(self.fillColor), wx.SOLID)
		with wx.DCPenChanger(dc, newPen), wx.DCBrushChanger(dc, newBrush):
			yMin = axes.yaxis.minVal
			X, Y, W, H = axes.getGeometry()
			#TODO: Is this round code the best way to go
			for x, y, w in zip(self.x, self.y, self.width):
				y = max(y, yMin)
				x1, x2 = W * axes.xaxis.scaleValue(np.array([x, x+w]))
				y1, y2 = H * axes.yaxis.scaleValue(np.array([yMin,y]))
				x1, x2, y2 = round(x1), round(x2), round(y2)
				#TODO: Verify the +1 here
				dc.DrawRectangle(X+x1, Y+(H-y2), x2-x1+1, y2+1)


def mapColor(mplColor):
		if len(mplColor) == 1:
			colors = {'b':wx.BLUE, 'g':wx.GREEN, 'r': wx.RED, 'c':wx.CYAN,
					'm':wx.TheColourDatabase.Find('magenta'),
					#wx.YELLOW should be there
					'y':wx.TheColourDatabase.Find('yellow'),
					'k':wx.BLACK, 'w':wx.WHITE}
			return colors[mplColor]
		elif mplColor[0] == '#':
			v = int(mplColor[1:], 16)
			return wx.Colour((v >> 16) & 0xff, (v >> 8) & 0xff, v & 0xff)
		else:
			assert("Unknown color: %s" % mplColor)
