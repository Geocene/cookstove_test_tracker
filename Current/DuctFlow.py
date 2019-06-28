from __future__ import absolute_import, division, print_function	#, unicode_literals

import math

#
# Compute Saturation pressure of H2O
# Ref http://www.vaisala.com/Vaisala%20Documents/Application%20notes/Humidity_Conversion_Formulas_B210973EN-F.pdf
# Temperature range -20 to 50 C
# Return value is in Pascals

def SaturationPressure(T):
	A = 6.116441
	m = 7.591386
	Tn = 240.7263
	PSat = A * 10 ** (m * T / (T + Tn))
	return 100 * PSat


def CalculateDuctFlow(deltaP, T, RH, P=101325):
	D  = 6 * 0.0254	# Duct diameter [m]
	D0 = 0.1164	# Orifice diameter [m]
	Cd = 0.6052	# Discharge coefficient

	A0 = 0.25 * math.pi * D0**2
	beta = D0/D
	print(A0, beta)

	#print SaturationPressure(T)

	RUniv = 8314.4621
	#mwAir = 28.965			# -> R = 287.052 where Julian had 286.9
	#mwH2O = 18.01528		# -> R = 461.522 where Julian had 461.5
	#B = mwAir/mwH2O		# 0.621967 where Julian had 0.6219907
	#print R/mwAir, R/mwH2O, mwH2O/mwAir

	#PSat = SaturationPressure(T)
	#pH2O = .01 * RH * PSat
	#x = pH2O / P
	#mW = (1-x) * mwAir + x * mwH2O
	mW = 28.98
	#print('P', P, 'PSat', PSat, 'x', x, 'mW', mW)

	density = P * mW / (RUniv * (T+273.15))

	Q = Cd * A0 * math.sqrt(2 * deltaP / density / (1 - beta**4))
	#Convert m^3/sec to CFM
	print('iso', Q, Q*60/(0.3048**3))

	K = 375
	deltaP = max(deltaP, 0)
	Q = K * math.sqrt(deltaP * 0.004014)
	print('k  ', Q)

if __name__ == "__main__":
	CalculateDuctFlow(deltaP=132.5, T=30, RH=40, P=101325)