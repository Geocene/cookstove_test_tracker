from __future__ import absolute_import, division, print_function, unicode_literals

import math

#Use my local copy of matplotlib.ticker
from . import _ticker as mplticker

#Use the installed version
#import matplotlib.ticker as mplticker

NullLocator = mplticker.NullLocator
FixedLocator = mplticker.FixedLocator
IndexLocator = mplticker.IndexLocator
LinearLocator = mplticker.LinearLocator
LogLocator = mplticker.LogLocator
MultipleLocator = mplticker.MultipleLocator
MaxNLocator = mplticker.MaxNLocator
AutoLocator = mplticker.AutoLocator
#from mplticker import NullLocator, FixedLocator, IndexLocator, LinearLocator
#from mplticker import LogLocator, MultipleLocator, MaxNLocator, AutoLocator


#Use the matplotlib versions for most of these, except for
#LogFormatterMathtext.  Perhaps I should make a really simple
#version of that, which understands $\mathdefault{xxx^{yyy}}$
TickHelper = mplticker.TickHelper
Formatter = mplticker.Formatter
NullFormatter = mplticker.NullFormatter
IndexFormatter = mplticker.IndexFormatter
FixedFormatter = mplticker.FixedFormatter
FuncFormatter = mplticker.FuncFormatter
FormatStrFormatter = mplticker.FormatStrFormatter
ScalarFormatter = mplticker.ScalarFormatter
LogFormatter = mplticker.LogFormatter
LogFormatterExponent = mplticker.LogFormatterExponent
LogFormatterMathtext = mplticker.LogFormatterMathtext
#from mplticker import TickHelper, Formatter
#from mplticker import NullFormatter, IndexFormatter, FixedFormatter, FuncFormatter
#from mplticker import FormatStrFormater, LocFormatter, LogFormatterExponent, LogFormatterMathtext


#TODO: Do this one right, which would mean returning a bitmap for the
#      moment, which the caller would have to recognize.
#      Could also have it return mathtext, and build a trivial version
#      of a mathtext interpreter.
#      Looks something like $\mathdefault{10^{2}}$ for 1e2
class LogFormatterMathtext(Formatter):
	#Commented out to allow the software in BLDG70
	#def __init__(self):
	#	TickHelper.__init__(self)

	def __call__(self, value, pos=None):
		if value == 0:
			return "0"
		e = math.floor(math.log10(value))
		v = value / 10**e
		return "%ge%d" % (v, e)

