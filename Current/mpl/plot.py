from __future__ import (absolute_import, division, print_function, unicode_literals)

#import numpy as np

#import wx

from .axes import Axes, Axis, XAxis, YAxis
from .renderer import Bar



"""
#import ticker
#import cm
from . import ticker
from . import cm

#TODO: Decide whether the maxmum value appears at the box size-1, or the box size.
# currently things are inconsistent
class Axes():
	def __init__(self, figure, nRows, nCols, n):
		#Added to allow software to work in BLDG70
		self.name = None
		self.figure = figure
		self.subplot_info = (nRows, nCols, n)
		self.xaxis = XAxis(self)
		self.yaxis = YAxis(self)
		self.clear()

	def clear(self):
		self.title = None
		self.xaxis.clear()
		self.yaxis.clear()
		self.curves = []
		self.images = []

	def grid(self, b, which='both', axis='both', **kwargs):
		assert axis in ('x', 'y', 'both')
		if axis == 'both':
			self.xaxis.grid(b, which, **kwargs)
			self.yaxis.grid(b, which, **kwargs)
		elif axis == 'x':
			self.xaxis.grid(b, which, **kwargs)
		else:
			self.yaxis.grid(b, which, **kwargs)

	def set_xscale(self, xScale):
		self.xaxis.set_scale(xScale)

	def set_yscale(self, xScale):
		self.yaxis.set_scale(xScale)

	def set_xlim(self, xMin=None, xMax=None, auto=False):
		self.xaxis.set_limits(xMin, xMax, auto)

	def set_ylim(self, yMin=None, yMax=None, auto=False):
		self.yaxis.set_limits(yMin, yMax, auto)

	def set_xlabel(self, label):
		self.xaxis.set_label(label)

	def set_ylabel(self, label):
		self.yaxis.set_label(label)

	def set_title(self, title):
		self.title = title

	def tick_params(self, axisName, length, width, which):
		#TODO Finish this
		assert axisName == 'both'
		for ax in [self.xaxis, self.yaxis]:
			ax.tick_parms[which]['length'] = length
			ax.tick_parms[which]['width']  = width

	def plot(self, x, y, **kwargs):
		self.curves.append(Line2D(self, x, y, **kwargs))

	def bar(self, x, y, width, align, linewidth, color, bottom):
		self.curves.append(Bar(self, x, y, width, align, linewidth, color))

	def imshow(self, A, cmap=None, interpolation=None, aspect=None, vmin=None, vmax=None):
		if vmin is None: vmin = A.min()
		if vmax is None: vmax = A.max()
		h, w = A.shape

		A = A - vmin
		A *= 128 / (vmax - vmin)
		A = A.astype(np.uint8)

		array = np.empty((h, w, 3), dtype=np.uint8)
		for color in range(3):
			np.take(cm.colorMap[:,color], A, out=array[:,:,color])

		#I think ImagefromBuffer is safe here, but it might not be.
		#It would be required that wxPython makes a reference to the buffer.
		#There does seem to be.  In fact, there are two references to
		#im = wx.ImageFromData(w, h, array)
		im = wx.ImageFromBuffer(w, h, array)
		self.images.append((im, interpolation))
		del array

	def setGeometry(self, x, y, w, h):
		self.x, self.y, self.w, self.h = int(x), int(y), int(w), int(h)
		#print("ax geom", self.x, self.y, self.w, self.h)

	def getGeometry(self):
		return self.x, self.y, self.w, self.h

#	def transAxes(self, points):
#		x0, y0, W, H = self.axes.getGeometry()
#		points = np.array(points):
#		if len(points.shape) == 1:
#			points.shape = (2,-1)
#		points[0:] = x0 + W * points[

	def draw(self, dc):
#		font = wx.Font(12, wx.FONTFAMILY_SWISS,
#				wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False,
#				"Arial")
		font = wx.Font(13, wx.FONTFAMILY_SWISS,
				wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False,
				"Arial Narrow")
		with wx.DCFontChanger(dc, font):
			self.draw_box(dc)
			for axis in [self.xaxis, self.yaxis]:
				axis.draw_ticks(dc)
			for image, interpolation in self.images:
				x, y, w, h = self.getGeometry()
				iq = wx.IMAGE_QUALITY_NORMAL if interpolation == 'none' else wx.IMAGE_QUALITY_HIGH
				im = image.Scale(w,h, iq)
				bmp = wx.BitmapFromImage(im)
				dc.DrawBitmap(bmp, x, y)
			for curve in self.curves:
				curve.draw(dc)
			self.draw_title(dc)

	def draw_box(self, dc):
		x0, y0, w, h = self.getGeometry()

		# Draw the background & surrounding box
		# TODO: There is a rounding issue somehow that becomes obvious
		#       when the box linewidth is not set to 1.  The second choice below
		#       on the DrawRectangle command makes things look OK, but might
		#       still be incorrect.  That version draws the box outside the
		#       limiting tick lines
		lineWidth = 1
		pen = wx.Pen(wx.BLACK, lineWidth, wx.SOLID)
		pen.SetJoin(wx.JOIN_MITER)
		with wx.DCPenChanger(dc, pen): #, wx.DCBrushChanger(self._backgroundBrush):
			#dc.DrawRectangle(x0-lineWidth//2,y0-lineWidth//2, w+lineWidth-1,h+lineWidth-1)
			dc.DrawRectangle(x0-lineWidth//2,y0-lineWidth//2, w+lineWidth,h+lineWidth)
			#dc.DrawRectangle(x0-lineWidth,y0-lineWidth, w+2*lineWidth,h+2*lineWidth)

		#for i in range(0,10):
		#	dc.DrawPoint(x0+i*2, y0+i*2)
		#
		#for i in range(0,10):
		#	dc.DrawPoint(x0+w-i*2, y0+h-i*2)

	def draw_title(self, dc):
		if self.title is not None:
			X, Y, W, H = self.getGeometry()
			w, h = dc.GetTextExtent(self.title)
			dc.DrawText(self.title, X + (W-w)/2, Y-h-2)


class Axis():
	def __init__(self, axes):
		self.axes = axes
		self.clear()

	def clear(self):
		self.minVal = self.maxVal = None
		self.auto = False
		self.scale = 'linear'
		self.label = None
		self.grid_parms = {'major':False, 'minor':False}
		self.set_major_locator(ticker.AutoLocator())
		self.set_major_formatter(ticker.ScalarFormatter())
		self.set_minor_locator(ticker.NullLocator())
		self.set_minor_formatter(ticker.NullFormatter())
		self.tick_parms = {'major' : {'length': 10, 'width': 1},
						   'minor' : {'length':  5, 'width': 1}}

	def set_label(self, label):
		self.label = label

	def set_scale(self, scale):
		self.scale = scale
		if scale == 'linear':
			self.set_major_locator(ticker.AutoLocator())
			self.set_major_formatter(ticker.ScalarFormatter())
			self.set_minor_locator(ticker.NullLocator())
			self.set_minor_formatter(ticker.NullFormatter())
		elif scale == 'log':
			self.base = 10
			self.subs = None
			self.set_major_locator(ticker.LogLocator(self.base))
			self.set_major_formatter(ticker.LogFormatterMathtext())
			self.set_minor_locator(ticker.LogLocator(self.base, self.subs))
			self.set_minor_formatter(ticker.NullFormatter())

	def grid(self, b, which='both', **kwargs):
		assert which in ('both', 'major', 'minor')
		if which == 'both':
			self.grid_parms['major'] = b
			self.grid_parms['minor'] = b
		else:
			self.grid_parms[which] = b

	def set_limits(self, minVal=None, maxVal=None, auto=False):
		self.minVal = minVal
		self.maxVal = maxVal
		self.auto   = auto

	def get_view_interval(self):
		return self.minVal, self.maxVal

	def set_major_locator(self, locator):
		self.majorLocator = locator
		#Added to allow software to work in Bldg70
		self.majorLocator.set_axis(self)

	def set_minor_locator(self, locator):
		self.minorLocator = locator
		#Added to allow software to work in Bldg70
		self.minorLocator.set_axis(self)

	def set_major_formatter(self, formatter):
		self.majorFormatter = formatter
		self.majorFormatter.set_axis(self)

	def set_minor_formatter(self, formatter):
		self.minorFormatter = formatter
		self.minorFormatter.set_axis(self)

	def scaleValue(self, v):
		if self.scale == 'linear':
			return (v - self.minVal) / (self.maxVal - self.minVal)
		else:
			return np.log((v / self.minVal)) / np.log((self.maxVal / self.minVal))

	def draw_ticks(self, dc):
		wMax1, hMax1 = self.draw_ticks1(dc, 'major',
								self.majorLocator, self.majorFormatter,
								[])
		wMax2, hMax2 = self.draw_ticks1(dc, 'minor',
								self.minorLocator, self.minorFormatter,
								self.majorLocator())
		self.draw_label(dc, self.label, max(wMax1, wMax2), max(hMax1, hMax2))


class XAxis(Axis):
	name = 'x'

	def __init__(self, axes):
		Axis.__init__(self, axes)
		self.clear()

	def clear(self):
		Axis.clear(self)
		self.label_position = 'bottom'

	def set_label_position(self, pos):
		self.label_position = pos

	def draw_ticks1(self, dc, which, locator, formatter, exclude):
		lineWidth = self.tick_parms[which]['width']
		#lineColor = wx.Colour(128,128,128) if self.grid_parms[which] else wx.BLACK
		lineColor = wx.BLACK
		tickLength = self.tick_parms[which]['length']
		newPen = wx.Pen(lineColor, lineWidth, wx.SOLID)
		with wx.DCPenChanger(dc, newPen):
			x0, y0, W, H = self.axes.getGeometry()
			wMax, hMax = 0,0
			#Changed to allow software to run in BLDG70
	#		tickValues = locator.tick_values(self.minVal, self.maxVal)
			tickValues = locator()
			formatter.set_locs(tickValues)
			for tickValue in tickValues:
				#Real matplotlib sometimes returns tick_values outside the view range
				if not self.minVal <= tickValue <= self.maxVal:
					continue
				x = x0 + self.scaleValue(tickValue) * W;
				#Avoid drawing at box edges.
				#TODO: Improve this test
				if (not tickValue in exclude  and  \
						abs(tickValue-self.minVal) > 1e-5  and  abs(tickValue-self.maxVal) > 1e-5):
					if self.grid_parms[which]:
						dc.DrawLine(x, y0+H, x, y0)
					else:
						dc.DrawLine(x, y0+H, x, y0+H-tickLength)
						dc.DrawLine(x, y0, x, y0+tickLength)

				s = formatter(tickValue)
				if s is not None:
					w, h = dc.GetTextExtent(s)
					y = y0+H+2 if self.label_position == 'bottom' else y0-h-2
					dc.DrawText(s, x-w/2, y)
					wMax, hMax = max(w, wMax), max(h, hMax)
		return wMax, hMax

	def draw_label(self, dc, label, wMax, hMax):
		if self.label is not None:
			x0, y0, W, H = self.axes.getGeometry()
			w, h = dc.GetTextExtent(self.label)
			y = y0+H+hMax+2 if self.label_position == 'bottom' else y0-h-hMax-5
			dc.DrawText(self.label, x0+(W-w)/2, y)


class YAxis(Axis):
	name = 'y'

	def __init__(self, axes):
		Axis.__init__(self, axes)
		self.clear()

	def clear(self):
		Axis.clear(self)
		self.label_position = 'left'

	def set_label_position(self, pos):
		self.label_position = pos

	def draw_ticks1(self, dc, which, locator, formatter, exclude):
		lineWidth = self.tick_parms[which]['width']
		#lineColor = wx.Colour(128,128,128) if self.grid_parms[which] else wx.BLACK
		lineColor = wx.BLACK
		tickLength = self.tick_parms[which]['length']
		newPen = wx.Pen(lineColor, lineWidth, wx.SOLID)
		with wx.DCPenChanger(dc, newPen):
			x0, y0, W, H = self.axes.getGeometry()
			#Changed to allow software to run in BLDG70
			#tickValues = locator.tick_values(self.minVal, self.maxVal)
			tickValues = locator()
			formatter.set_locs(tickValues)
			wMax, hMax = 0, 0
			for tickValue in tickValues:
				#Real matplotlib sometimes returns tick_values outside the view range
				if not self.minVal <= tickValue <= self.maxVal:
					continue
				y = y0 + (1-self.scaleValue(tickValue)) * H
				#Avoid drawing at box edges.
				#TODO: Improve this test
				if (not tickValue in exclude  and
						abs(tickValue-self.minVal) > 1e-5  and  abs(tickValue-self.maxVal) > 1e-5):
					if self.grid_parms[which]:
						dc.DrawLine(x0, y, x0+W, y)
					else:
						dc.DrawLine(x0, y, x0+tickLength, y)
						dc.DrawLine(x0+W-tickLength, y, x0+W, y)

				s = formatter(tickValue)
				if s is not None:
					w, h = dc.GetTextExtent(s)
					dc.DrawText(s, x0-w-3, y-h/2)
					wMax, hMax = max(w, wMax), max(h, hMax)
		return wMax, hMax

	def draw_label(self, dc, label, wMax, hMax):
		if self.label is not None:
			x0, y0, W, H = self.axes.getGeometry()
			w, h = dc.GetTextExtent(self.label)
			dc.DrawRotatedText(self.label, x0-wMax-h-5, y0+(H+w)/2, 90)


class Line2D():
	def __init__(self, axes, x, y, color='k', linewidth=0):
		self.axes = axes
		self.x, self.y, self.color, self.lineWidth = x, y, color, linewidth

	def draw(self, dc):
		newPen = wx.Pen(mapColor(self.color), self.lineWidth, wx.SOLID)
		X, Y, W, H = self.axes.getGeometry()
		with wx.DCPenChanger(dc, newPen), wx.DCClipper(dc, X, Y, W, H):
			points=[]
			for x, y in zip(self.x, self.y):
				x = X + W * self.axes.xaxis.scaleValue(x)
				y = Y + H * (1-self.axes.yaxis.scaleValue(y))
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


class Bar():
	def __init__(self, axes, x,y, width, align, linewidth, fillColor):
		self.axes = axes
		self.x, self.y, self.width = x, y, width
		self.align = align
		self.lineWidth, self.fillColor = linewidth, fillColor

	def draw(self, dc):
		newPen = wx.Pen(wx.BLACK, self.lineWidth, wx.SOLID)
		newBrush = wx.Brush(mapColor(self.fillColor), wx.SOLID)
		with wx.DCPenChanger(dc, newPen), wx.DCBrushChanger(dc, newBrush):
			yMin = self.axes.yaxis.minVal
			X, Y, W, H = self.axes.getGeometry()
			#TODO: Is this round code the best way to go
			for x, y, w in zip(self.x, self.y, self.width):
				y = max(y, yMin)
				x1, x2 = W * self.axes.xaxis.scaleValue(np.array([x, x+w]))
				y1, y2 = H * self.axes.yaxis.scaleValue(np.array([yMin,y]))
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
"""