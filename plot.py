import itertools
import matplotlib, matplotlib.figure

class Plot(object):
	dateformat = '%H:%M:%S'

	left = .75
	right = .75
	top = .2
	bottom = None # see setup_xaxis_labels()
	hspace = .2
	wspace = .2

	def __init__(self, figure):
		self.figure = figure
		self.subplots = []

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
		self.figure.clear()
		self.subplots = []

	def add_subplot(self, subplot):
		self.subplots.append(subplot)

	def setup(self):

		req = []
		for p in self.subplots:
			req.extend((p, r) for r in p.get_axes_requirements())
		total = len(req)

		ret = []
		for i, (p, r) in enumerate(req):
			if i > 0 and not r.no_sharex:
				axes = self.figure.add_subplot(total, 1, i+1, sharex=top)
			else:
				axes = self.figure.add_subplot(total, 1, i+1)

			if i == 0: # first
				top = axes

			self.setup_xaxis_labels(axes)

			if r.twinx:
				axes = (axes, axes.twinx())
				self.setup_xaxis_labels(axes[1])
			
			ret.append((p, axes))

		for p, groups in itertools.groupby(ret, key=lambda x: x[0]):
			p.set_axes(list(axes for (subplot, axes) in groups))

		for p in self.subplots:
			p.setup()

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

	def setup_xaxis_labels(self, axes=None):
		if axes is None:
			if not self.subplots:
				return
			axes = self.subplots[-1].axes

		axes.xaxis_date()
	
		if hasattr(axes, 'is_last_row') and axes.is_last_row():
			for label in axes.get_xticklabels():
				label.set_ha('right')
				label.set_rotation(30)

			if len(self.dateformat) > 10:
				self.bottom = 1.
			else:
				self.bottom = .75
			axes.xaxis.set_major_formatter(matplotlib.dates.DateFormatter(self.dateformat))

			self.setup_margins()
		else:
			for label in axes.get_xticklabels():
				label.set_visible(False)


