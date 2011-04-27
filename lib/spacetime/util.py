import matplotlib.dates
import time, datetime, pytz
import scipy.fftpack, numpy

from .superstruct import Struct


class SharedXError(Exception):
	pass


localtz = pytz.timezone('Europe/Amsterdam') # FIXME: should be detected
utctz = pytz.utc

def mpldtfromtimestamp(ts, tz=localtz):
	return matplotlib.dates.date2num(tz.localize(datetime.datetime.fromtimestamp(ts)))

def mpldtfromdatetime(dt):
	assert dt.tzinfo is not None
	return matplotlib.dates.date2num(dt)

def datetimefrommpldt(num, tz=localtz):
	return matplotlib.dates.num2date(num, tz)

def mpldtstrptime(str, format, tz=localtz):
	return mpldtfromdatetime(tz.localize(datetime.datetime.strptime(str, format)))


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
