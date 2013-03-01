# This file is part of Spacetime.
#
# Copyright (C) 2010-2013 Leiden University.
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

import datetime, pytz
import numpy
import subprocess
import threading, Queue

from .superstruct import Struct
from .detect_timezone import detect_timezone
from . import pypymanager


class SharedXError(Exception):
	pass


localtz = pytz.timezone(detect_timezone())
utctz = pytz.utc


# Borrowed from matplotlib.cbook
def iterable(obj):
	'return true if *obj* is iterable'
	try:
		len(obj)
	except:
		return False
	return True


# Borrowed from matplotlib.dates
HOURS_PER_DAY = 24.
MINUTES_PER_DAY  = 60.*HOURS_PER_DAY
SECONDS_PER_DAY =  60.*MINUTES_PER_DAY
MUSECONDS_PER_DAY = 1e6*SECONDS_PER_DAY
def _to_ordinalf(dt):
	"""
	Convert :mod:`datetime` to the Gregorian date as UTC float days,
	preserving hours, minutes, seconds and microseconds.  Return value
	is a :func:`float`.
	"""

	if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
		delta = dt.tzinfo.utcoffset(dt)
		if delta is not None:
			dt -= delta

	base =  float(dt.toordinal())
	if hasattr(dt, 'hour'):
		base += (dt.hour/HOURS_PER_DAY + dt.minute/MINUTES_PER_DAY +
				 dt.second/SECONDS_PER_DAY + dt.microsecond/MUSECONDS_PER_DAY
				 )
	return base


# Borrowed from matplotlib.dates
def _from_ordinalf(x, tz):
	"""
	Convert Gregorian float of the date, preserving hours, minutes,
	seconds and microseconds.  Return value is a :class:`datetime`.
	"""
	ix = int(x)
	dt = datetime.datetime.fromordinal(ix)
	remainder = float(x) - ix
	hour, remainder = divmod(24*remainder, 1)
	minute, remainder = divmod(60*remainder, 1)
	second, remainder = divmod(60*remainder, 1)
	microsecond = int(1e6*remainder)
	if microsecond<10: microsecond=0 # compensate for rounding errors
	dt = datetime.datetime(
		dt.year, dt.month, dt.day, int(hour), int(minute), int(second),
		microsecond, tzinfo=utctz).astimezone(tz)

	if microsecond>999990:  # compensate for rounding errors
		dt += datetime.timedelta(microseconds=1e6-microsecond)

	return dt


def mpldtfromtimestamp(ts, tz=localtz):
	return mpldtfromdatetime(tz.localize(datetime.datetime.fromtimestamp(ts)))


def mpldtfromdatetime(dt):
	assert dt.tzinfo is not None
	# based on matplotlib.date2num
	if iterable(dt):
		return numpy.asarray([_to_ordinalf(val) for val in dt])
	else:
		return _to_ordinalf(dt)


def mpldtlikedatetime(*args, **kwargs):
	tz = kwargs.pop('tzinfo', localtz)
	return mpldtfromdatetime(tz.localize(datetime.datetime(*args, **kwargs)))


def datetimefrommpldt(num, tz=localtz):
	# based on matplotlib.num2date
	if iterable(num):
		return [_from_ordinalf(val, tz) for val in num]
	else:
		return _from_ordinalf(num, tz)


def mpldtstrptime(str, format, tz=localtz):
	return mpldtfromdatetime(tz.localize(datetime.datetime.strptime(str, format)))


class ContextManager(object):
	def __init__(self, enter, exit):
		self.enter = enter
		self.exit = exit

	def __enter__(self):
		return self.enter()

	def __exit__(self, exc_type, exc_value, traceback):
		return self.exit(exc_type, exc_value, traceback)


class FFmpegEncode(object):
	def __init__(self, path, format, codec, framerate, framesize, opts=None):
		command = [
			'ffmpeg',
			'-y',                # force overwrite
			'-f', 'rawvideo',    # input file format
			'-pix_fmt', 'rgb24', # input pixel format
			'-r', str(framerate),
			'-s', '{0}x{1}'.format(*framesize),
			'-i', '-',           # read from std input
			'-an',               # no audio
			'-r', str(framerate),
			'-f', format,        # output file format
			'-vcodec', codec,
		]
		if opts:
			command.extend(opts)
		command.append(path)
		self.proc = subprocess.Popen(
			command,
			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			close_fds=(not subprocess.mswindows),
		)

	def spawnstdoutthread(self):
		def readstdout(queue, stdout):
			for line in stdout:
				queue.put(line)
			stdout.close()
		queue = Queue.Queue()
		thread = threading.Thread(target=readstdout, args=(queue, self.proc.stdout))
		thread.start()

		def cleanup():
			thread.join()
			stdout = []
			while not queue.empty():
				stdout.append(queue.get())		
			return ''.join(stdout)
		return cleanup

	def writeframe(self, data): # needs RGB raw data
		self.proc.stdin.write(data)

	def close(self):
		if hasattr(self, 'proc'):
			if not self.proc.stdin.closed:
				self.proc.stdin.close()
			proc = self.proc
			del self.proc
			return proc.wait()

	def abort(self):
		if hasattr(self, 'proc'):
			self.proc.terminate()
		return self.close()

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc_value, traceback):
		self.close()


# decorator function, for stuff to be delegated to the pypy subprocess
def pypy(func):
	def wrapper(*args, **kwargs):
		return pypymanager.run(func, *args, **kwargs)
	wrapper.__name__ = func.__name__
	return wrapper

def class_fqn(cls):
	return '{0.__module__}.{0.__name__}'.format(cls)

def instance_fqcn(obj):
	return class_fqn(obj.__class__)


def loadtxt(file, delimiter=None, skip_lines=0):
	# simplified & faster version of numpy.loadtxt
	if isinstance(file, basestring):
		file = open(file)
	
	for i in range(skip_lines):
		next(file)

	lines = (line.strip() for line in file)
	return numpy.array([line.split(delimiter) for line in lines if line], dtype=float)


# shamelessly copied from matplotlib 1.2.0 to provide compatibility with older
# matplotlib versions that do not understand PIL mode I;16
def pil_to_array( pilImage ):
	"""
	Load a PIL image and return it as a numpy array.  For grayscale
	images, the return array is MxN.  For RGB images, the return value
	is MxNx3.  For RGBA images the return value is MxNx4
	"""
	def toarray(im, dtype=numpy.uint8):
		"""Teturn a 1D array of dtype."""
		x_str = im.tostring('raw', im.mode)
		x = numpy.fromstring(x_str, dtype)
		return x

	if pilImage.mode in ('RGBA', 'RGBX'):
		im = pilImage # no need to convert images
	elif pilImage.mode=='L':
		im = pilImage # no need to luminance images
		# return MxN luminance array
		x = toarray(im)
		x.shape = im.size[1], im.size[0]
		return x
	elif pilImage.mode=='RGB':
		#return MxNx3 RGB array
		im = pilImage # no need to RGB images
		x = toarray(im)
		x.shape = im.size[1], im.size[0], 3
		return x
	elif pilImage.mode.startswith('I;16'):
		# return MxN luminance array of uint16
		im = pilImage
		if im.mode.endswith('B'):
			x = toarray(im, '>u2')
		else:
			x = toarray(im, '<u2')
		x.shape = im.size[1], im.size[0]
		return x.astype('=u2')
	else: # try to convert to an rgba image
		try:
			im = pilImage.convert('RGBA')
		except ValueError:
			raise RuntimeError('Unknown image mode')

	# return MxNx4 RGBA array
	x = toarray(im)
	x.shape = im.size[1], im.size[0], 4
	return x


class StackCache(object):
	def __init__(self, limit=None):
		self.limit = limit
		self.activity = []
		self.lookup = {}

	def find(self, key):
		if key in self.lookup:
			self.activity.remove(key)
			self.activity.insert(0, key)
			return self.lookup[key]
		return None

	def insert(self, key, value):
		self.lookup[key] = value
		self.activity.insert(0, key)
		self._check_limit()

	def set_limit(self, limit):
		self.limit = limit
		self._check_limit()

	def _check_limit(self):
		if self.limit is None or len(self.activity) <= self.limit:
			return
		excess = self.activity[self.limit:]
		for key in excess:
			del self.lookup[key]
		self.activity = self.activity[:self.limit]
