import matplotlib.dates
import datetime
import scipy.fftpack, numpy

from .superstruct import Struct


class SharedXError(Exception):
	pass


# FIXME: These functions are currently not timezone aware, this could cause problems eventually.
def mpldtfromtimestamp(ts):
	return matplotlib.dates.date2num(datetime.datetime.fromtimestamp(ts))

mpldtfromdatetime = matplotlib.dates.date2num
datetimefrommpldt = matplotlib.dates.num2date


def easyfft(data, sample_frequency):
	N = len(data) - 1
	z = scipy.fftpack.fftshift(scipy.fftpack.fft(data) / N)

	if N % 2 == 0:
		freq = numpy.arange(-N/2, N/2, dtype=float)
	else:
		freq = numpy.arange(-(N-1)/2, (N+1)/2, dtype=float)
	freq *= sample_frequency / N

	z = z[freq > 0]       # FIXME: this could be simplified
	freq = freq[freq > 0] # idem
	return (freq, z * z.conj())
