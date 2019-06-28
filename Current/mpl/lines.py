from __future__ import (absolute_import, print_function, division, unicode_literals)

import numpy as np

import wx
from .renderer import mapColor

class Line2D():
	def __init__(self, x, y, color='k', linewidth=0):
		self.x, self.y, self.color, self.lineWidth = x, y, color, linewidth

	def draw(self, axes, dc):
		newPen = wx.Pen(mapColor(self.color), self.lineWidth, wx.SOLID)
		X, Y, W, H = axes.getGeometry()
		with wx.DCPenChanger(dc, newPen), wx.DCClipper(dc, X, Y, W, H):
			points=[]
			for x, y in zip(self.x, self.y):
				x = X + W * axes.xaxis.scaleValue(x)
				y = Y + H * (1-axes.yaxis.scaleValue(y))
				#Must break line segments at NaN or Inf.
				#TODO: Turn this into a PolyPolyline
				if np.isnan(x) or np.isnan(y) or np.isinf(x) or np.isinf(y):
					if len(points) > 0:
						dc.DrawLines(points)
						points = []
				else:
					points.append((x,y))
			if len(points) > 0:
				dc.DrawLines(points)

