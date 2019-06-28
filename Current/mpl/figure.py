from __future__ import (absolute_import, print_function, division, unicode_literals)

#from plot import Axes
from .plot import Axes

class Figure():
	def __init__(self):
		self.axesList = []
		#Defaults
		self.left, self.right, self.hspace = 0.125, 0.9, 0.2
		self.bottom, self.top, self.vspace = 0.1, 0.9, 0.2

	def add_subplot(self, nRows, nCols, n):
		ax = Axes(self, nRows, nCols, n)
		self.axesList.append(ax)
		return ax

	#TODO: Understand why adjusting top seems to do nothing
	def subplots_adjust(self, *args, **kwargs):
		#TODO: Is the best way to do this verification?
		choices = ['left', 'right', 'hspace', 'bottom', 'top', 'vspace']
		for key, value in kwargs.items():
			assert(key in choices)
			setattr(self, key, value)

	def setGeometry(self, x, y, w, h):
		self.x, self.y, self.w, self.h = x, y, w, h

	def draw(self, dc):
		X, Y, W, H = self.x, self.y, self.w, self.h
		for ax in self.axesList:
			nRows, nCols, n = ax.subplot_info
			iCol, iRow = (n-1)%nCols, (n-1)/nCols

			w = (self.right - self.left) / (nCols + (nCols-1)*self.hspace)
			h = (self.top - self.bottom) / (nRows + (nRows-1)*self.vspace)
			x = X + (self.left  + w*(1+self.hspace)*iCol)*W
			y = Y + (1-self.top + h*(1+self.vspace)*iRow)*H
			ax.setGeometry(x,y, w*W, h*H)
			ax.draw(dc)
