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

import itertools
import os.path
import numpy
import PIL.Image
import struct
import ctypes
import pyglet

from ... import util
from . import dm3lib


class DataObject(object):
	def __init__(self, **kwargs):
		self.__dict__.update(kwargs)

	def clone(self, **kwargs):
		return self.__class__.transclone(self, **kwargs)

	@classmethod
	def transclone(cls, source, **kwargs):
		new = cls(**source.__dict__)
		new.__dict__.update(kwargs)
		return new


class DataChannel(DataObject):
	id = None
	time = None
	value = None


class ImageFrame(DataObject):
	tstart = None
	tend = None
	image = None
	pixelsize = None
	pixelunit = None

	def get_extent(self):
		if hasattr(self.image, 'shape'):
			if self.pixelsize:
				return (0, self.pixelsize * self.image.shape[1], 0, self.pixelsize * self.image.shape[0])
			else:
				return (0, self.image.shape[1], 0, self.image.shape[0])


class FFTImageFrame(ImageFrame):
	def get_extent(self):
		if hasattr(self.image, 'shape'):
			if self.pixelsize:
				return (-self.image.shape[1]*self.pixelsize/2,  self.image.shape[1]*self.pixelsize/2, -self.image.shape[0]*self.pixelsize/2,  self.image.shape[0]*self.pixelsize/2)
			else:
				return (-.5, .5, -.5, .5)


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
		for f in self.filters:
			data = f(data)
		return data

	def apply_filter(self, *filters):
		self.filters.extend(filters)
		return self


class CSVFactory(object):
	def __init__(self, **props):
		self.props = props

	def __call__(self, filename):
		obj = CSV()
		obj.set_config(filename, **self.props)
		obj.load()
		return obj


class CSVFormatError(Exception):
	pass


class CSV(MultiTrend):
	delimiter = '\t'
	skip_lines = 0
	time_column = 0
	time_type = 'unix'
	time_strptime = '%Y-%m-%d %H:%M:%S'
	time_channel_headers = set(['Time'])

	def iterchannelnames(self):
		time_columns = self.get_time_columns()
		return (lbl for (i, lbl) in enumerate(self.channel_labels) if i not in time_columns)

	def get_time_columns(self):
		if self.time_column == 'auto':
			if set(self.channel_labels) & self.time_channel_headers:
				return [i for (i,l) in enumerate(self.channel_labels) if l in self.time_channel_headers]
			else:
				return [0]
		try:
			return list(self.time_column)
		except TypeError:
			return [self.time_column]

	def convert_time(self, data):
		if self.time_type == 'matplotlib':
			return data
		elif self.time_type == 'unix':
			return numpy.fromiter((util.mpldtfromtimestamp(i) for i in data), dtype=float)
		elif self.time_type == 'labview':
			# Labview uses the number of seconds since 1-1-1904 00:00:00 UTC.
			# mpldtfromdatetime(datetime.datetime(1904, 1, 1, 0, 0, 0, tzinfo=pytz.utc)) = 695056
			return data / 86400. + 695056
		raise RuntimeError('not reached')

	def get_channel_kwargs(self, label, i):
		return dict(id=label)

	def verify_data(self):
		assert len(self.channel_labels) == self.data.shape[1]

	def iterchannels(self):
		time_columns = self.get_time_columns()
		if time_columns[0] != 0:
			time = self.data[:, time_columns[0]]

		for i, label in enumerate(self.channel_labels):
			if time_columns and i == time_columns[0]:
				time = self.data[:, time_columns.pop(0)]
			else:
				yield DataChannel(time=time, value=self.data[:, i].astype(float), **self.get_channel_kwargs(label, i))

	def __init__(self):
		pass

	def set_config(self, filename, delimiter='\t', skip_lines=0, time_type='matplotlib', time_strptime=None, time_column='auto'):
		self.filename = filename
		self.delimiter = delimiter
		self.skip_lines = skip_lines
		assert time_type in ('unix', 'matplotlib', 'labview', 'strptime')
		self.time_type = time_type
		self.time_strptime = time_strptime
		self.time_column = time_column

	def read_header(self, fp):
		for i in range(self.skip_lines):
			fp.readline()

		line = fp.readline()
		if self.delimiter not in line:
			raise CSVFormatError('header line does not contain delimiter')
		self.channel_labels = [i.strip() for i in line.split(self.delimiter)]

	@classmethod
	def probe_column_names(cls, filename, delimiter, skip_lines):
		obj = cls()
		obj.delimiter = delimiter
		obj.skip_lines = skip_lines
		try:
			with open(filename) as fp:
				obj.read_header(fp)
				return obj.channel_labels
		except:
			return []

	def load(self, probe=False):
		with open(self.filename) as fp:
			self.read_header(fp)

			time_columns = self.get_time_columns()

			if probe:
				fp = itertools.islice(fp, 10)

			if self.time_type == 'strptime':
				time_columns = set(time_columns)
				self.data = numpy.array([tuple(util.mpldtstrptime(v.strip(), self.time_strptime) if i in time_columns else float(v) for (i, v) in enumerate(line.split(self.delimiter))) for line in fp])
			else:
				self.data = util.loadtxt(fp, delimiter=self.delimiter)

				for i in time_columns:
					self.data[:, i] = self.convert_time(self.data[:, i])
		self.verify_data()


class CustomCSV(CSV):
	def __init__(self, filename):
		MultiTrend.__init__(self, filename) # skip CSV constructor (it's a no-op anyway)
		self.load()


class RGBImage(DataSource):
	def __init__(self, filename, tstart, tend=None):
		super(RGBImage, self).__init__(filename)
		self.tstart = tstart
		self.tend = tend
		self.imageframe = ImageFrame(image=self.loadfile(), tstart=self.tstart, tend=self.tend, **self.get_scale())
	
	def iterframes(self):
		yield self.imageframe

	@classmethod
	def detect_subclass(cls, filename):
		root, ext = os.path.splitext(filename)
		if ext.lower() == '.dm3':
			return DM3Image
		try:
			int(ext[1:])
		except:
			return PILImage
		else:
			return DM3Image

	@classmethod
	def autodetect(cls, filename, tstart, tend=None):
		return cls.detect_subclass(filename)(filename, tstart, tend)

	@classmethod
	def autodetect_timeinfo(cls, filename):
		return cls.detect_subclass(filename).get_timeinfo(filename)

	def get_scale(self):
		return dict()

	def is_greyscale(self):
		raise NotImplementedError


# utility functions for TVIPS TemData header parsing
def _read_long(fp):
	return struct.unpack('<l', fp.read(4))[0]

def _read_float(fp):
	return struct.unpack('<f', fp.read(4))[0]


class PILImage(RGBImage):
	def loadfile(self):
		self.im = PIL.Image.open(self.filename)
		return util.pil_to_array(self.im)

	@staticmethod
	def get_timeinfo(filename):
		im = PIL.Image.open(filename)
		if hasattr(im, 'tag') and im.tag.has_key(37706): # TVIPS TemData header
			offset = im.tag[37706][0]
			fp = im.fp
			fp.seek(offset)
			if _read_long(fp) == 2:
				fp.seek(offset + 584)
				date = _read_long(fp)
				year, month, day = date//65536, (date//256) % 256, date % 256
				time = _read_long(fp)
				hour, min, sec = time//3600, (time//60) % 60, time % 60
				timestamp = util.mpldtlikedatetime(year, month, day, hour, min, sec)

				fp.seek(offset + 3952)
				exposure = _read_float(fp)
				
				return timestamp, exposure

		info = im._getexif()
		timestamp = util.mpldtstrptime(info[0x132], '%Y:%m:%d %H:%M:%S')
		exposure = info.get(0x829a, (0,1))
		exposure = 1e3 * exposure[0] / exposure[1]
		return timestamp, exposure

	def get_scale(self):
		if hasattr(self.im, 'tag') and self.im.tag.has_key(37706): # TVIPS TemData header
			offset = self.im.tag[37706][0]
			with open(self.filename, 'rb') as fp:
				fp.seek(offset)
				if _read_long(fp) == 2:
					fp.seek(offset + 2968)
					size = _read_float(fp)
					return dict(pixelsize=size, pixelunit='nm')
		return dict()

	def is_greyscale(self):
		return self.im.mode[0] in 'LIF'


class DM3Scaling(object):
	def get_scale(self):
		size = float(self.dm3.tags['root.ImageList.1.ImageData.Calibrations.Dimension.0.Scale'])
		unit = self.dm3.tags['root.ImageList.1.ImageData.Calibrations.Dimension.0.Units']
		return dict(pixelsize=size, pixelunit=unit)


class DM3Image(DM3Scaling, RGBImage):
	def loadfile(self):
		self.dm3 = dm3lib.DM3(self.filename)
		return self.dm3.getImageData() 

	@staticmethod
	def get_timeinfo(filename):
		dm3 = dm3lib.DM3(filename)
		date = dm3.tags['root.ImageList.1.ImageTags.DataBar.Acquisition Date']
		time = dm3.tags['root.ImageList.1.ImageTags.DataBar.Acquisition Time']
		timestamp = util.mpldtstrptime('{0} {1}'.format(date, time), '%m/%d/%Y %I:%M:%S %p')
		exposure = float(dm3.tags['root.ImageList.1.ImageTags.Acquisition.Parameters.High Level.Exposure (s)']) * 1e3
		return timestamp, exposure

	def is_greyscale(self):
		return True


class DM3Stack(DataSource, DM3Scaling):
	frameno = 0

	def __init__(self, *args, **kwargs):
		super(DM3Stack, self).__init__(*args, **kwargs)
		self.dm3 = dm3lib.DM3(self.filename)
		self.framecount = int(self.dm3.tags['root.ImageList.1.ImageData.Dimensions.2'])

	def set_settings(self, frameno, tstart, exposure, delay):
		# unfortunately, there is no timing info embedded in these files...
		self.frameno = frameno
		self.tstart = tstart
		self.exposure = exposure
		self.delay = delay

	def iterframes(self):
		tstart = self.tstart + self.frameno * (self.exposure + self.delay)
		tend = tstart + self.exposure
		yield ImageFrame(image=self.dm3.getImageData(self.frameno), tstart=tstart, tend=tend, **self.get_scale())


class AveragedImage(DataSource):
	def __init__(self, images):
		frames = list(itertools.chain(*(im.iterframes() for im in images)))

		if not all(im.is_greyscale() for im in images) or not all(f.image.ndim == 2 for f in frames):
			raise ValueError('cannot average: not all images are greyscale')

		if len(set(f.image.shape for f in frames)) != 1:
			raise ValueError('cannot average: not all images have the same shape')
		
		tstart = min(f.tstart for f in frames)
		tend = max(f.tend for f in frames)
		pixelsize = set(f.pixelsize for f in frames)
		if len(pixelsize) == 1:
			pixelsize = pixelsize.pop()
		else:
			pixelsize = None
		pixelunit = set(f.pixelunit for f in frames)
		if len(pixelunit) == 1:
			pixelunit = pixelunit.pop()
		else:
			pixelunit = None

		image = numpy.dstack(tuple(f.image for f in frames)).mean(axis=2)
		self.imageframe = ImageFrame(image=image, tstart=tstart, tend=tend, pixelsize=pixelsize, pixelunit=pixelunit)
	
	def iterframes(self):
		yield self.imageframe


class Video(DataSource):
	frameno = 0

	def __init__(self, filename):
		self.filename = filename
		self.reload_video()

	def count_frames(self):
		while self.video.get_next_video_frame() is not None:
			self.last_frameno += 1
		count = self.last_frameno + 1
		self.reload_video()
		return count

	def reload_video(self):
		self.video = pyglet.media.load(self.filename)
		if not self.video.video_format:
			raise pyglet.media.MediaException("'{0}' does not appear to be a video file".format(self.filename))
		self.last_frameno = -1
		self.timestamp = 0
		self.frame = None

	def set_tzero(self, tzero):
		self.tzero = tzero

	def set_frameno(self, frameno):
		self.frameno = frameno

	def stepframe(self):
		self.last_frameno += 1
		timestamp = self.video.get_next_video_timestamp()
		if timestamp is None:
			return
		self.timestamp = timestamp
		im = self.video.get_next_video_frame().get_image_data()
		pilim = PIL.Image.fromstring('RGB', (im.width, im.height), im.get_data('RGB', im.width * 3))
		self.frame = util.pil_to_array(pilim)

	def iterframes(self):
		if self.frameno < self.last_frameno:
			self.reload_video()
		for i in range(self.frameno - self.last_frameno):
			self.stepframe()
		yield ImageFrame(image=self.frame, tstart=self.tzero + self.timestamp)
