from __future__ import division

import numpy
import matplotlib.patches, matplotlib.cm, matplotlib.colors, matplotlib.dates, matplotlib.font_manager, matplotlib.transforms

from ... import util

class Subplot(object):
	axes = None
	marker_callbacks = None
	time_offset = 0.
	time_factor = 1.

	def __init__(self, data=None):
		self.data = data
		self.marker_callbacks = []

	def set_data(self, data):
		self.data = data

	def get_axes_requirements(self):
		return [util.Struct()] # request a single subplot

	def set_axes(self, axes):
		self.axes = axes[0]

	def setup(self):
		# what could possibly go wrong? a lot, but it will do the right thing most of the time
		if not any(i.independent_x for i in self.get_axes_requirements()):
			self.axes.fmt_xdata = matplotlib.dates.DateFormatter('%Y-%m-%d %H:%M:%S.%f', util.localtz)

	def draw(self):
		raise NotImplementedError

	def clear(self, quick=False):
		# The quick parameter is set when the entire figure is being cleared;
		# in this case it is sufficient to only clear the internal state of the
		# Subplot and leave the axes untouched
		self.clear_other_markers(quick=quick)

	@staticmethod
	def autoscale_x(axes):
		# FIXME: Look at Axes.autoscale_view (line 1761) in matplotlib/axes.py
		# See also Plot.autoscale_x_shared
		xshared = axes._shared_x_axes.get_siblings(axes)
		dl = [ax.dataLim for ax in xshared if ax.lines or ax.images or ax.patches]
		if dl:
			bb = matplotlib.transforms.BboxBase.union(dl)
			x0, x1 = bb.intervalx
		else:
			x0, x1 = 0, 1
		XL = axes.xaxis.get_major_locator().view_limits(x0, x1)
		axes.set_xbound(XL)

	@staticmethod
	def autoscale_y(axes):
		y0, y1 = axes.dataLim.intervaly
		YL = axes.yaxis.get_major_locator().view_limits(y0, y1)
		axes.set_ybound(YL)

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


class XAxisHandling(object):
	xlim_callback = None
	xlim_min = 0.
	xlim_max = 1.
	xlim_auto = True
	xlog = False

	def get_axes_requirements(self):
		return [util.Struct(independent_x = True)]

	def set_xlim_callback(self, func):
		self.xlim_callback = func

	def set_xlim(self, min, max, auto):
		self.xlim_min = min
		self.xlim_max = max
		self.xlim_auto = auto
		try:
			self.xlim_rescale()
		except util.SharedXError:
			# this is needed for graphs that can enable/disable the shared x axis
			pass

	def xlim_rescale(self):
		if not self.axes:
			return
		if self.xlim_auto:
			self.autoscale_x(self.axes)
		else:
			self.axes.set_xlim(self.xlim_min, self.xlim_max)

	def set_xlog(self, xlog):
		self.xlog = xlog
		if self.axes:
			self.axes.set_xscale('log' if xlog else 'linear')
		if self.secondaryaxes:
			self.secondaryaxes.set_xscale('log' if xlog else 'linear')


class YAxisHandling(object):
	ylim_callback = None
	ylim_min = 0.
	ylim_max = 1.
	ylim_auto = True
	ylog = False

	def set_ylim_callback(self, func):
		self.ylim_callback = func

	def set_ylim(self, min, max, auto):
		self.ylim_min = min
		self.ylim_max = max
		self.ylim_auto = auto
		self.ylim_rescale()

	def ylim_rescale(self):
		if not self.axes:
			return
		if self.ylim_auto:
			self.autoscale_y(self.axes)
		else:
			self.axes.set_ylim(self.ylim_min, self.ylim_max)

	def set_ylog(self, ylog):
		self.ylog = ylog
		if self.axes:
			self.axes.set_yscale('log' if ylog else 'linear')


class DoubleYAxisHandling(YAxisHandling):
	secondaryaxes = None

	ylim2_min = 0.
	ylim2_max = 1.
	ylim2_auto = True
	ylog2 = False

	def set_ylim2(self, min, max, auto):
		self.ylim2_min = min
		self.ylim2_max = max
		self.ylim2_auto = auto
		self.ylim_rescale()

	def ylim_rescale(self):
		super(DoubleYAxisHandling, self).ylim_rescale()
		if not self.secondaryaxes:
			return
		if self.ylim2_auto:
			self.autoscale_y(self.secondaryaxes)
		else:
			self.secondaryaxes.set_ylim(self.ylim2_min, self.ylim2_max)

	def set_ylog2(self, ylog2):
		self.ylog2 = ylog2
		if self.secondaryaxes:
			self.secondaryaxes.set_yscale('log' if ylog2 else 'linear')

	def get_axes_requirements(self):
		return [util.Struct(twinx=True)]


class MultiTrendFormatter(object):
	counter = -1
	colors = 'bgrcmyk'

	def __call__(self, data):
		self.increase_counter()
		return self.colors[self.counter] + '-'

	def increase_counter(self):
		self.counter = (self.counter + 1) % len(self.colors)

	def reset(self):
		self.counter = -1


class MultiTrend(YAxisHandling, Subplot):
	legend = 'best'
	legendprops = matplotlib.font_manager.FontProperties(size='medium')

	def __init__(self, data=None, formatter=None):
		super(MultiTrend, self).__init__(data)
		if formatter is None:
			self.formatter = MultiTrendFormatter()
		else:
			if not isinstance(formatter, MultiTrendFormatter):
				raise TypeError("formatter must be a MultiTrendFormatter object (got '{0}')".format(formatter.__class__.__name__))
			self.formatter = formatter

	def setup(self):
		super(MultiTrend, self).setup()
		if self.ylim_callback:
			self.axes.callbacks.connect('ylim_changed', self.ylim_callback)

	def get_xdata(self, chandata):
		return self.time_factor*chandata.time + self.time_offset/86400.

	def draw(self):
		if not self.data:
			return
		self.formatter.reset()
		for d in self.data.iterchannels():
			self.axes.plot(self.get_xdata(d), d.value, self.formatter(d), label=d.id)
		self.draw_legend()
		if self.ylog:
			self.axes.set_yscale('log')

	def clear(self, quick=False):
		if not quick:
			if self.axes:
				del self.axes.lines[:]
				self.axes.relim()
		super(MultiTrend, self).clear(quick)

	def set_legend(self, legend):
		self.legend = legend
		if legend:
			self.draw_legend()
		elif self.axes:
			self.axes.legend_ = None

	def draw_legend(self):
		if self.legend and self.axes and self.axes.get_legend_handles_labels()[0]:
			self.axes.legend(loc=self.legend, prop=self.legendprops)


class DoubleMultiTrend(MultiTrend, DoubleYAxisHandling):
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
				self.secondaryaxes.plot(self.get_xdata(d), d.value, self.formatter(d), label=d.id)
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
				self.secondaryaxes.legend(handles, labels, prop=self.legendprops)

	def set_legend(self, legend):
		if not legend and self.secondaryaxes:
			self.secondaryaxes.legend_ = None
		super(DoubleMultiTrend, self).set_legend(legend)

	def set_axes(self, axes):
		self.axes, self.secondaryaxes = axes[0]

	def clear(self, quick=False):
		if not quick:
			if self.secondaryaxes:
				del self.secondaryaxes.lines[:]
			self.secondaryaxes.relim()
		super(DoubleMultiTrend, self).clear(quick)


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
			return [util.Struct(independent_x = True)]
		else:
			return [util.Struct()]

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
				# somehow, origin=upper is not respected here for imshow, fix manually
				image = d.image[::-1,:]
				if self.rotate:
					image = numpy.rot90(image, 3)
				self.axes.imshow(image, aspect='equal', cmap=self.colormap, interpolation=self.interpolation)

				self.set_other_markers(tstart, tend)
			else:
				tendzoom = tstart + (tend - tstart) * self.tzoom
				self.axes.imshow(numpy.rot90(d.image), extent=(tstart, tendzoom, 0, 1), aspect='auto', cmap=self.colormap, interpolation=self.interpolation)
				self.axes.add_patch(matplotlib.patches.Rectangle((tstart, 0), tendzoom-tstart, 1, linewidth=1, edgecolor='black', fill=False))
	
		# imshow() changes the axes xlim/ylim, so go back to something sensible
		self.ylim_rescale()
		try:
			self.xlim_rescale()
		except util.SharedXError:
			pass
		# NOTE: IMHO the better solution is to change
		# matplotlib.image.ImageAxes.set_extent(); this should call
		# axes.autoscale_view(tight=True) instead of messing with the axes

	def ylim_rescale(self):
		self.autoscale_y(self.axes)

	def xlim_rescale(self):
		if self.mode == 'film strip':
			raise util.SharedXError
		self.autoscale_x(self.axes)

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
			im.set_data(numpy.rot90(im._A, 3))
		else:
			im.set_data(numpy.rot90(im._A))

	def set_marker(self, left, right=None):
		# don't allow markers on this kind of plot, doesn't play nice with clear()
		return None
