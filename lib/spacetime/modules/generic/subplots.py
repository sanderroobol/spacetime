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

from __future__ import division

import numpy
import matplotlib.cbook, matplotlib.cm, matplotlib.colors, matplotlib.dates, matplotlib.font_manager, matplotlib.offsetbox, matplotlib.patches, matplotlib.transforms

from ... import util

class LogNorm(matplotlib.colors.LogNorm):
	# directly copied from matplotlib.colors.LogNorm.__call__, but with the ma.masked_less_equal line commented out to fix clipping
    def __call__(self, value, clip=None):
        if clip is None:
            clip = self.clip

        result, is_scalar = self.process_value(value)

        #result = ma.masked_less_equal(result, 0, copy=False)

        self.autoscale_None(result)
        vmin, vmax = self.vmin, self.vmax
        if vmin > vmax:
            raise ValueError("minvalue must be less than or equal to maxvalue")
        elif vmin <= 0:
            raise ValueError("values must all be positive")
        elif vmin == vmax:
            result.fill(0)
        else:
            if clip:
                mask = numpy.ma.getmask(result)
                result = numpy.ma.array(numpy.clip(result.filled(vmax), vmin, vmax),
                                  mask=mask)
            # in-place equivalent of above can be much faster
            resdat = result.data
            mask = result.mask
            if mask is numpy.ma.nomask:
                mask = (resdat <= 0)
            else:
                mask |= resdat <= 0
            matplotlib.cbook._putmask(resdat, mask, 1)
            numpy.log(resdat, resdat)
            resdat -= numpy.log(vmin)
            resdat /= (numpy.log(vmax) - numpy.log(vmin))
            result = numpy.ma.array(resdat, mask=mask, copy=False)
        if is_scalar:
            result = result[0]
        return result

class AxesRequirements(object):
	independent_x = False
	size = 1
	twinx = False
	
	def __init__(self, **kwargs):
		self.__dict__.update(kwargs)

class Subplot(object):
	axes = None
	time_offset = 0.
	time_factor = 1.
	size = 1

	def __init__(self, data=None):
		self.data = data

	def set_data(self, data):
		self.data = data

	def get_axes_requirements(self):
		return [AxesRequirements(size=self.size)] # request a single subplot

	def set_axes(self, axes):
		self.axes = axes[0]

	def setup(self):
		# what could possibly go wrong? a lot, but it will do the right thing most of the time
		if not self.parent.rezero and not any(i.independent_x for i in self.get_axes_requirements()):
			self.axes.fmt_xdata = matplotlib.dates.DateFormatter('%Y-%m-%d %H:%M:%S.%f', util.localtz)

	def draw(self):
		raise NotImplementedError

	def clear(self, quick=False):
		# The quick parameter is set when the entire figure is being cleared;
		# in this case it is sufficient to only clear the internal state of the
		# Subplot and leave the axes untouched
		pass

	def autoscale_x(self, axes):
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
		self.ax_set_xlim(axes, *XL)

	def autoscale_y(self, axes):
		y0, y1 = axes.dataLim.intervaly
		YL = axes.yaxis.get_major_locator().view_limits(y0, y1)
		self.ax_set_ylim(axes, *YL)

	def draw_markers(self):
		for marker in self.parent.markers:
			self.draw_marker(marker)

	def draw_marker(self, marker):
		raise NotImplementedError

	def adjust_time(self, offset, factor=1.):
		self.time_offset = offset
		self.time_factor = factor

	def correct_time(self, value):
		if self.parent.rezero:
			return (value + self.time_offset/86400. - self.parent.rezero_offset) * self.time_factor * self.parent.rezero_unit
		else:
			return self.time_factor*value + self.time_offset/86400.


class XAxisHandling(object):
	xlim_callback_ext = None
	xlim_min = 0.
	xlim_max = 1.
	xlim_auto = True
	xlog = False

	@staticmethod
	def ax_get_xlim(ax):
		return ax.get_xlim()
	
	@staticmethod
	def ax_set_xlim(ax, min, max):
		return ax.set_xlim(min, max)

	def get_axes_requirements(self):
		return [AxesRequirements(size=self.size, independent_x=True)]

	def xlim_callback(self, ax):
		self.xlim_min, self.xlim_max = self.ax_get_xlim(ax)
		if self.xlim_callback_ext:
			self.xlim_callback_ext(ax)

	def set_xlim_callback(self, func):
		self.xlim_callback_ext = func

	def set_xlim(self, min, max, auto):
		self.xlim_min = min
		self.xlim_max = max
		self.xlim_auto = auto
		try:
			self.xlim_rescale()
		except util.SharedXError:
			# this is needed for graphs that can enable/disable the shared x axis
			pass
		if self.axes:
			return self.ax_get_xlim(self.axes)
		else:
			return self.xlim_min, self.xlim_max

	def xlim_rescale(self):
		if not self.axes:
			return
		if self.xlim_auto:
			self.autoscale_x(self.axes)
		else:
			self.ax_set_xlim(self.axes, self.xlim_min, self.xlim_max)

	# any class that inherits from XAxisHandling is responsible to call set_xlog() at the end of draw()
	def set_xlog(self, xlog=None):
		if xlog is not None:
			self.xlog = xlog
		if self.axes:
			self.axes.set_xscale('log' if self.xlog else 'linear')
		if self.secondaryaxes:
			self.secondaryaxes.set_xscale('log' if self.xlog else 'linear')


class YAxisHandling(object):
	ylim_callback_ext = None
	ylim_min = 0.
	ylim_max = 1.
	ylim_auto = True
	ylog = False

	@staticmethod
	def ax_get_ylim(ax):
		return ax.get_ylim()
	
	@staticmethod
	def ax_set_ylim(ax, min, max):
		return ax.set_ylim(min, max)

	def ylim_callback(self, ax):
		self.ylim_min, self.ylim_max = self.ax_get_ylim(ax)
		if self.ylim_callback_ext:
			self.ylim_callback_ext(ax)

	def set_ylim_callback(self, func):
		self.ylim_callback_ext = func

	def set_ylim(self, min, max, auto):
		self.ylim_min = min
		self.ylim_max = max
		self.ylim_auto = auto
		self.ylim_rescale()
		if self.axes:
			return self.ax_get_ylim(self.axes)
		else:
			return self.ylim_min, self.ylim_max

	def ylim_rescale(self):
		if not self.axes:
			return
		if self.ylim_auto:
			self.autoscale_y(self.axes)
		else:
			self.ax_set_ylim(self.axes, self.ylim_min, self.ylim_max)

	def set_ylog(self, ylog):
		self.ylog = ylog
		if self.axes:
			self.axes.set_yscale('log' if ylog else 'linear')


class InverseYAxisHandling(YAxisHandling):
	@staticmethod
	def ax_get_ylim(ax):
		min, max = ax.get_ylim()
		return max, min
	
	@staticmethod
	def ax_set_ylim(ax, min, max):
		return ax.set_ylim(max, min)


class DoubleYAxisHandling(YAxisHandling):
	secondaryaxes = None

	ylim2_min = 0.
	ylim2_max = 1.
	ylim2_auto = True
	ylog2 = False

	def ylim_callback(self, ax):
		if ax is self.axes:
			self.ylim_min, self.ylim_max = self.ax_get_ylim(ax)
		elif ax is self.secondaryaxes:
			self.ylim2_min, self.ylim2_max = self.ax_get_ylim(ax)
		if self.ylim_callback_ext:
			self.ylim_callback_ext(ax)

	def set_ylim2(self, min, max, auto):
		self.ylim2_min = min
		self.ylim2_max = max
		self.ylim2_auto = auto
		self.ylim_rescale()
		if self.secondaryaxes:
			return self.ax_get_ylim(self.secondaryaxes)
		else:
			return self.ylim2_min, self.ylim2_max

	def ylim_rescale(self):
		super(DoubleYAxisHandling, self).ylim_rescale()
		if not self.secondaryaxes:
			return
		if self.ylim2_auto:
			self.autoscale_y(self.secondaryaxes)
		else:
			self.ax_set_ylim(self.secondaryaxes, self.ylim2_min, self.ylim2_max)

	def set_ylog2(self, ylog2):
		self.ylog2 = ylog2
		if self.secondaryaxes:
			self.secondaryaxes.set_yscale('log' if ylog2 else 'linear')

	def get_axes_requirements(self):
		return [AxesRequirements(size=self.size, twinx=True)]


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
	legend = 'upper right'
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
		self.axes.callbacks.connect('ylim_changed', self.ylim_callback)

	def get_xdata(self, chandata):
		return self.correct_time(chandata.time)

	def get_ydata(self, chandata):
		return chandata.value

	def draw(self):
		if self.data:
			self.formatter.reset()
			for d in self.data.iterchannels():
				self.axes.plot(self.get_xdata(d), self.get_ydata(d), self.formatter(d), label=d.id)
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
			self.get_legend_axes().legend_ = None

	def get_legend_items(self):
		return self.axes.get_legend_handles_labels()

	def get_legend_axes(self):
		return self.axes

	def draw_legend(self):
		if self.legend and self.axes:
			handles, labels = self.get_legend_items()
			if handles:
				l = self.get_legend_axes().legend(handles, labels, loc=self.legend, prop=self.legendprops)
				l.draggable(state=True)
			else:
				self.get_legend_axes().legend_ = None

	def draw_marker(self, marker):
		ax = self.axes
		if marker.interval():
			vspan = ax.axvspan(marker.left, marker.right, color='silver', zorder=-1e9)
			marker.add_callback(lambda: ax.patches.remove(vspan))
		else:
			line = ax.axvline(marker.left, color='silver', zorder=-1e9)
			marker.add_callback(lambda: ax.lines.remove(line))


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
		self.secondaryaxes.callbacks.connect('ylim_changed', self.ylim_callback)

	def draw(self):
		super(DoubleMultiTrend, self).draw()
		if self.secondarydata:
			for d in self.secondarydata.iterchannels():
				self.secondaryaxes.plot(self.get_xdata(d), self.get_ydata(d), self.formatter(d), label=d.id)
			self.draw_legend()
		if self.ylog2:
			self.secondaryaxes.set_yscale('log')

	def get_legend_items(self):
		# manually join the legends for both y-axes
		handles1, labels1 = self.axes.get_legend_handles_labels()
		handles2, labels2 = self.secondaryaxes.get_legend_handles_labels()
		return handles1 + handles2, labels1 + labels2

	def get_legend_axes(self):
		return self.secondaryaxes

	def set_axes(self, axes):
		self.axes, self.secondaryaxes = axes[0]

	def clear(self, quick=False):
		if not quick:
			if self.secondaryaxes:
				del self.secondaryaxes.lines[:]
				self.secondaryaxes.relim()
		super(DoubleMultiTrend, self).clear(quick)


class ImageBase(Subplot):
	colormap = 'spectral'
	interpolation = 'nearest'

	clim_min = 0.
	clim_max = 1.
	clim_auto = True
	clim_log = False
	clim_callback_ext = None

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

	def set_clim(self, min, max, auto, log):
		self.clim_min = min
		self.clim_max = max
		self.clim_auto = auto
		self.clim_log = log
		self.clim_rescale()

	def clim_rescale(self):
		if self.axes:
			for image in self.axes.images:
				# NOTE: it seems that a single instance of mpl.colors.Normalize isn't meant to be used for multiple images
				image.norm = self.get_clim_norm()

	def set_clim_callback(self, func):
		self.clim_callback_ext = func

	def clim_callback(self):
		if self.clim_auto and self.axes and self.axes.images:
			self.clim_min = +numpy.inf
			self.clim_max = -numpy.inf
			for image in self.axes.images:
				self.clim_min = min(image._A.min(), self.clim_min)
				self.clim_max = max(image._A.max(), self.clim_max)
			if self.clim_callback_ext:
				self.clim_callback_ext(self.clim_min, self.clim_max)

	def get_clim_norm(self):
		if self.clim_auto:
			min = max = None
		else:
			min = self.clim_min
			max = self.clim_max
		if self.clim_log:
			return LogNorm(min, max, clip=True)
		else:
			return matplotlib.colors.Normalize(min, max, clip=True)


class Time2D(YAxisHandling, ImageBase):
	def draw(self):
		if not self.data:
			return

		for image in self.data.iterimages():
			tstart = self.correct_time(image.tstart)
			tend = self.correct_time(image.tend)
			self.axes.imshow(self.get_imdata(image), 
				origin='lower', extent=(tstart, tend, image.ybottom, image.ytop), aspect='auto',
				cmap=self.colormap, interpolation=self.interpolation, norm=self.get_clim_norm()
			)

		self.clim_callback()
		self.ylim_rescale()

	def clear(self, quick=False):
		if not quick and self.axes:
			del self.axes.images[:], self.axes.lines[:], self.axes.patches[:]
			self.axes.relim()

	def draw_marker(self, marker):
		shinysilver = (.75, .75, .75, .5)
		ax = self.axes
		if marker.interval():
			vspan = ax.axvspan(marker.left, marker.right, color=shinysilver, zorder=1e9)
			marker.add_callback(lambda: ax.patches.remove(vspan))
		else:
			line = ax.axvline(marker.left, color=shinysilver, zorder=1e9)
			marker.add_callback(lambda: ax.lines.remove(line))


# based on the matplotlib anchored_artists example
class Scalebar(matplotlib.offsetbox.AnchoredOffsetbox):
	def __init__(self, transform, size, label, loc,
				 pad=0.2, borderpad=0.4, sep=5, prop=None, frameon=True, color='black'):
		"""
		Draw a horizontal bar with the size in data coordinate of the give axes.
		A label will be drawn underneath (center-aligned).

		pad, borderpad in fraction of the legend font size (or prop)
		sep in points.
		"""
		self.size_bar = matplotlib.offsetbox.AuxTransformBox(transform)
		self.size_bar.add_artist(matplotlib.patches.Rectangle((0,0), size, 0, fc="none", ec=color, lw=3))

		self.txt_label = matplotlib.offsetbox.TextArea(label, minimumdescent=False, textprops=dict(color=color))

		self._box = matplotlib.offsetbox.VPacker(children=[self.size_bar, self.txt_label],
							align="center",
							pad=0, sep=sep)

		super(Scalebar, self).__init__(loc, pad=pad, borderpad=borderpad,
									child=self._box,
									prop=prop,
									frameon=frameon)

		self.patch = matplotlib.patches.FancyBboxPatch(
			xy=(0.0, 0.0), width=1., height=1.,
			facecolor='w', edgecolor='none',
			mutation_scale=self.prop.get_size_in_points(),
			snap=True
		)
		self.patch.set_boxstyle("square",pad=pad)


class Image(ImageBase, XAxisHandling, InverseYAxisHandling):
	colormap = 'afmhot'
	interpolation = 'nearest'
	tzoom = 1
	mode = 'film strip'
	rotate = False
	marker = None
	scalebar = True
	frame = None

	def __init__(self, *args, **kwargs):
		self.vspans = []
		super(Image, self).__init__(*args, **kwargs)

	def get_axes_requirements(self):
		if self.mode == 'single frame':
			return [AxesRequirements(size=self.size, independent_x=True)]
		else:
			return [AxesRequirements(size=self.size)]

	def setup(self):
		super(Image, self).setup()
		self.axes.set_yticks([])
		if self.mode == 'single frame':
			self.axes.set_xticks([])
			self.axes.fmt_xdata = None
			self.axes.callbacks.connect('xlim_changed', self.xlim_callback)
		self.axes.callbacks.connect('ylim_changed', self.ylim_callback)
	
	def draw(self):
		if not self.data:
			return

		for d in self.data.iterframes():
			# map the linenunumber to the time axis and the individual points to some arbitrary unit axis
			# transpose the image data to plot scanlines vertical
			ysize, xsize = d.image.shape[:2] # support NxM 'greyscale' images, NxMx3 RGB, and NxMx4 RGBA
			tstart = self.correct_time(d.tstart)
			if d.tend is None:
				tend = None
			else:
				tend = self.correct_time(d.tend)

			if self.mode == 'single frame':
				self.frame = d

				if self.rotate:
					image = numpy.rot90(d.image, 3)
				else:
					image = d.image

				extent = d.get_extent()
				self.axes.imshow(image, origin='lower', aspect='equal', cmap=self.colormap, interpolation=self.interpolation, norm=self.get_clim_norm(), extent=extent)

				self.marker = self.parent.markers.add(tstart, tend)

				if self.scalebar:
					self.draw_scalebar(d)
			else:
				tendzoom = tstart + (tend - tstart) * self.tzoom
				self.axes.imshow(numpy.rot90(d.image), extent=(tstart, tendzoom, 0, 1), aspect='auto', cmap=self.colormap, interpolation=self.interpolation, norm=self.get_clim_norm())
				self.axes.add_patch(matplotlib.patches.Rectangle((tstart, 0), tendzoom-tstart, 1, linewidth=1, edgecolor='black', fill=False))
		
	def xlim_rescale(self):
		if self.mode == 'single frame':
			super(ImageBase, self).xlim_rescale()

	def clear(self, quick=False):
		if not quick:
			if self.axes:
				del self.axes.lines[:], self.axes.images[:], self.axes.patches[:], self.axes.artists[:]
				self.axes.relim()
			if self.marker:
				self.parent.markers.remove(self.marker)
		self.marker = None
		super(Image, self).clear(quick)

	def set_rotate(self, rotate):
		if rotate == self.rotate:
			return
		self.rotate = rotate

		if self.axes and self.mode == 'single frame':
			im = self.axes.images[0]
			# NOTE this uses a feature that is not officially in the matplotlib API
			if rotate:
				im.set_data(numpy.rot90(im._A, 3))
			else:
				im.set_data(numpy.rot90(im._A))

	def draw_marker(self, marker):
		pass

	@staticmethod
	def find_nice_number(near):
		# returns 1, 2, 5, 10, 20, 50, ...
		magn = int(numpy.floor(numpy.log10(near)))
		val = int(round(float(near) / 10**magn))
		if val == 1:
			return 1 * 10**magn
		elif val <= 3:
			return 2 * 10**magn
		elif val <= 7:
			return 5 * 10**magn
		else:
			return 10 * 10**magn

	def draw_scalebar(self, image):
		if image.pixelsize is None:
			return

		extent = image.get_extent()
		length = 0.1 * abs(extent[1] - extent[0])

		if image.pixelsize == 0:
			label = 0
		else:		
			label = length = self.find_nice_number(length)
		
		label = u'{0}{1}{2}'.format(label, ' ' if image.pixelunit else '', image.pixelunit or '')
		self.axes.add_artist(Scalebar(self.axes.transData, size=length, label=label, loc=4))
