from __future__ import division

import numpy
import itertools
from camera.formats import raw
import datetime

from .util import *

class DataSource(object):
	def __init__(self, filename):
		self.filename = filename

	def apply_filter(self, *filters):
		return DataSourceFilter(self, *filters)


class MultiTrend(DataSource):
	channels = None

	def selectchannels(self, condition):
		return SelectedMultiTrend(self, condition)

	def iterchannels(self):
		if self.channels is None:
			self.read()
		return iter(self.channels)

	def iterchannelnames(self):
		return (chan.id for chan in self.channels)


class SelectedMultiTrend(MultiTrend):
	def __init__(self, parent, condition):
		self.parent = parent
		self.condition = condition

	def iterchannels(self):
		return itertools.ifilter(self.condition, self.parent.iterchannels())

	def iterchannelnames(self):
		return (chan.id for chan in self.parent.iterchannels() if self.condition(chan))


class QMS(MultiTrend):
	channels = None
	masses = None
	fp = None

	@staticmethod
	def parseDT(s):
		return mpldtfromdatetime(datetime.datetime.strptime(s, '%m/%d/%Y %I:%M:%S %p'))

	@staticmethod
	def parseExtDT(s):
		return mpldtfromdatetime(datetime.datetime.strptime(s, '%m/%d/%Y %I:%M:%S.%f %p'))

	@staticmethod
	def parseLine(line):
		data = line.strip().split('\t')
		assert len(data) % 3 == 0
		return [float(d) for (i,d) in enumerate(data) if (i % 3) in (1, 2)]

	def __init__(self, *args, **kwargs):
		super(QMS, self).__init__(*args, **kwargs)
		self.fp = open(self.filename)

		headerlines = [self.fp.readline() for i in range(6)]
		self.header = Struct()
		self.header.source     =                 headerlines[0].split('\t')[1].strip()
		self.header.exporttime =    self.parseDT(headerlines[1].split('\t')[1].strip())
		self.header.starttime  = self.parseExtDT(headerlines[3].split('\t')[1].strip())
		self.header.stoptime   = self.parseExtDT(headerlines[4].split('\t')[1].strip())

		self.masses = [int(i) for i in self.fp.readline().split()]
		columntitles = self.fp.readline() # not used
		
		data = [self.parseLine(line) for line in self.fp if line.strip()]
		if len(data[-2]) > len(data[-1]):
			data[-1].extend([0.] * (len(data[-2]) - len(data[-1])))
		rawdata = numpy.array(data)

		self.channels = []
		for i, mass in enumerate(self.masses):
			d = Struct()
			d.mass = mass
			d.id = str(mass)
			d.time = rawdata[:,2*i]/86400 + self.header.starttime
			d.value = rawdata[:,2*i+1]
			self.channels.append(d)


class OldGasCabinet(MultiTrend):
	controllers = ['MFC CO', 'MFC NO', 'MFC H2', 'MFC O2', 'MFC Shunt', 'BPC1', 'BPC2', 'MFM Ar']
	parameters = ['valve output', 'measure', 'set point']
	data = None

	def __init__(self, *args, **kwargs):
		super(OldGasCabinet, self).__init__(*args, **kwargs)
		self.data = numpy.loadtxt(self.filename)
		# FIXME: this is an ugly hack to determine the date. the fileformat should be
        # modified such that date information is stored INSIDE the file
		import re
		y, m, d = re.search('(20[0-9]{2})([0-9]{2})([0-9]{2})', self.filename).groups()
 		self.offset = mpldtfromdatetime(datetime.datetime(int(y), int(m), int(d)))

		columns = self.data.shape[1]
		assert (columns - 2)  % 4 == 0
		self.channels = []
		for i in range((columns - 2) // 4):
			time = self.data[:,i*4]/86400 + self.offset
			for j, p in enumerate(self.parameters):
				self.channels.append(Struct(time=time, value=self.data[:,i*4+j+1], id='%s %s' % (self.controllers[i], p), parameter=p, controller=self.controllers[i]))
		# NOTE: the last two columns (Leak dectector) are ignored


class GasCabinet(MultiTrend):
	controllers = ['NO', 'H2', 'O2', 'CO', 'Ar', 'Shunt', 'BPC1', 'BPC2']
	parameters = ['time', 'measure', 'set point', 'valve output']
	valves = ['MIX', 'MRS', 'INJ', 'OUT', 'Pump'] 
	data = None

	@staticmethod
	def parselabviewdate(fl):
		# Labview uses the number of seconds since 1-1-1904 00:00:00 UTC.
		# mpldtfromdatetime(datetime.datetime(1904, 1, 1, 0, 0, 0, tzinfo=pytz.utc)) = 695056
		# FIXME: the + 1./24 is a hack to convert to local time
		return fl / 86400. + 695056 + 1./24

	def __init__(self, *args, **kwargs):
		super(GasCabinet, self).__init__(*args, **kwargs)
		self.data = numpy.loadtxt(self.filename, skiprows=1) # skip header line

		assert self.data.shape[1] == 38
		self.channels = []
		for i, c in enumerate(self.controllers):
			time = self.parselabviewdate(self.data[:,i*4])
			for j, p in enumerate(self.parameters[1:]):
				self.channels.append(Struct(time=time, value=self.data[:,i*4+j+1], id='%s %s' % (c, p), parameter=p, controller=c))

		colstart = len(self.controllers) * len(self.parameters)
		time = self.parselabviewdate(self.data[:,colstart])
		for i, v in enumerate(self.valves):
			self.channels.append(Struct(time=time, value=self.data[:,colstart+i+1], id='%s valve' % v, valve=v))
			

class TPDirk(MultiTrend):
	def readiter(self):
		fp = open(self.filename)
		fp.readline() # ignore two header lines
		fp.readline()
		for line in fp:
			data = line.strip().split(';')
			if len(data) == 2: # last line ends with "date;time"
				continue
			no, dt, pressure, temperature = data
			yield numpy.array((
				mpldtfromdatetime(datetime.datetime.strptime(dt, '%y/%m/%d %H:%M:%S')),
				float(pressure),
				float(temperature)
			))

	def __init__(self, *args, **kwargs):
		super(TPDirk, self).__init__(*args, **kwargs)
		data = numpy.array(list(self.readiter()))
		self.channels = [
			Struct(id='pressure', time=data[:,0], value=data[:,1]),
			Struct(id='temperature', time=data[:,0], value=data[:,2]),
		]



class ChainedImage(DataSource):
	def __init__(self, *args):
		self.args = args

	def iterframes(self):
		for arg in self.args:
			for frame in arg.iterframes():
				yield frame


# Camera class for image mode and trend mode
class Camera(MultiTrend):
	direction = raw.RawFileChannelInfo.LR
	averaging = False # only for trend mode

	def __init__(self, *args, **kwargs):
		super(Camera, self).__init__(*args, **kwargs)
		self.rawfile = raw.RawFileReader(self.filename)

	def getdata(self, channel, frame):
		ret = Struct()
		ret.image = self.rawfile.channelImage(frame, channel).asArray(direction=self.direction)
		ysize, xsize = ret.image.shape

		frameinfo = self.rawfile.frameInfo(frame)
		ret.tstart = mpldtfromtimestamp(frameinfo.acquisitionTime)
		ret.tend = ret.tstart + (xsize*ysize / frameinfo.pixelclock_kHz / 1000 * 2) / 86400
		return ret

	def getchanneldata(self, channel, frameiter=None):
		data = []
		time = []
		if frameiter is None:
			frameiter = self.framenumberiter()
		for frame in frameiter:
			image = self.rawfile.channelImage(frame, channel).asArray(direction=self.direction)

			frameinfo = self.rawfile.frameInfo(frame)
			tstart = mpldtfromtimestamp(frameinfo.acquisitionTime)
			tend = tstart + (image.size / frameinfo.pixelclock_kHz / 1000 * 2) / 86400

			if self.averaging:
				im = image.mean(axis=1) # FIXME: check if this is really the right axis to average
			else:
				im = image.flatten()
			data.append(im)
			time.append(numpy.linspace(tstart, tend, im.size))
		return Struct(id=str(channel), value=numpy.hstack(data), time=numpy.hstack(time))

	def getframecount(self):
		return self.rawfile.header.frameCount

	def getchannelcount(self):
		return self.rawfile.header.channelCount

	def selectchannel(self, channel):
		return CameraChannel(self, channel)
	
	def selectframes(self, *args, **kwargs):
		return CameraSelectedFrames(self, *args, **kwargs)

	def framenumberiter(self):
		return xrange(self.getframecount())

	def iterchannelnames(self):
		return (str(i) for i in range(self.getchannelcount()))

	def iterchannels(self):
		return (self.getchanneldata(channel) for channel in range(self.getchannelcount()))


# image mode and trend mode
class CameraSelectedFrames(MultiTrend):
	def __init__(self, cameradata, firstframe, lastframe, step=1):
		self.cameradata = cameradata
		self.firstframe = firstframe
		self.lastframe = lastframe
		self.step = step

	def framenumberiter(self):
		return xrange(max(0, self.firstframe), min(self.lastframe+1, self.cameradata.getframecount()), self.step)

	def selectframes(self, *args, **kwargs):
		return self.cameradata.selectframes(*args, **kwargs)

	def selectchannel(self, channel):
		return CameraChannel(self, channel)

	def getdata(self, channel, frame):
		return self.cameradata.getdata(channel, frame)

	def iterchannelnames(self):
		return self.cameradata.iterchannelnames()

	def iterchannels(self):
		return (self.cameradata.getchanneldata(channel, self.framenumberiter()) for channel in range(self.cameradata.getchannelcount()))


# image mode only
class CameraChannel(DataSource):
	def __init__(self, cameradata, channel):
		self.cameradata = cameradata
		self.channel = channel

	def selectframes(self, *args, **kwargs):
		return self.cameradata.selectframes(*args, **kwargs).selectchannel(self.channel)

	def iterframes(self):
		for i in self.cameradata.framenumberiter():
			yield self.cameradata.getdata(self.channel, i)


class DataSourceFilter(MultiTrend):
	def __init__(self, original, *filters):
		self.original = original
		self.filters = list(filters)
		
	def iterframes(self):
		return itertools.imap(self.apply, self.original.iterframes())

	def iterchannels(self):
		return itertools.imap(self.apply, self.original.iterchannels())

	def iterchannelnames(self):
		return self.original.iterchannelnames()
	
	def apply(self, data):
		for filter in self.filters:
			data = filter(data)
		return data

	def apply_filter(self, *filters):
		self.filters.extend(filters)
		return self
