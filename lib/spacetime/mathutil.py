# This file is part of Spacetime.
#
# Copyright (C) 2010-2012 Leiden University.
# Written by Sander Roobol.
#
# Spacetime is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Spacetime is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import scipy.fftpack
import numpy

def easyfft(data, sample_frequency):
	N = len(data)
	z = scipy.fftpack.fft(data) / N

	if N % 2 == 0:
		freq = numpy.linspace(0, sample_frequency / 2., N/2+1)
		zpos = z[0:N/2+1]
	else:
		freq = numpy.linspace(0, sample_frequency / 2., (N+1)/2)
		zpos = z[0:(N+1)/2]

	return freq, abs(zpos)**2
