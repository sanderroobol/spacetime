import itertools
import matplotlib, matplotlib.figure

class Plot(object):
	left = .75
	right = .75
	top = .2
	bottom = .75
	hspace = .2
	wspace = .2

	xlim_callback = None
	
	subplots = []
	master_axes = None

	def __init__(self, figure):
		self.figure = figure
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

			if r.twinx:
				twin = axes.twinx()
				self.twinx_axes.append(twin)
				self.setup_xaxis_labels(twin)
				axes = (axes, twin)
			
			ret.append((p, axes))

		for p, groups in itertools.groupby(ret, key=lambda x: x[0]):
			p.set_axes(list(axes for (subplot, axes) in groups))

		for p in self.subplots:
			p.setup()

		if self.shared_axes:
			self.master_axes = self.shared_axes[-1]
			if self.xlim_callback:
				self.master_axes.callbacks.connect('xlim_changed', self.xlim_callback)
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
		axes.xaxis_date()
	
		if hasattr(axes, 'is_last_row') and axes.is_last_row():
			for label in axes.get_xticklabels():
				label.set_ha('right')
				label.set_rotation(30)

			self.setup_margins()
		else:
			for label in axes.get_xticklabels():
				label.set_visible(False)

	def set_xlim_callback(self, func):
		self.xlim_callback = func

	def autoscale(self, master=None):
		# NOTE: this is a workaround for matplotlib's internal autoscaling routines. 
		# it imitates axes.autoscale_view(), but only takes the dataLim into account when
		# there are actually some lines or images in the graph

		# NOTE: master axes detection only works when all axes from a Subplot are either all shared
		# or all independent
		if master and master in self.independent_axes:
			master.autoscale_view()
			return
			
		if not self.shared_axes:
			return
		# NOTE: this assumes twinx axes always belong to a shared axes
		for ax in self.shared_axes + self.twinx_axes:
			ax.autoscale_view(scalex=False)

		dl = [ax.dataLim for ax in self.shared_axes + self.twinx_axes if ax.lines or ax.images or ax.patches]
		if dl:
			bb = matplotlib.transforms.BboxBase.union(dl)
			x0, x1 = bb.intervalx
			XL = self.master_axes.xaxis.get_major_locator().view_limits(x0, x1)
			self.master_axes.set_xbound(XL)