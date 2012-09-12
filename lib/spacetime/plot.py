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
import numpy
import matplotlib, matplotlib.figure, matplotlib.dates, matplotlib.gridspec

from . import util


class AbsoluteGridSpec(matplotlib.gridspec.GridSpecBase):
	def __init__(self, nrows, ncols,
	             margins=(.75, .75, .75, .75),
	             spacing=(.75, .75),
	             ratios=(None, None)):
		"""gridspec in absolute units

		all sizes in inches
		* margins: top, right, bottom, left
		* spacing: horizontal, vertical 
		* ratios:  like GridSpec's ratios
		"""

		self._margins = margins
		self._spacing = spacing

		matplotlib.gridspec.GridSpecBase.__init__(self, nrows, ncols,
		                      width_ratios=ratios[0],
		                      height_ratios=ratios[1])

	@staticmethod
	def _divide_into_cells(size, n, margin_low, margin_high, spacing, ratios):
		total = size - margin_low - margin_high - (n-1)*spacing
		cell = total / n

		if ratios is None:
			cells = [cell] * n
		else:
			tr = sum(ratios)
			cells = [total*r/tr for r in ratios]

		seps = [0] + ([spacing] * (n-1))
		cells = numpy.add.accumulate(numpy.ravel(zip(seps, cells)))

		lowers = [(margin_low + cells[2*i])/size for i in range(n)]
		uppers = [(margin_low + cells[2*i+1])/size for i in range(n)]
		return lowers, uppers

	def get_grid_positions(self, fig):
		width, height = fig.get_size_inches()
		mtop, mright, mbottom, mleft = self._margins
		hspace, vspace = self._spacing
		if self._row_height_ratios:
			# plot numbering should start at top, but y-coordinates start at bottom
			height_ratios = self._row_height_ratios[::-1]
		else:
			height_ratios = None
		figBottoms, figTops = self._divide_into_cells(height, self._nrows, mbottom, mtop, vspace, height_ratios)
		figLefts, figRights = self._divide_into_cells(width,  self._ncols, mleft, mright, hspace, self._col_width_ratios)
		return figBottoms[::-1], figTops[::-1], figLefts, figRights

class Marker(object):
	def __init__(self, left, right=None):
		self.callbacks = []
		self._set_params(left, right)

	def add_callback(self, callback):
		self.callbacks.append(callback)

	def clear(self):
		for callback in self.callbacks:
			callback()

	def draw(self):
		for s in self.plot.subplots:
			s.draw_marker(self)

	def _set_params(self, left, right=None):
		self.clear()
		self.left = left
		self.right = right

	def move(self, left, right=None):
		self._set_params(left, right)
		self.draw()

	def interval(self):
		return self.right is not None


class Markers(object):
	def __init__(self, parent):
		self.parent = parent
		self.clear()

	def add(self, *args, **kwargs):
		marker = Marker(*args, **kwargs)
		marker.plot = self.parent
		self.markers.append(marker)
		marker.draw()
		return marker

	def redraw(self):
		for marker in self.markers:
			marker.clear()
			marker.draw()

	def clear(self):
		self.markers = []

	def remove(self, marker):
		self.markers.remove(marker)
		marker.clear()

	def __iter__(self):
		return iter(self.markers)
	

class Plot(object):
	shared_xlim_callback_ext = None
	shared_xmin = 0.
	shared_xmax = 1.
	shared_xauto = True
	
	subplots = []
	master_axes = None

	rezero = False
	rezero_unit = 1.
	rezero_offset = 0.

	def __init__(self, figure):
		self.figure = figure
		self.markers = Markers(self)
		self.clear()

	@classmethod
	def newpyplotfigure(klass, size=(14,8)):
		import matplotlib.pyplot
		return klass(matplotlib.pyplot.figure(figsize=size))

	@classmethod
	def newmatplotlibfigure(klass):
		return klass(matplotlib.figure.Figure())

	@classmethod
	def autopyplot(klass, *subplots, **kwargs):
		import matplotlib.pyplot
		plot = klass.newpyplotfigure(**kwargs)
		for p in subplots:
			plot.add_subplot(p)
		plot.setup()
		plot.draw()
		matplotlib.pyplot.show()
		return plot

	def relocate(self, figure):
		self.clear()
		self.figure = figure

	def clear(self):
		for p in self.subplots:
			p.clear(quick=True)
		self.figure.clear()
		self.markers.clear()
		self.subplots = []
		self.independent_axes = []
		self.shared_axes = []
		self.twinx_axes = []

	def add_subplot(self, subplot):
		subplot.parent = self
		self.subplots.append(subplot)

	def setup(self):
		req = []
		for p in self.subplots:
			req.extend((p, r) for r in p.get_axes_requirements())
		total = len(req)

		ret = []
		shared = None
		gridspec = AbsoluteGridSpec(
				total, 1,
				margins=(.2, .75, .75, .75),
				spacing=(.2, .2),
				ratios=(None, tuple(r.size for (p, r) in req))
		)
		for i, (p, r) in enumerate(req):
			if r.independent_x:
				axes = self.figure.add_subplot(gridspec[i, 0])
				self.independent_axes.append(axes)
			else:
				if shared:
					axes = self.figure.add_subplot(gridspec[i, 0], sharex=shared)
				else:
					shared = axes = self.figure.add_subplot(gridspec[i, 0])
				self.shared_axes.append(axes)
				self.setup_xaxis_labels(axes)
			axes.autoscale(False)

			if r.twinx:
				twin = axes.twinx()
				self.twinx_axes.append(twin)
				if not r.independent_x:
					self.setup_xaxis_labels(twin)
				axes = (axes, twin)
				twin.autoscale(False)
			
			ret.append((p, axes))

		for p, groups in itertools.groupby(ret, key=lambda x: x[0]):
			p.set_axes(list(axes for (subplot, axes) in groups))

		for p in self.subplots:
			p.setup()

		if self.shared_axes:
			self.master_axes = self.shared_axes[-1]
			for axes in self.shared_axes:
				axes.callbacks.connect('xlim_changed', self.shared_xlim_callback)
		else:
			self.master_axes = None

	def draw(self):
		for p in self.subplots:
			p.draw()

	def setup_xaxis_labels(self, axes):
		if not self.rezero:
			axes.xaxis_date(tz=util.localtz)
			
			# Timezone support is not working properly with xaxis_date(), so override manually
			locator = matplotlib.dates.AutoDateLocator(tz=util.localtz)
			axes.xaxis.set_major_locator(locator)
			axes.xaxis.set_major_formatter(matplotlib.dates.AutoDateFormatter(locator, tz=util.localtz))

		if hasattr(axes, 'is_last_row') and axes.is_last_row():
			if not self.rezero:
				for label in axes.get_xticklabels():
					label.set_ha('right')
					label.set_rotation(30)
		else:
			for label in axes.get_xticklabels():
				label.set_visible(False)

	def shared_xlim_callback(self, ax):
		self.shared_xmin, self.shared_xmax = self.get_ax_limits(ax)
		if self.shared_xlim_callback_ext:
			self.shared_xlim_callback_ext(ax)

	def set_shared_xlim_callback(self, func):
		self.shared_xlim_callback_ext = func

	def autoscale(self, subplot=None):
		if subplot:
			subplots = [subplot]
		else:
			subplots = self.subplots
		
		# this silently assumes that a single subplot will not have multiple
		# graphs with mixed shared/non-shared x-axis
		shared_xlim_rescale = False
		for subplot in subplots:
			subplot.ylim_rescale()
			try:
				subplot.xlim_rescale()
			except (AttributeError, util.SharedXError):
				shared_xlim_rescale = True

		if shared_xlim_rescale:
			self.shared_xlim_rescale()

	def set_shared_xlim(self, min, max, auto):
		self.shared_xmin = min
		self.shared_xmax = max
		self.shared_xauto = auto
		self.shared_xlim_rescale()
		if self.master_axes:
			return self.get_ax_limits(self.master_axes)
		else:
			return self.shared_xmin, self.shared_xmax

	def shared_xlim_rescale(self):
		if not self.master_axes:
			return
		if self.shared_xauto:
			self.autoscale_shared_x()
		else:
			self.master_axes.set_xlim(self.correct_time(self.shared_xmin), self.correct_time(self.shared_xmax))
			
	def autoscale_shared_x(self):
		# NOTE: this is a workaround for matplotlib's internal autoscaling routines. 
		# it imitates axes.autoscale_view(), but only takes the dataLim into account when
		# there are actually some lines or images in the graph
		# see also Subplots.autoscale_x
		dl = [ax.dataLim for ax in self.shared_axes + self.twinx_axes if ax.lines or ax.images or ax.patches]
		if dl:
			bb = matplotlib.transforms.BboxBase.union(dl)
			x0, x1 = bb.intervalx
			XL = self.master_axes.xaxis.get_major_locator().view_limits(x0, x1)
			self.master_axes.set_xlim(XL)

	def set_rezero_opts(self, enable, unit, offset):
		self.rezero = enable
		self.rezero_unit = unit
		self.rezero_offset = offset

	def correct_time(self, value):
		return (value - self.rezero_offset) * self.rezero_unit 

	def correct_time_inverse(self, value):
		return value / self.rezero_unit + self.rezero_offset

	def get_ax_limits(self, ax):
		low, up = ax.get_xlim()
		return self.correct_time_inverse(low), self.correct_time_inverse(up)
