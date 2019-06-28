from __future__ import (absolute_import, division, print_function, unicode_literals)

import numpy as np

#class colormaps:
#	pass
#cm = colormaps()

gray = None


def blue(v):
	v = float(v/2 + 1)	# Matlab scaling

	if v <= 16:
		return 0.5313 + (1 - 0.5313) * (v-1) / (16-1)
	elif v <= 48:
		return 1.0
	elif v < 80:
		return 1.0 + (0.0 - 1) * (v - 48) / (80 - 48)
	else:
		return 0.0

def green(v):
	v = float(v/2 + 1)	# Matlab scaling

	if v < 17:
		return 0.0
	elif v <= 48:
		return 0 + (1.0 - 0.0) * (v - 17) / (48-17)
	elif v <= 80:
		return 1.0
	elif v <= 112:
		return 1.0 + (0.0 - 1.0) * (v-80) / (112 - 80)
	else:
		return 0.0

def red(v):
	v = float(v/2 + 1)	# Matlab scaling

	if v <= 48:
		return 0.0
	elif v <= 80:
		return 0.0 + (1.0 - 0.0) * (v-48) / (80 - 48)
	elif v <= 112:
		return 1.0
	else:
		return 1.0 + (0.5 - 1.0) * (v-112) / (128 - 112)

colorMap = np.zeros((256, 3), dtype=np.uint8)
for i in range(256):
	colorMap[i, 0] = int(255*red(i))
	colorMap[i, 1] = int(255*green(i))
	colorMap[i, 2] = int(255*blue(i))
