from __future__ import division

import numpy

import datasources

class Subplot(object):
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


class MultiTrend(Subplot):
	secondaryaxes = None

	def __init__(self, data, secondarydata=None, formatter=None):
		if not isinstance(data, datasources.MultiTrend):
			raise TypeError("data must be a datasources.MultiTrend object (got '%s')" % data.__class__.__name__)
		if secondarydata is not None and not isinstance(data, datasources.MultiTrend):
			raise TypeError("secondarydata must be a datasources.MultiTrend object (got '%s')" % secondarydata.__class__.__name__)
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
		super(MultiTrend, self).clean()


class QMS(MultiTrend):
	def build(self, axes):
		super(QMS, self).build(axes)
		self.axes.set_ylabel('Ion current (A)')
		self.axes.set_yscale('log')


class Image(Subplot):
	def __init__(self, data):
		if not isinstance(data, datasources.Image):
			raise TypeError("data must be a datasources.Image object (got '%s')" % data.__class__.__name__)
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
