from __future__ import division

import numpy
import itertools
from camera.formats import raw
import datetime
from util import *

class DataSource(object):
	def __init__(self, filename, label=None):
		self.filename = filename
		self.label = label


class MultiTrend(DataSource):
	def selectchannels(self, condition):
		return SelectedMultiTrend(self, condition)


class SelectedMultiTrend(MultiTrend):
	def __init__(self, parent, condition):
		self.parent = parent
		self.condition = condition

	def iterchannels(self):
		return itertools.ifilter(self.condition, self.parent.iterchannels())


class QMS(MultiTrend):
	channels = None
	masses = None
	fp = None

	@staticmethod
	def parseDT(s):
		return mpdtfromdatetime(datetime.datetime.strptime(s, '%m/%d/%Y %I:%M:%S %p'))

	@staticmethod
	def parseExtDT(s):
		return mpdtfromdatetime(datetime.datetime.strptime(s, '%m/%d/%Y %I:%M:%S.%f %p'))

	@staticmethod
	def parseLine(line):
		data = line.strip().split('\t')
		assert len(data) % 3 == 0
		return [float(d) for (i,d) in enumerate(data) if (i % 3) in (1, 2)]

	def __init__(self, filename, label=None):
		super(QMS, self).__init__(filename, label)
		self.fp = open(self.filename)

		headerlines = [self.fp.readline() for i in range(6)]
		self.header = Struct()
		self.header.source     =                 headerlines[0].split('\t')[1].strip()
		self.header.exporttime =    self.parseDT(headerlines[1].split('\t')[1].strip())
		self.header.starttime  = self.parseExtDT(headerlines[3].split('\t')[1].strip())
		self.header.stoptime   = self.parseExtDT(headerlines[4].split('\t')[1].strip())

		self.masses = [int(i) for i in self.fp.readline().split()]
		columntitles = self.fp.readline() # not used
		

	def read(self):
		data = [self.parseLine(line) for line in self.fp if line.strip()]
		if len(data[-2]) > len(data[-1]):
			data[-1].extend([0.] * (len(data[-2]) - len(data[-1])))
		rawdata = numpy.array(data)

		self.channels = []
		for i, mass in enumerate(self.masses):
			d = Struct()
			d.mass = mass
			d.label = str(mass)
			d.time = rawdata[:,2*i]/86400 + self.header.starttime
			d.value = rawdata[:,2*i+1]
			self.channels.append(d)

	def iterchannels(self):
		if self.channels is None:
			self.read()
		return iter(self.channels)


class GasCabinet(MultiTrend):
	controllers = ['MFC CO', 'MFC NO', 'MFC H2', 'MFC O2', 'MFC Shunt', 'BPC1', 'BPC2', 'MFM Ar']
	parameters = ['valve output', 'measure', 'set point']
	data = None

	def read(self):
		self.data = numpy.loadtxt(self.filename)
		# FIXME: this is an ugly hack to determine the date. the fileformat should be
        # modified such that date information is stored INSIDE the file
		import re
		y, m, d = re.search('(20[0-9]{2})([0-9]{2})([0-9]{2})', self.filename).groups()
 		self.offset = mpdtfromdatetime(datetime.datetime(int(y), int(m), int(d)))

	def iterchannels(self):
		if self.data is None:
			self.read()
		columns = self.data.shape[1]
		assert (columns - 2)  % 4 == 0
		for i in range((columns - 2) // 4):
			time = self.data[:,i*4]/86400 + self.offset
			for j, p in enumerate(self.parameters):
				yield Struct(time=time, value=self.data[:,i*4+j+1], label='%s %s' % (self.controllers[i], p), parameter=p, controller=self.controllers[i])
		# NOTE: the last two columns (Leak dectector) are ignored


class Image(DataSource):
	def apply_filter(self, *filters):
		return ImageFilter(self, *filters)


class ChainedImage(Image):
	def __init__(self, *args):
		self.args = args

	def iterframes(self):
		for arg in self.args:
			for frame in arg.iterframes():
				yield frame


class Camera(DataSource):
	def __init__(self, filename, label=None):
		super(Camera, self).__init__(filename, label)
		self.rawfile = raw.RawFileReader(self.filename)

	def getdata(self, channel, frame):
		ret = Struct()
		ret.image = self.rawfile.channelImage(frame, channel).asArray()
		ysize, xsize = ret.image.shape

		frameinfo = self.rawfile.frameInfo(frame)
		ret.tstart = mpdtfromtimestamp(frameinfo.acquisitionTime)
		ret.tend = ret.tstart + (xsize*ysize / frameinfo.pixelclock_kHz / 1000 * 2) / 86400
		return ret

	def getframecount(self):
		return self.rawfile.header.frameCount

	def selectchannel(self, channel):
		return CameraChannel(self, channel)


class CameraChannel(Image):
	def __init__(self, cameradata, channel):
		self.cameradata = cameradata
		self.channel = channel

	def iterframes(self):
		for i in range(self.cameradata.getframecount()):
			yield self.cameradata.getdata(self.channel, i)


class ImageFilter(Image):
	def __init__(self, original, *filters):
		self.original = original
		self.filters = list(filters)

	def iterframes(self):
		return itertools.imap(self.apply, self.original.iterframes())
	
	def apply(self, frame):
		for filter in self.filters:
			frame = filter(frame)
		return frame

	def apply_filter(self, *filters):
		self.filters.extend(filters)
		return self
