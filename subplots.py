from __future__ import division

import numpy
import matplotlib.patches, matplotlib.cm, matplotlib.colors

import datasources
from util import *

class Subplot(object):
	axes = None
	ylim_callback = None

	def __init__(self, data=None):
		self.data = data

	def set_data(self, data):
		self.data = data

	def get_axes_requirements(self):
		return [Struct()] # request a single subplot

	def set_axes(self, axes):
		self.axes = axes[0]

	def setup(self):
		if self.ylim_callback:
			self.axes.callbacks.connect('ylim_changed', self.ylim_callback)

	def draw(self):
		raise NotImplementedError

	def clear(self, quick=False):
		# The quick parameter is set when the entire figure is being cleared;
		# in this case it is sufficient to only clear the internal state of the
		# Subplot and leave the axes untouched
		pass

	def set_ylim_callback(self, func):
		self.ylim_callback = func


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

	def clear(self, quick=False):
		if quick:
			return
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

	def set_data(self, data, secondarydata=None):
		self.secondarydata = secondarydata
		super(DoubleMultiTrend, self).set_data(data)

	def setup(self):
		super(DoubleMultiTrend, self).setup()
		if self.ylim_callback:
			self.secondaryaxes.callbacks.connect('ylim_changed', self.ylim_callback)

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

	def get_axes_requirements(self):
		return [Struct(twinx=True)]

	def set_axes(self, axes):
		self.axes, self.secondaryaxes = axes[0]

	def clear(self, quick=False):
		if quick:
			return
		if self.secondaryaxes:
			del self.secondaryaxes.lines[:]
		self.secondaryaxes.relim()
		super(DoubleMultiTrend, self).clear()


class QMS(MultiTrend):
	def setup(self):
		super(QMS, self).setup()
		self.axes.set_ylabel('Ion current (A)')
		self.axes.set_yscale('log')


class TPDirk(DoubleMultiTrend):
	def __init__(self, data=None, formatter=None):
		self.set_data(data)
		super(TPDirk, self).__init__(self.data, self.secondarydata, formatter)
	
	def set_data(self, data):
		self.realdata = data
		if data:
			self.data = data.selectchannels(lambda x: x.id == 'pressure')
			self.secondarydata = data.selectchannels(lambda x: x.id == 'temperature')
		else:
			self.data = None
			self.secondarydata = None

	def setup(self):
		super(TPDirk, self).setup()
		self.axes.set_ylabel('Pressure (mbar)')
		self.axes.set_yscale('log')
		self.secondaryaxes.set_ylabel('Temperature (K)')


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
	interpolation = 'nearest'
	tzoom = 1
	mode = 'film strip'
	rotate = True

	def __init__(self, *args, **kwargs):
		self.vspans = []
		super(Image, self).__init__(*args, **kwargs)

	def get_axes_requirements(self):
		if self.mode == 'single frame':
			return [Struct(independent_x = True)]
		else:
			return [Struct()]

	def setup(self):
		super(Image, self).setup()
		self.axes.set_yticks([])
		if self.mode == 'single frame':
			self.axes.set_xticks([])
	
	def draw(self):
		if not self.data:
			return

		for d in self.data.iterframes():
			# map the linenunumber to the time axis and the individual points to some arbitrary unit axis
			# transpose the image data to plot scanlines vertical
			ysize, xsize = d.image.shape

			if self.mode == 'single frame':
				if self.rotate:
					image = numpy.rot90(d.image)
				else:
					image = d.image
				self.axes.imshow(image, aspect='equal', cmap=self.colormap, interpolation=self.interpolation)

				for axes in self.parent.shared_axes:
					self.vspans.append((axes, axes.axvspan(d.tstart, d.tend, color='silver', zorder=-1e9)))
			else:
				tendzoom = d.tstart + (d.tend - d.tstart) * self.tzoom
				self.axes.imshow(numpy.rot90(d.image), extent=(d.tstart, tendzoom, 0, ysize+1), aspect='auto', cmap=self.colormap, interpolation=self.interpolation)
				self.axes.add_patch(matplotlib.patches.Rectangle((d.tstart, 0), tendzoom-d.tstart, ysize+1, linewidth=1, edgecolor='black', fill=False))
	
		# imshow() changes the axes xlim/ylim, so go back to something sensible
		self.axes.autoscale_view()
		# NOTE: IMHO the better solution is to change
		# matplotlib.image.ImageAxes.set_extent(); this should call
		# axes.autoscale_view(tight=True) instead of messing with the axes

	def clear(self, quick=False):
		if not quick:
			if self.axes:
				del self.axes.lines[:], self.axes.images[:], self.axes.patches[:]
			for (axes, vspan) in self.vspans:
				axes.patches.remove(vspan)
			self.axes.relim()
		del self.vspans[:]

	def set_colormap(self, colormap):
		self.colormap = colormap
		if self.axes:
 			for image in self.axes.images:
				image.set_cmap(colormap)

	def set_interpolation(self, interpolation):
		self.interpolation = interpolation
		if self.axes:
 			for image in self.axes.images:
				image.set_interpolation(interpolation)

	def set_rotate(self, rotate):
		if rotate == self.rotate:
			return
		self.rotate = rotate

		im = self.axes.images[0]
		# NOTE this uses a feature that is not officially in the matplotlib API
		if rotate:
			im.set_data(numpy.rot90(im._A))
		else:
			im.set_data(numpy.rot90(im._A, 3))
