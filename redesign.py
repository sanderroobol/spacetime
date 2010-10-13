from __future__ import division

import itertools
import datetime
import pytz

import numpy
import scipy.stats
import pylab, matplotlib

from superstruct import Struct

from camera.formats import raw

# FIXME: These functions are currently not timezone aware, this could cause problems eventually.
def mpdtfromtimestamp(ts):
	return matplotlib.dates.date2num(datetime.datetime.fromtimestamp(ts))

mpdtfromdatetime = matplotlib.dates.date2num


class MainFigure(object):
	def __init__(self):
		self.plots = []

	def add_plot(self, plot):
		self.plots.append(plot)

	def build(self):
		self.figsetup()
		top = None
		for i, p in enumerate(self.plots):
			if top:
				axes = self.figure.add_subplot(len(self.plots), 1, i+1, sharex=top)
			else:
				top = axes = self.figure.add_subplot(len(self.plots), 1, i+1)
			try:
				if p.secondarydata: # FIXME: this is not really nice
					p.secondaryaxes = axes.twinx()
					p.secondaryaxes.xaxis_date()
			except AttributeError:
				pass
			if i + 1 != len(self.plots):
				self.hide_xticklabels(axes)
			p.build(axes)
			axes.xaxis_date()
		self.reformat_xaxis()

	def reformat_xaxis(self):
		self.figure.axes[-1].xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M:%S'))

	@staticmethod
	def hide_xticklabels(ax):
		for label in ax.get_xticklabels():
			label.set_visible(False)

	def figinit(self, size=(14,8)):
		self.figure = matplotlib.figure.Figure(figsize=size)

	def figsetup(self, size=(14,8), legend=0):
		self.figinit(size)

		width, height = size
		def wabs2rel(x): return x / width
		def habs2rel(x): return x / height

		lrborder = .75
		tbborder = .45
		hspace = .2
		wspace = .2
		
		self.figure.subplots_adjust(
				left=wabs2rel(lrborder),
				right=1-wabs2rel(lrborder + legend),
				top=1-habs2rel(tbborder),
				bottom=habs2rel(tbborder),
				hspace=habs2rel(hspace),
				wspace=wabs2rel(wspace),
		)


class MainFigurePylab(MainFigure):
	def figinit(self, size=(14,8)):
		self.figure = matplotlib.pyplot.figure(figsize=size)


class Plot(object):
	axes = None

	def build(self, axes):
		raise NotImplementedError

	def clean(self):
		while self.axes and len(self.axes.lines):
			del self.axes.lines[-1]


class MultiTrendFormatter(object):
	counter = -1
	colors = 'bgrcmyk'

	def __call__(self, data):
		self.counter += 1
		return self.colors[self.counter] + '-'

	def reset(self):
		self.counter = -1


class GasCabinetFormatter(MultiTrendFormatter):
	prevcontroller = None

	def __call__(self, data):
		if data.parameter == 'set point':
			linestyle = '--' # dashed
		else:
			linestyle = '-' # solid
	
		if self.prevcontroller != data.controller:
			self.counter += 1
			self.prevcontroller = data.controller

		return self.colors[self.counter] + linestyle


class MultiTrendPlot(Plot):
	secondaryaxes = None

	def __init__(self, data, secondarydata=None, formatter=None):
		if not isinstance(data, MultiTrendData):
			raise TypeError("data must be a MultiTrendData object (got '%s')" % data.__class__.__name__)
		if secondarydata is not None and not isinstance(data, MultiTrendData):
			raise TypeError("secondarydata must be a MultiTrendData object (got '%s')" % secondarydata.__class__.__name__)
		self.data = data
		self.secondarydata = secondarydata
		if formatter is None:
			self.formatter = MultiTrendFormatter()
		else:
			if not isinstance(formatter, MultiTrendFormatter):
				raise TypeError("formatter must be a MultiTrendFormatter object (got '%s')" % formatter.__class__.__name__)
			self.formatter = formatter

	def build(self, axes):
		self.axes = axes
		self.formatter.reset()
		for d in self.data.iterchannels():
			self.axes.plot(d.time, d.value, self.formatter(d), label=d.label)
		if self.secondarydata:
			for d in self.secondarydata.iterchannels():
				self.secondaryaxes.plot(d.time, d.value, self.formatter(d), label=d.label)
			
			# manually join the legends for both y-axes
			handles, labels = self.axes.get_legend_handles_labels()
			handles2, labels2 = self.secondaryaxes.get_legend_handles_labels()
			handles.extend(handles2)
			labels.extend(labels2)
			if len(handles):
				self.axes.legend(handles, labels)
		else:
			if len(self.axes.get_legend_handles_labels()[0]):
				self.axes.legend()

	def clean(self):
		while self.secondaryaxes and len(self.secondaryaxes.lines):
			del self.secondaryaxes.lines[-1]
		super(MultiTrendPlot, self).clean()


class QMSPlot(MultiTrendPlot):
	def build(self, axes):
		super(QMSPlot, self).build(axes)
		self.axes.set_ylabel('Ion current (A)')
		self.axes.set_yscale('log')


class ImagePlot(Plot):
	def __init__(self, data):
		if not isinstance(data, ImageData):
			raise TypeError("data must be a ImageData object (got '%s')" % data.__class__.__name__)
		self.data = data
	
	def build(self, axes):
		self.axes = axes
		for d in self.data.iterframes():
			ysize, xsize = d.image.shape

			# map the linenunumber to the time axis and the individual points to some arbitrary unit axis
			time, pixel = numpy.meshgrid(numpy.linspace(d.tstart, d.tend, ysize+1), numpy.arange(xsize+1))
			self.axes.axvline(d.tstart, color='g', zorder=0)
			self.axes.axvline(d.tend, color='r', zorder=0)

			# transpose the image data to plot scanlines vertical
			self.axes.pcolormesh(time, pixel, d.image.T, zorder=1)
		self.axes.set_yticks([])


class Data(object):
	def __init__(self, filename, label=None):
		self.filename = filename
		self.label = label


class MultiTrendData(Data):
	def selectchannels(self, condition):
		return SelectedMultiTrendData(self, condition)


class SelectedMultiTrendData(MultiTrendData):
	def __init__(self, parent, condition):
		self.parent = parent
		self.condition = condition

	def iterchannels(self):
		return itertools.ifilter(self.condition, self.parent.iterchannels())


class QMSData(MultiTrendData):
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
		super(QMSData, self).__init__(filename, label)
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


class GasCabinetData(MultiTrendData):
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


class ImageData(Data):
	def apply_filter(self, *filters):
		return ImageDataFilter(self, *filters)


class ChainedImageData(ImageData):
	def __init__(self, *args):
		self.args = args

	def iterframes(self):
		for arg in self.args:
			for frame in arg.iterframes():
				yield frame


class CameraData(Data):
	def __init__(self, filename, label=None):
		super(CameraData, self).__init__(filename, label)
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
		return CameraChannelData(self, channel)


class CameraChannelData(ImageData):
	def __init__(self, cameradata, channel):
		self.cameradata = cameradata
		self.channel = channel

	def iterframes(self):
		for i in range(self.cameradata.getframecount()):
			yield self.cameradata.getdata(self.channel, i)


class ImageDataFilter(ImageData):
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


def BGSubtractLineByLine(frame):
	# FIXME: this modifies the frame in-place, I'm not sure if this is desired behaviour
	new = numpy.zeros(frame.image.shape)
	pixels = numpy.arange(frame.image.shape[1])
	for i, line in enumerate(frame.image):
		slope, intercept, r_value, p_value, stderr = scipy.stats.linregress(pixels, line)
		new[i,:] = line - (slope * pixels + intercept)
	frame.image = new
	return frame

def ClipStdDev(number):
	# FIXME: this modifies the frame in-place, I'm not sure if this is desired behaviour
	def clip(frame):
		avg, stddev = frame.image.mean(), frame.image.std()
		frame.image = numpy.clip(frame.image, avg - number * stddev, avg + number * stddev)
		return frame
	return clip


if __name__ == '__main__':
	f = MainFigurePylab()

	f.add_plot(ImagePlot(ChainedImageData(
			#CameraData('../20101001 CO oxidation/101001_PdNPAl2O3_35nm_Vacuum_tip100930.raw').selectchannel(0),
			#CameraData('../20101001 CO oxidation/101001_PdNPAL2O3_H2_P_05bar_HighT.raw').selectchannel(0),
			CameraData('../20101001 CO oxidation/101001_PdAl2O3_CO_O2_HighT.raw').selectchannel(0),
			CameraData('../20101001 CO oxidation/101001_PdAl2O3_CO_O2_HighT_2.raw').selectchannel(0),
	).apply_filter(BGSubtractLineByLine, ClipStdDev(4))))

	f.add_plot(QMSPlot(
			QMSData('../20101001 CO oxidation/20101001 190122 SEM Airdemo MID.asc').selectchannels(
				lambda d: d.mass in (28, 32, 44)
			)
	))

	gcdata = GasCabinetData('../20101001 CO oxidation/copy of 20101001 gas cabinet data.txt')
	f.add_plot(MultiTrendPlot(
			gcdata.selectchannels(
				lambda d: d.controller in ('MFC CO', 'MFC O2') and d.parameter in ('measure', 'set point')
			),
			gcdata.selectchannels(
				lambda d: d.controller == 'BPC1' and d.parameter in ('measure', 'set point')
			),
			formatter=GasCabinetFormatter()
	))

	f.build()
	pylab.show()
