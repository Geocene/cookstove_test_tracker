from __future__ import absolute_import, division, print_function	#, unicode_literals
"""
Trend.py

Class encapsulatating a trend object.

Note, Under Microsoft Winddows (at least), this object must be contained
in a wxPanel rather than a wxFrame it to get an initial wx.EVT_SIZE event,
which is the reason for the funny try: s.self except: block in OnPaint.
"""

import wx
import time

class Trend (wx.Window):
	def __init__(self,parent,id=-1,pos=wx.DefaultPosition,size=wx.DefaultSize,style=0,nLines=1, hideXInfo=False):
		wx.Window.__init__(self,parent,-1, pos,size,style,"Trend")

		self.nLines= nLines
		self.hideXInfo = hideXInfo

		self.width = 10		# width of graph in seconds
		self.TimeBase = None

		self.nxMajorTicks, self.nxMinorTicks = 5,4
		self.nyMajorTicks, self.nyMinorTicks = 6,2

		self.yMin = [0.0]*nLines
		self.yMax = [1.0]*nLines
		self.legendFormat = ['%.1f'] * nLines

		self.labels = ["Line"]*nLines

		self.pens = [
				wx.Pen(wx.BLUE,		2, wx.SOLID),
				wx.Pen(wx.GREEN,	2, wx.SOLID),
				wx.Pen(wx.RED,		2, wx.SOLID),
				wx.Pen(wx.CYAN,		2, wx.SOLID),
				wx.Pen(wx.BLACK,	2, wx.SOLID),
				wx.Pen(wx.BLACK,	2, wx.SOLID),
				wx.Pen(wx.BLACK,	2, wx.SOLID),
				wx.Pen(wx.BLACK,	2, wx.SOLID),
				wx.Pen(wx.BLACK,	2, wx.SOLID),
		]

		self.Flush()

		#self.SetSizeHints(400,200,600,400)

		self.X0, self.Y0 = 75,25		# UL corner of trend box
		self.X1, self.Y1 = 50,46		# LR corner wrt entire window

		self._backgroundBrush = wx.WHITE_BRUSH
		self._gridColor1 = wx.Colour(136,136,136)
		self._gridColor2 = wx.Colour(0,0,0)

		self.Bind(wx.EVT_SIZE, self.OnSize)
		self.Bind(wx.EVT_PAINT, self.OnPaint)

	def Flush(self):
		self.trend  = []
		self.values = [0]*self.nLines
		self.clock  = time.clock() - self.width

	def GetRange(self,line):
		return self.yMin[line], self.yMax[line]

	def SetTimeBase(self,timeBase):
		self.TimeBase = timeBase

	def SetLabels(self,labels):
		self.labels = labels

	def SetLabel(self,line,label):
		self.labels[line] = label

	def SetRange(self,line,yMin,yMax,nyMajorTicks=None,nyMinorTicks=None):
		self.yMin[line] = float(yMin)
		self.yMax[line] = float(yMax)
		if nyMajorTicks:
			self.nyMajorTicks = nyMajorTicks
		if nyMinorTicks:
			self.nyMinorTicks = nyMinorTicks

	def SetLinePen(self,line,pen):
		self.pens[line] = pen

	def SetLabelPenAndRange(self,line,label,pen,yMin,yMax):
		self.labels[line] = label
		if pen:
			self.pens[line] = pen
		self.yMin[line] = yMin
		self.yMax[line] = yMax

	def SetWidth(self,width, nxMajorTicks=None, nxMinorTicks=None):
#		self.trend = []
		self.width = width
		if nxMajorTicks:
			self.nxMajorTicks = nxMajorTicks
		if nxMinorTicks:
			self.nxMinorTicks = nxMinorTicks
		self.Refresh(False)

	def AddPoint(self,*yList):
		now = time.clock()

		if self.TimeBase is None:
			start = now-self.width
			while len(self.trend) > 1  and  self.trend[1][0] < start:
				self.trend.pop(0)
			self.clock = start

		self.trend.append((now,)+yList)
		self.values = yList

		# Invalidate the region above the trend y=0..Y0 to get the legend info
#		self.Refresh(False,wx.Rect(self.X0,0,self.W-self.X0-self.X1,self.H-0-self.Y1))
		self.Refresh(False)

	def OnSize(self,event):
#		print "Trend.OnSize",self.GetSizeTuple()
		self.W, self.H = self.GetClientSize()
		self.bitmap = wx.EmptyBitmap(self.W,self.H)
		self.Refresh(True);

	def OnPaint(self,event):
		try:
			self.W
		except:
			self.OnSize(None)
			#print("Fake OnSize", self.W, self.H)
		dc = wx.BufferedPaintDC(self,self.bitmap)
		dc.SetBackground(wx.Brush(wx.Colour(192,192,192)))
		dc.Clear()
		self.OnDraw(dc)

	def DrawBox(self,dc):
		x0 ,y0 = self.X0, self.Y0
		w,  h  = self.W-self.X0-self.X1,  self.H-self.Y0-self.Y1

		# Draw the background & surrounding box
		lineWidth = 1
		pen = wx.Pen(wx.BLACK, lineWidth ,wx.SOLID)
		pen.SetJoin(wx.JOIN_MITER)
		with wx.DCPenChanger(dc, pen), wx.DCBrushChanger(dc, self._backgroundBrush):
			dc.DrawRectangle(x0-lineWidth/2, y0-lineWidth/2, w+lineWidth, h+lineWidth)

	def OnDraw(self,dc):
		x0 ,y0 = self.X0, self.Y0
		w,  h  = self.W-self.X0-self.X1,  self.H-self.Y0-self.Y1

		# TODO
		# Figure out how to avoid redrawing the tick labels every time
		# Involves use of GetUpdateRegion (in wxWindow not wxDC!!)

		self.DrawBox(dc)

		oldPen = dc.GetPen()
		pen1 = wx.Pen(self._gridColor1, 0, wx.SOLID)
		pen2 = wx.Pen(self._gridColor2, 0, wx.SOLID)

		oldFont = dc.GetFont()
		dc.SetFont(wx.Font(14, wx.SWISS, wx.NORMAL, wx.BOLD, False, 'Arial Narrow'))
		tickLength = 5
		minorTicksAsGrid = False

		# Horizontal axis ticks and tick labels
		format = "%.0f"
		nTicks = self.nxMajorTicks * self.nxMinorTicks
		for i in range(int(nTicks+1)):
			x = x0 + int(round(i * w / nTicks))
			if i != 0  and i != nTicks:
				#dc.SetPen(pen2 if i % self.nxMinorTicks == 0 else pen1)
				if i % self.nxMinorTicks != 0:
					if minorTicksAsGrid:
						dc.SetPen(pen1)
						dc.DrawLine(x,y0-1,x,y0+h)
					else:
						dc.SetPen(pen2)
						dc.DrawLine(x,y0-1,    x,y0+tickLength)
						dc.DrawLine(x,y0+h-tickLength, x,y0+h)
				else:
					dc.SetPen(pen1)
					dc.DrawLine(x,y0-1,x,y0+h)
					dc.SetPen(pen2)
					dc.DrawLine(x,y0-1,x,y0+2*tickLength)
					dc.DrawLine(x,y0+h-2*tickLength,x,y0+h)
			if i % self.nxMinorTicks == 0  and not self.hideXInfo:
				v = -self.width + i * self.width / nTicks
				s = format % v
				e = dc.GetTextExtent(s)
				dc.DrawText(s,x-e[0]/2,y0+h+5)

		# Vertical axis ticks and tick labels
		lMax = max(abs(self.yMin[0]), abs(self.yMax[0]))
		lFormat = "%.2f" if lMax <= 1 else "%.1f" if lMax <= 1000 else "%.0f"
		rMax = max(abs(self.yMin[1]), abs(self.yMax[1]))
		rFormat = "%.2f" if rMax <= 1 else "%.1f" if rMax <= 1000 else "%.0f"
		lFormat = rFormat = "%g"
		nTicks = self.nyMajorTicks * self.nyMinorTicks
		for i in range(int(nTicks+1)):
			y = y0 + h - int(round(i * h / nTicks))
			if i != 0  and  i != nTicks:
				if i % self.nyMinorTicks != 0:
					if minorTicksAsGrid:
						dc.SetPen(pen1)
						dc.DrawLine(x0-1,y,x0+w,y)
					else:
						dc.SetPen(pen2)
						dc.DrawLine(x0-1,y, x0+tickLength,y)
						dc.DrawLine(x0+w-tickLength,y, x0+w,y)
				else:
					dc.SetPen(pen1)
					dc.DrawLine(x0-1,y,x0+w,y)
					dc.SetPen(pen2)
					dc.DrawLine(x0-1,y, x0+2*tickLength,y)
					dc.DrawLine(x0+w-2*tickLength,y, x0+w,y)
			if i % self.nyMinorTicks == 0:
				v = self.yMin[0] + i * (self.yMax[0]-self.yMin[0]) / nTicks
				s = lFormat % v
				wt, ht = dc.GetTextExtent(s)
				dc.SetTextForeground(wx.BLUE)
				dc.DrawText(s, x0-wt-3, y-ht/2)

				# Alternate axix tick labels:  Use second min/max values for now
				v = self.yMin[1] + i * (self.yMax[1]-self.yMin[1]) / nTicks
				s = rFormat % v
				wt, ht = dc.GetTextExtent(s)
				dc.SetTextForeground(wx.BLACK)
				dc.DrawText(s, x0+w+3, y-ht/2)
			dc.SetTextBackground(wx.BLACK)

		#dc.SetFont(wx.Font(13,wx.SWISS,wx.NORMAL,wx.BOLD,False,'Arial Narrow'))
		if not self.hideXInfo:
			s = "Time  [seconds]"
			e = dc.GetTextExtent(s)
			dc.DrawText(s,x0+w/2-e[0]/2,y0+h+e[1])

		#s = self.labels[0]
		#e = dc.GetTextExtent(s)
		#dc.DrawRotatedText(s,10,y0+(h+e[0])/2,90)
		#dc.SetFont(wx.NullFont)

		# Draw in the data
		with wx.DCClipper(dc, x0, y0, w, h):
#		if 1:
			start = self.TimeBase or self.clock
			n = len(self.trend)
			points = [0]*n
			for j in range(self.nLines):
				yMin = self.yMin[j]
				yMax = self.yMax[j]
				xScale = float(w) / self.width
				yScale = float(h) / (yMax-yMin)
				for i in range(n):
					v = self.trend[i]
					x = x0 + xScale * (v[0]-start )
					y = y0 + yScale * (yMax-v[j+1])
					points[i] = (x,y)
				dc.SetPen(self.pens[j])
				dc.DrawLines(points)

		# Draw the legend
		x, y = x0,y0-dc.GetTextExtent(" ")[1] - 5
		for i in range(self.nLines):
			#dc.SetTextForeground(self.pens[i].GetColour())
			s = self.labels[i] + " = " + self.legendFormat[i] % self.values[i]
			dc.DrawText(s,x,y)
			e = dc.GetTextExtent(s)
			dc.SetPen(self.pens[i])
			dc.DrawLine(x + e[0]+20, y0-e[1]//2-5, x+e[0]+20 + 80, y0-e[1]//2-5)
#			x += 2*dc.GetTextExtent(s)[0]
			x += 250
		#dc.SetTextForeground(wx.BLACK)
		dc.SetFont(oldFont)
		dc.SetPen(oldPen)
