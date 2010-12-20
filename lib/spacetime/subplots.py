from __future__ import division

import numpy
import matplotlib.patches, matplotlib.cm, matplotlib.colors, matplotlib.dates

from . import datasources
from .util import *

class Subplot(object):
	axes = None
	ylim_callback = None
	marker_callbacks = None
	time_offset = 0.
	time_factor = 1.

	def __init__(self, data=None):
		self.data = data
		self.marker_callbacks = []

	def set_data(self, data):
		self.data = data

	def get_axes_requirements(self):
		return [Struct()] # request a single subplot

	def set_axes(self, axes):
		self.axes = axes[0]

	def setup(self):
		self.axes.fmt_xdata = matplotlib.dates.DateFormatter('%Y-%m-%d %H:%M:%S.%f')
		if self.ylim_callback:
			self.axes.callbacks.connect('ylim_changed', self.ylim_callback)

	def draw(self):
		raise NotImplementedError

	def clear(self, quick=False):
		# The quick parameter is set when the entire figure is being cleared;
		# in this case it is sufficient to only clear the internal state of the
		# Subplot and leave the axes untouched
		self.clear_other_markers(quick=quick)

	def set_ylim_callback(self, func):
		self.ylim_callback = func

	def clear_other_markers(self, quick=False):
		if not quick:
			for m in self.marker_callbacks:
				if m is not None:
					m()
		self.marker_callbacks = []

	def set_other_markers(self, left, right=None):
		for sp in self.parent.subplots:
			if sp is self:
				continue
			self.marker_callbacks.append(sp.set_marker(left, right))

	def set_marker(self, left, right=None):
		return self.set_axes_marker(self.axes, left, right)
	
	@staticmethod
	def set_axes_marker(ax, left, right):
		if right is not None:
			vspan = ax.axvspan(left, right, color='silver', zorder=-1e9)
			return lambda: ax.patches.remove(vspan)
		else:
			line = ax.axvline(left, color='silver', zorder=-1e9)
			return lambda: ax.lines.remove(line)

	def adjust_time(self, offset, factor=1.):
		self.time_offset = offset
		self.time_factor = factor


class MultiTrendFormatter(object):
	counter = -1
	colors = 'bgrcmyk'

	def __call__(self, data):
		self.counter = (self.counter + 1) % len(self.colors)
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
	ylog = False

	def __init__(self, data=None, formatter=None):
		super(MultiTrend, self).__init__(data)
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
			self.axes.plot(self.time_factor*d.time + self.time_offset/86400., d.value, self.formatter(d), label=d.id)
		self.draw_legend()
		if self.ylog:
			self.axes.set_yscale('log')

	def clear(self, quick=False):
		if not quick:
			if self.axes:
				del self.axes.lines[:]
				self.axes.relim()
		super(MultiTrend, self).clear(quick)

	def set_ylog(self, ylog):
		self.ylog = ylog
		if self.axes:
			self.axes.set_yscale('log' if ylog else 'linear')

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
	secondaryaxes = None
	ylog2 = False

	def __init__(self, data=None, secondarydata=None, formatter=None):
		self.secondarydata = secondarydata
		super(DoubleMultiTrend, self).__init__(data, formatter)

	def set_data(self, data, secondarydata=None):
		self.secondarydata = secondarydata
		super(DoubleMultiTrend, self).set_data(data)

	def setup(self):
		super(DoubleMultiTrend, self).setup()
		self.secondaryaxes.fmt_xdata = self.axes.fmt_xdata
		if self.ylim_callback:
			self.secondaryaxes.callbacks.connect('ylim_changed', self.ylim_callback)

	def draw(self):
		super(DoubleMultiTrend, self).draw()
		if self.secondarydata:
			for d in self.secondarydata.iterchannels():
				self.secondaryaxes.plot(self.time_factor*d.time + self.time_offset/86400., d.value, self.formatter(d), label=d.id)
			self.draw_legend()
			if self.ylog2:
				self.secondaryaxes.set_yscale('log')

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

	def set_ylog2(self, ylog2):
		self.ylog2 = ylog2
		if self.secondaryaxes:
			self.secondaryaxes.set_yscale('log' if ylog2 else 'linear')

	def set_legend(self, legend):
		if not legend and self.secondaryaxes:
			self.secondaryaxes.legend_ = None
		super(DoubleMultiTrend, self).set_legend(legend)

	def get_axes_requirements(self):
		return [Struct(twinx=True)]

	def set_axes(self, axes):
		self.axes, self.secondaryaxes = axes[0]

	def clear(self, quick=False):
		if not quick:
			if self.secondaryaxes:
				del self.secondaryaxes.lines[:]
			self.secondaryaxes.relim()
		super(DoubleMultiTrend, self).clear(quick)


class QMS(MultiTrend):
	def setup(self):
		super(QMS, self).setup()
		self.axes.set_ylabel('Ion current (A)')


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


class CV(Subplot):
	x = y = None
	markers = None, None
	marker_points = None, None

	def get_axes_requirements(self):
		return [Struct(independent_x = True)]

	def set_data(self, x, y):
		self.x = next(x.iterchannels())
		self.y = next(y.iterchannels())

	def draw(self):
		if not self.x:
			return
		self.axes.plot(self.x.value, self.y.value, 'b-')
		self.plot_marker()

	def clear(self, quick=False):
		if not quick:
			if self.axes:
				del self.axes.lines[:]
			self.axes.relim()
		super(CV, self).clear(quick)

	def clear_marker(self):
		left, right = self.marker_points
		if left:
			self.axes.lines.remove(left)
		if right:
			self.axes.lines.remove(right)
		self.markers = self.marker_points = None, None

	def set_marker(self, left, right=None):
		self.markers = left, right
		if self.x:
			self.plot_marker()
		return self.clear_marker

	def plot_marker(self):
		left, right = self.markers

		index_left = numpy.searchsorted(self.x.time, left, 'left')
		if index_left == self.x.time.size:
			index_left -= 1

		left_point = self.axes.plot([self.x.value[index_left]], [self.y.value[index_left]], 'go')[0]
		if right is None:
			self.marker_points = left_point, None
		else:
			index_right = numpy.searchsorted(self.x.time, right, 'right')
			if index_right == self.x.time.size:
				index_right -= 1
			right_point = self.axes.plot([self.x.value[index_right]], [self.y.value[index_right]], 'ro')[0]
			self.marker_points = left_point, right_point


class Image(Subplot):
	colormap = 'afmhot'
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
			self.axes.fmt_xdata = None
	
	def draw(self):
		if not self.data:
			return

		for d in self.data.iterframes():
			# map the linenunumber to the time axis and the individual points to some arbitrary unit axis
			# transpose the image data to plot scanlines vertical
			ysize, xsize = d.image.shape
			tstart = self.time_factor * d.tstart + self.time_offset / 86400.
			tend = self.time_factor * d.tend + self.time_offset / 86400.

			if self.mode == 'single frame':
				if self.rotate:
					image = numpy.rot90(d.image)
				else:
					image = d.image
				self.axes.imshow(image, aspect='equal', cmap=self.colormap, interpolation=self.interpolation)

				self.set_other_markers(tstart, tend)
			else:
				tendzoom = tstart + (tend - tstart) * self.tzoom
				self.axes.imshow(numpy.rot90(d.image), extent=(tstart, tendzoom, 0, 1), aspect='auto', cmap=self.colormap, interpolation=self.interpolation)
				self.axes.add_patch(matplotlib.patches.Rectangle((tstart, 0), tendzoom-tstart, 1, linewidth=1, edgecolor='black', fill=False))
	
		# imshow() changes the axes xlim/ylim, so go back to something sensible
		self.axes.autoscale_view()
		# NOTE: IMHO the better solution is to change
		# matplotlib.image.ImageAxes.set_extent(); this should call
		# axes.autoscale_view(tight=True) instead of messing with the axes

	def clear(self, quick=False):
		if not quick:
			if self.axes:
				del self.axes.lines[:], self.axes.images[:], self.axes.patches[:]
			self.axes.relim()
		super(Image, self).clear(quick)

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

	def set_marker(self, left, right=None):
		# don't allow markers on this kind of plot, doesn't play nice with clear()
		return None
