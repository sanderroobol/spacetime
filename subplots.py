from __future__ import division

import numpy
import matplotlib.patches, matplotlib.cm, matplotlib.colors

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
	legend = True

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
			self.axes.plot(d.time, d.value, self.formatter(d), label=d.id)
		self.draw_legend()

	def clear(self):
		if self.axes:
			del self.axes.lines[:]
		self.axes.relim()

	def set_legend(self, legend):
		self.legend = legend
		if legend:
			self.draw_legend()
		elif self.axes:
			self.axes.legend_ = None

	def draw_legend(self):
		if self.legend and self.axes and self.axes.get_legend_handles_labels()[0]:
			self.axes.legend()


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
				self.secondaryaxes.plot(d.time, d.value, self.formatter(d), label=d.id)
			self.draw_legend()

	def draw_legend(self):
		if self.legend:
			# manually join the legends for both y-axes
			handles, labels = self.axes.get_legend_handles_labels()
			handles2, labels2 = self.secondaryaxes.get_legend_handles_labels()
			handles.extend(handles2)
			labels.extend(labels2)
			self.axes.legend_ = None
			if len(handles):
				self.secondaryaxes.legend(handles, labels)

	def set_legend(self, legend):
		if not legend:
			self.secondaryaxes.legend_ = None
		super(DoubleMultiTrend, self).set_legend(legend)

	def axes_requirements(self):
		return [Struct(twinx=True)]

	def register_axes(self, axes):
		self.axes, self.secondaryaxes = axes[0]

	def clear(self):
		if self.secondaryaxes:
			del self.secondaryaxes.lines[:]
		self.secondaryaxes.relim()
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

	def draw(self):
		super(GasCabinet, self).draw()
		self.axes.set_ylabel('')
		self.secondaryaxes.set_ylabel('')

		if self.data and list(self.data.iterchannelnames()):
			if all(chan.startswith('MF') for chan in self.data.iterchannelnames()):
				self.axes.set_ylabel('Mass flow (ml/min)')
			elif all(chan.startswith('BPC') for chan in self.data.iterchannelnames()):
				self.axes.set_ylabel('Pressure (bar)')

		if self.secondarydata and list(self.secondarydata.iterchannelnames()):
			if all(chan.startswith('MF') for chan in self.secondarydata.iterchannelnames()):
				self.secondaryaxes.set_ylabel('Mass flow (ml/min)')
			elif all(chan.startswith('BPC') for chan in self.secondarydata.iterchannelnames()):
				self.secondaryaxes.set_ylabel('Pressure (bar)')


class Image(Subplot):
	colormap = 'gist_heat'

	def setup(self):
		self.axes.set_yticks([])
	
	def draw(self):
		if not self.data:
			return

		for d in self.data.iterframes():
			# map the linenunumber to the time axis and the individual points to some arbitrary unit axis
			# transpose the image data to plot scanlines vertical
			ysize, xsize = d.image.shape
			self.axes.imshow(d.image.T, extent=(d.tstart, d.tend, 0, ysize+1), aspect='auto', cmap=self.colormap)
			self.axes.add_patch(matplotlib.patches.Rectangle((d.tstart, 0), d.tend-d.tstart, ysize+1, linewidth=1, edgecolor='black', fill=False))

			# indicate beginning and end of frames
			#self.axes.axvline(d.tstart, color='g', zorder=0)
			#self.axes.axvline(d.tend, color='r', zorder=0)

		# imshow() changes the axes xlim/ylim, so go back to something sensible
		self.axes.autoscale_view()
		# NOTE: IMHO the better solution is to change
		# matplotlib.image.ImageAxes.set_extent(); this should call
		# axes.autoscale_view(tight=True) instead of messing with the axes

	def clear(self):
		if self.axes:
			del self.axes.lines[:], self.axes.images[:], self.axes.patches[:]
		self.axes.relim()

	def set_colormap(self, colormap):
		self.colormap = colormap
		if self.axes:
 			for image in self.axes.images:
				image.set_cmap(colormap)

