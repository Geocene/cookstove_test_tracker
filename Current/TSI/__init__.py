from __future__ import absolute_import, division, print_function	#, unicode_literals

from .FMPS3091 import FMPS3091
from .OPS3330 import OPS3330
from .APS3321 import APS3321
from .DustTrax import DustTrax


#
# Sizer Bin Location notes
# The bin edges are fixed on the FMPS3091 and APS3330 units.  First, I reverse
# engineered the approximate values by using the bin center locations in the
# TSI Aerosol Instrument Manager.  There were 32 bins over two decades for the
# FMPS3091 (16 bins/decade), and 51 bins over 1.5 decades for the APS3321
# (32 bins/decade).  Sometime after that I realized that the both had bin boundaries
# aligned so that they aligned with a grid of 32 bins per decade, starting at 1
# nanommeter.  In effect, the only reverse engineering left is the starting bin location,
# which is now an integer.
#
# The OPS3330 has settable bin locations.  They are set in the software below
# so that the final bin ends at 10000 nm.  There are 16 bins, each with a width
# of 32/3 bins per decade.
#
# This table has virtual bin 0 starting at 1 nm, and 32 bins per decade.  The bin
# width is the number of multiples one virtual bin in a single device bin.
#
# FMPS3091
#   nBins = 32, binWidth=2, virtualBin0=24, virtualBinN=virtualBin0+nBins*binWidth=88
#   dMin = 1 * 10**(virtualBin0/32) = 5.6234
#   dMax = 1 * 10**(virtualBinN/32) = 562.34
#
# OPS3330
#   nBins = 16l  binWidth=3, virtualBin0=80, virtualBinN=virtualBin0+nBinw*binWidth=128
#   dMin = 1 * 10**(virtualBin0/32) = 316.228
#   dMax = 1 * 10**(virtualBinN/32) = 10000
#
# APS3321
#   nBins = 51;  binWidth=1, virtualBin0=87, virtualBinN=virtualBin0+nBins*binWidth=138
#   dMin = 1 * 10**(virtualBin0/32) = 523.299
#   dMax = 1 * 10**(virtualBinN/32) = 20535.25
#
# TODO: As of 2014.08.28 I think the bin locations on the APS3321 might be adjustable
# via the RS-232 interface.  I need to check this.
#
