import itertools
import time
import numpy

from ... import util

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

class CSV(MultiTrend):
	time_column = 0
	time_type = 'unix'
	time_strptime = '%Y-%m-%d %H:%M:%S'
	time_channel_headers = set('Time')

	@classmethod
	def factory(klass, **props):
		def _factory(*args, **kwargs):
			obj = klass(*args, **kwargs)
			obj.__dict__.update(props)
			return obj
		return _factory

	def set_header(self, line):
		self.channel_labels = line.strip().split('\t')

	def iterchannelnames(self):
		return iter(self.channel_labels)

	def get_time_columns(self):
		if self.time_column == 'auto':
			if set(self.channel_labels) & self.time_channel_headers:
				return (i for (i,l) in enumerate(self.channel_labels) if l in self.time_channel_headers)
			else:
				return [0]
		try:
			return iter(self.time_column)
		except TypeError:
			return [self.time_column]

	def parse_time(self, data):
		if self.time_type == 'matplotlib':
			return data
		elif self.time_type == 'unix':
			return numpy.fromiter((util.mpldtfromtimestamp(i) for i in data), dtype=float)
		elif self.time_type == 'labview':
			# Labview uses the number of seconds since 1-1-1904 00:00:00 UTC.
			# mpldtfromdatetime(datetime.datetime(1904, 1, 1, 0, 0, 0, tzinfo=pytz.utc)) = 695056
			return data / 86400. + 695056
		elif self.time_type == 'strptime':
			try:
				return numpy.fromiter((time.strptime(i, self.strptime) for i in data), dtype=float)
			except TypeError:
				return time.strptime(data, self.strptime)	

	def get_channel_kwargs(self, label, i):
		return dict(id=label)

	def verify_data(self, data):
		pass

	def iterchannels(self):
			time_columns = list(self.get_time_columns())
			if time_columns[0] != 0:
				time = self.parse_time(self.data[:,time_columns[0]])

			for i, label in enumerate(self.channel_labels):
				if time_columns and i == time_columns[0]:
					time = self.parse_time(self.data[:,time_columns.pop(0)])
				else:
					yield util.Struct(time=time, value=self.data[:,i], **self.get_channel_kwargs(label, i))

	def __init__(self, *args, **kwargs):
		super(CSV, self).__init__(*args, **kwargs)
		with open(self.filename) as fp:
			self.set_header(fp.readline())
			self.data = numpy.loadtxt(fp)
		self.verify_data(self.data)
