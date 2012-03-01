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

import matplotlib.dates
import datetime, pytz
import scipy.fftpack, numpy
import subprocess
import threading, Queue

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
			print stdout
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
