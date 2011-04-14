import itertools

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
		for filter in self.filters:
			data = filter(data)
		return data

	def apply_filter(self, *filters):
		self.filters.extend(filters)
		return self
