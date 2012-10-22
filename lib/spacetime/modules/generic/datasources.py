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

import itertools
import os.path
import numpy
import PIL.Image, matplotlib.image

from ... import util


class DataObject(object):
	def __init__(self, **kwargs):
		self.__dict__.update(kwargs)


class DataChannel(DataObject):
	id = None
	time = None
	value = None


class ImageFrame(DataObject):
	tstart = None
	tend = None
	image = None


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

			if self.time_type == 'strptime':
				data = []
				for line in itertools.islice(fp, 0, 10 if probe else None):
					data.append(tuple(util.mpldtstrptime(v.strip(), self.time_strptime) if i in time_columns else float(v) for (i, v) in enumerate(line.strip().split(self.delimiter))))
				self.data = numpy.array(data)
			else:
				if probe:
					data = []
					for line in itertools.islice(fp, 10):
						data.append(tuple(float(i) for i in line.split(self.delimiter)))
					self.data = numpy.array(data)
				else:
					self.data = numpy.loadtxt(fp, delimiter=self.delimiter)

				for i in time_columns:
					self.data[:, i] = self.convert_time(self.data[:, i])
		self.verify_data()


class RGBImage(DataSource):
	def __init__(self, filename, tstart, tend=None):
		super(RGBImage, self).__init__(filename)
		self.tstart = tstart
		self.tend = tend
	
	def getframe(self):
		return ImageFrame(image=matplotlib.image.pil_to_array(PIL.Image.open(self.filename)), tstart=self.tstart, tend=self.tend)
	
	def iterframes(self):
		yield self.getframe()
