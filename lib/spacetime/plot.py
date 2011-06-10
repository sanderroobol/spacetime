import itertools
import matplotlib, matplotlib.figure, matplotlib.dates

from . import util

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
	left = .75
	right = .75
	top = .2
	bottom = .75
	hspace = .2
	wspace = .2

	shared_xlim_callback = None
	shared_xmin = 0.
	shared_xmax = 1.
	shared_xauto = True
	
	subplots = []
	master_axes = None

	def __init__(self, figure):
		self.figure = figure
		self.markers = Markers(self)
		self.clear()

	@classmethod
	def newpyplotfigure(klass, size=(14,8)):
		import matplotlib.pyplot
		plot = klass(matplotlib.pyplot.figure(figsize=size))
		plot.figure.canvas.mpl_connect('resize_event', plot.setup_margins)
		return plot

	@classmethod
	def newmatplotlibfigure(klass):
		return klass(matplotlib.figure.Figure())

	@classmethod
	def autopylab(klass, *subplots, **kwargs):
		import matplotlib.pylab
		plot = klass.newpyplotfigure(**kwargs)
		for p in subplots:
			plot.add_subplot(p)
		plot.setup()
		plot.draw()
		matplotlib.pylab.show()
		return plot

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
		for i, (p, r) in enumerate(req):
			if r.independent_x:
				axes = self.figure.add_subplot(total, 1, i+1)
				self.independent_axes.append(axes)
			else:
				if shared:
					axes = self.figure.add_subplot(total, 1, i+1, sharex=shared)
				else:
					shared = axes = self.figure.add_subplot(total, 1, i+1)
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
			if self.shared_xlim_callback:
				for axes in self.shared_axes:
					axes.callbacks.connect('xlim_changed', self.shared_xlim_callback)
		else:
			self.master_axes = None

	def draw(self):
		for p in self.subplots:
			p.draw()

	def setup_margins(self, event=None):
		width, height = self.figure.get_size_inches()

		def wabs2rel(x): return x / width
		def habs2rel(x): return x / height
	
		self.figure.subplots_adjust(
				left   = wabs2rel(self.left),
				right  = 1-wabs2rel(self.right),
				top    = 1-habs2rel(self.top),
				bottom = habs2rel(self.bottom),
				hspace = habs2rel(self.hspace) * len(self.subplots),
				wspace = wabs2rel(self.wspace),
		)

	def setup_xaxis_labels(self, axes):
		axes.xaxis_date(tz=util.localtz)
		
		# Timezone support is not working properly with xaxis_date(), so override manually
		locator = matplotlib.dates.AutoDateLocator(tz=util.localtz)
		axes.xaxis.set_major_locator(locator)
		axes.xaxis.set_major_formatter(matplotlib.dates.AutoDateFormatter(locator, tz=util.localtz))

		if hasattr(axes, 'is_last_row') and axes.is_last_row():
			for label in axes.get_xticklabels():
				label.set_ha('right')
				label.set_rotation(30)

			self.setup_margins()
		else:
			for label in axes.get_xticklabels():
				label.set_visible(False)

	def set_xlim_callback(self, func):
		self.shared_xlim_callback = func

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
			return self.master_axes.get_xlim()
		else:
			return self.shared_xmin, self.shared_xmax

	def shared_xlim_rescale(self):
		if not self.master_axes:
			return
		if self.shared_xauto:
			self.autoscale_shared_x()
		else:
			self.master_axes.set_xlim(self.shared_xmin, self.shared_xmax)#, emit=False) # FIXME this breaks twinx()ed graphs!
			
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
			self.master_axes.set_xlim(XL)#, emit=False) FIXME this breaks twinx()ed graphs!
