from __future__ import division

import numpy

import datasources
from util import *

class Subplot(object):
	axes = None

	def __init__(self, data=None):
		self.data = data

	def retarget(self, data):
		self.data = data

	def axes_requirements(self):
		return [Struct()] # request a single subplot

	def register_axes(self, axes):
		self.axes = axes[0]

	def setup(self):
		pass

	def draw(self):
		raise NotImplementedError

	def clear(self):
		pass


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

	def reset(self):
		self.prevcontroller = None
		super(GasCabinetFormatter, self).reset()

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
	def __init__(self, data=None, formatter=None):
		self.data = data
		if formatter is None:
			self.formatter = MultiTrendFormatter()
		else:
			if not isinstance(formatter, MultiTrendFormatter):
				raise TypeError("formatter must be a MultiTrendFormatter object (got '%s')" % formatter.__class__.__name__)
			self.formatter = formatter

	def draw(self):
		if not self.data:
			return
		self.formatter.reset()
		for d in self.data.iterchannels():
			self.axes.plot(d.time, d.value, self.formatter(d), label=d.label)
		if len(self.axes.get_legend_handles_labels()[0]):
			self.axes.legend()

	def clear(self):
		while self.axes and len(self.axes.lines):
			del self.axes.lines[-1]


class DoubleMultiTrend(MultiTrend):
	def __init__(self, data=None, secondarydata=None, formatter=None):
		self.secondarydata = secondarydata
		super(DoubleMultiTrend, self).__init__(data, formatter)

	def retarget(self, data, secondarydata=None):
		self.secondarydata = secondarydata
		super(DoubleMultiTrend, self).retarget(data)

	def draw(self):
		super(DoubleMultiTrend, self).draw()
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

	def axes_requirements(self):
		return [Struct(twinx=True)]

	def register_axes(self, axes):
		self.axes, self.secondaryaxes = axes[0]

	def clear(self):
		while self.secondaryaxes and len(self.secondaryaxes.lines):
			del self.secondaryaxes.lines[-1]
		super(DoubleMultiTrend, self).clear()


class QMS(MultiTrend):
	def setup(self):
		self.axes.set_ylabel('Ion current (A)')
		self.axes.set_yscale('log')


class GasCabinet(DoubleMultiTrend):
	def __init__(self, data=None, secondarydata=None, formatter=None):
		if formatter is None:
			formatter = GasCabinetFormatter()
		super(GasCabinet, self).__init__(data, secondarydata, formatter)


class Image(Subplot):
	def setup(self):
		self.axes.set_yticks([])
	
	def draw(self):
		if not self.data:
			return

		for d in self.data.iterframes():
			# map the linenunumber to the time axis and the individual points to some arbitrary unit axis
			# transpose the image data to plot scanlines vertical
			ysize, xsize = d.image.shape
			self.axes.imshow(d.image.T, extent=(d.tstart, d.tend, 0, ysize+1), aspect='auto', zorder=1)

			# indicate beginning and end of frames
			self.axes.axvline(d.tstart, color='g', zorder=0)
			self.axes.axvline(d.tend, color='r', zorder=0)

		# imshow() changes the axes xlim/ylim, so go back to something sensible
		self.axes.autoscale_view()
		# NOTE: IMHO the better solution is to change
		# matplotlib.image.ImageAxes.set_extent(); this should call
		# axes.autoscale_view(tight=True) instead of messing with the axes

	def clear(self):
		while self.axes and len(self.axes.lines):
			del self.axes.lines[-1]
		while self.axes and len(self.axes.images):
			del self.axes.images[-1]


