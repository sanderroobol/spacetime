import matplotlib.dates
import datetime, pytz
import scipy.fftpack, numpy

from .superstruct import Struct
from .detect_timezone import detect_timezone


class SharedXError(Exception):
	pass


localtz = pytz.timezone(detect_timezone())
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
	N = len(data)
	z = scipy.fftpack.fft(data) / N

	if N % 2 == 0:
		freq = numpy.linspace(0, sample_frequency / 2., N/2+1)
		zpos = z[0:N/2+1]
	else:
		freq = numpy.linspace(0, sample_frequency / 2., (N+1)/2)
		zpos = z[0:(N+1)/2]

	return freq, abs(zpos)**2


class ContextManager(object):
	def __init__(self, enter, exit):
		self.enter = enter
		self.exit = exit

	def __enter__(self):
		return self.enter()

	def __exit__(self, exc_type, exc_value, traceback):
		return self.exit(exc_type, exc_value, traceback)
