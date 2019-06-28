from __future__ import absolute_import, print_function, division, unicode_literals

import numpy as np

import wx

from . import ticker
from . import cm

from . import lines
from .renderer import Bar, mapColor

#TODO: Decide whether the maxmum value appears at the box size-1, or the box size.
# currently things are inconsistent
class Axes():
	def __init__(self, figure, nRows, nCols, n):
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
		self._legend = []

	def grid(self, b, which='both', axis='both', **kwargs):
		assert axis in ('x', 'y', 'both')
		if axis == 'both':
			self.xaxis.grid(b, which, **kwargs)
			self.yaxis.grid(b, which, **kwargs)
		elif axis == 'x':
			self.xaxis.grid(b, which, **kwargs)
		else:
			self.yaxis.grid(b, which, **kwargs)

	def get_figure(self):
		return self.figure

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

	def legend(self, lines, labels):
		self._legend = (lines, labels)

	def plot(self, x, y, **kwargs):
		self.curves.append(lines.Line2D(x, y, **kwargs))

	def bar(self, x, y, width, align, linewidth, color, bottom):
		self.curves.append(Bar(x, y, width, align, linewidth, color))

	def imshow(self, A, extent=None, cmap=None, interpolation='bilinear', aspect=None, vmin=None, vmax=None, norm=None):
		if vmin is None: vmin = A.min()
		if vmax is None: vmax = A.max()
		if extent is not None:
			self.set_xlim(extent[0], extent[1])
			self.set_ylim(extent[2], extent[3])

		h, w = A.shape
		#Invert top to bottom if necessary
		#if self.yaxis.minVal < self.yaxis.maxVal:
		#	A = A[::-1,:]

		if norm is not None:
			A = norm.Normalize(A, scale=255)
		else:
			A = A - vmin
			A *= 255 / (vmax - vmin)
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
			for image, interpolation in self.images:
				#The x+1,y+1 and w-1, h-1 are draw the image inside the perimeter
				#rectangle, rather than covering it.
				x, y, w, h = self.getGeometry()
				iq = wx.IMAGE_QUALITY_NORMAL if interpolation == 'none' else wx.IMAGE_QUALITY_HIGH
				im = image.Scale(w-1,h-1, iq)
				bmp = wx.BitmapFromImage(im)
				dc.DrawBitmap(bmp, x+1, y+1)
			for axis in [self.xaxis, self.yaxis]:
				axis.draw_ticks(dc)
			for curve in self.curves:
				curve.draw(self, dc)
			if self._legend != []:
				self.draw_legend(dc)
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

	def draw_legend(self, dc):
		lines, labels = self._legend
		if len(lines) == 0:
			return

		lineLength = 25
		wLeft, wGap, wRight = 10, 15, 10
		hTop, hGap, hBottom =  3,  0,  3

		wMax = 0
		for label in labels:
			wt, ht = dc.GetTextExtent(label)
			wMax = max(wt, wMax)
		wTotal = wLeft + lineLength + wGap + wMax + wRight
		hTotal = hTop + (ht+hGap)*len(labels) - hGap + hBottom

		X, Y, W, H = self.getGeometry()
		x, y, w, h = X + W - wTotal-7, Y+7, wTotal, hTotal

		lineWidth = 1
		pen = wx.Pen(wx.BLACK, lineWidth, wx.SOLID)
		with wx.DCPenChanger(dc, pen):
			dc.DrawRoundedRectangle(x, y, w, h, 5)

		y += hTop
		for line, label in zip(lines,labels):
			#wt, ht = dc.GetTextExtent(label)
			pen = wx.Pen(mapColor(line.color), line.lineWidth, wx.SOLID)
			pen.SetCap(wx.CAP_BUTT)
			with wx.DCPenChanger(dc,pen):
				dc.DrawLine(x + wLeft, y+ht/2, x+wLeft+lineLength, y+ht/2)
			dc.DrawText(label, x+wLeft+lineLength+wGap, y)
			y += ht + hGap

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
						   'minor' : {'length':  5, 'width': 1},
						   'labelbottom' : 'on',
						   'labeltop' : 'off'}

		self.tickColor = wx.BLACK
		self.tickStyle = wx.PENSTYLE_SOLID
		self.gridColor = wx.LIGHT_GREY
		self.gridStyle = wx.PENSTYLE_SOLID

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
		self.majorLocator.set_axis(self)

	def set_minor_locator(self, locator):
		self.minorLocator = locator
		self.minorLocator.set_axis(self)

	def set_major_formatter(self, formatter):
		self.majorFormatter = formatter
		self.majorFormatter.set_axis(self)

	def set_minor_formatter(self, formatter):
		self.minorFormatter = formatter
		self.minorFormatter.set_axis(self)

	def set_tick_params(self, labelbottom, labeltop):
		self.tick_parms['labelbottom'] = labelbottom
		self.tick_parms['labeltop'] = labeltop

	def scaleValue(self, v):
		if self.scale == 'linear':
			return (v - self.minVal) / (self.maxVal - self.minVal)
		else:
			#TODO: How does this happen?
			#TODO: Why is this called on a point by point basis, vs a ndarray?
			#if v <= 0: return 0
			return np.log((v / self.minVal)) / np.log((self.maxVal / self.minVal))

	def draw_ticks(self, dc):
		majorTicks = self.majorLocator()
		minorTicks = self.minorLocator()
		wMax2, hMax2 = self.draw_ticks1(dc, 'minor', minorTicks, majorTicks,
								self.minorFormatter)
		wMax1, hMax1 = self.draw_ticks1(dc, 'major', majorTicks, [],
								self.majorFormatter)
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

	#TODO: Separate out the label_position and tick_parms['labeltop' stuff
	def draw_ticks1(self, dc, which, tickLocs, skipLocs, formatter):
		tickWidth = self.tick_parms[which]['width']
		tickLength = self.tick_parms[which]['length']
		tickPen = wx.Pen(self.tickColor, tickWidth, self.tickStyle)
		gridPen = wx.Pen(self.gridColor, 0, self.gridStyle)
		with wx.DCPenChanger(dc, tickPen):
			x0, y0, W, H = self.axes.getGeometry()
			wMax, hMax = 0,0
			formatter.set_locs(tickLocs)
			for i, tickValue in enumerate(tickLocs):
				#Real matplotlib sometimes returns tick_values outside the view range
				if not self.minVal <= tickValue <= self.maxVal:
					continue
				x = x0 + self.scaleValue(tickValue) * W;
				#Don't draw tick at box boundaries, or on other set of ticks
				skipTick = (tickValue in skipLocs or
							np.isclose(tickValue, self.minVal)  or
							np.isclose(tickValue, self.maxVal))
				if not skipTick:
					#if self.grid_parms[which]:
					#	dc.DrawLine(x, y0+H, x, y0)
					#else:
					if self.grid_parms[which]:
						with wx.DCPenChanger(dc, gridPen):
							dc.DrawLine(x, y0+H, x, y0)
					dc.DrawLine(x, y0+H, x, y0+H-tickLength)
					dc.DrawLine(x, y0, x, y0+tickLength)

				s = formatter(tickValue, i)
				if s is not None:
					w, h = dc.GetTextExtent(s)
#					y = y0+H+2 if self.label_position == 'bottom' else y0-h-2
					y = y0+H+2 if self.tick_parms['labeltop'] != 'on' else y0-h-2
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

	def draw_ticks1(self, dc, which, tickLocs, skipLocs, formatter):
		tickWidth = self.tick_parms[which]['width']
		tickLength = self.tick_parms[which]['length']
		tickPen = wx.Pen(self.tickColor, tickWidth, self.tickStyle)
		gridPen = wx.Pen(self.gridColor, 0, self.gridStyle)
		with wx.DCPenChanger(dc, tickPen):
			x0, y0, W, H = self.axes.getGeometry()
			formatter.set_locs(tickLocs)
			wMax, hMax = 0, 0
			for i,tickValue in enumerate(tickLocs):
				#Real matplotlib sometimes returns tick_values outside the view range
				if not self.minVal <= tickValue <= self.maxVal:
					continue
				y = y0 + (1-self.scaleValue(tickValue)) * H
				#Don't draw tick at box boundaries, or on other set of ticks
				skipTick = (tickValue in skipLocs or
							np.isclose(tickValue, self.minVal)  or
							np.isclose(tickValue, self.maxVal))
				if not skipTick:
#					if self.grid_parms[which]:
#						dc.DrawLine(x0, y, x0+W, y)
#					else:
					if self.grid_parms[which]:
						with wx.DCPenChanger(dc, gridPen):
							dc.DrawLine(x0, y, x0+W, y)
					dc.DrawLine(x0, y, x0+tickLength, y)
					dc.DrawLine(x0+W-tickLength, y, x0+W, y)

				s = formatter(tickValue,i)
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
