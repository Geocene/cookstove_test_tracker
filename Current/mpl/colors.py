from __future__ import absolute_import, division, print_function, unicode_literals
import numpy as np

class Normalizer:
	def __init__(self, vmin, vmax, clip=False):
		self.vmin = vmin
		self.vmax = vmax
		self.clip = clip

	def copyAndClip(self, A):
		if self.clip:
			A = np.clip(A, self.vmin, self.vmax)
		else:
			A = A.copy()
		return A

class Normalize(Normalizer):
	def Normalize(self, A, scale=1):
		A = self.copyAndClip(A)
		A -= self.vmin
		A *= scale / (self.vmax - self.vmin)
		return A


class LogNorm(Normalizer):
	def Normalize(self, A, scale=1):
		A = self.copyAndClip(A)
		np.log(A, out=A)
		A -= np.log(self.vmin)
		A *= scale / np.log(self.vmax/self.vmin)
		return A
