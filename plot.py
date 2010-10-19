import itertools
import matplotlib, matplotlib.figure

class Plot(object):
	def __init__(self):
		self.subplots = []

	@classmethod
	def fromfigure(klass, figure):
		plot = klass()
		plot.figure = figure
		plot.figsetup()
		return plot

	@classmethod
	def newpyplotfigure(klass, size=(14,8)):
		import matplotlib.pyplot
		return klass.fromfigure(matplotlib.pyplot.figure(figsize=size))

	@classmethod
	def newmatplotlibfigure(klass):
		return klass.fromfigure(matplotlib.figure.Figure())

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

			self.general_axes_setup(axes, i+1 != total)

			if r.twinx:
				axes = (axes, axes.twinx())
				self.general_axes_setup(axes[1], i+1 != total)
			
			ret.append((p, axes))

		for p, groups in itertools.groupby(ret, key=lambda x: x[0]):
			p.set_axes(list(axes for (subplot, axes) in groups))

		for p in self.subplots:
			p.setup()

	@staticmethod
	def general_axes_setup(axes, hide_xticklabels=False):
		axes.xaxis_date()
		axes.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M:%S'))
		if hide_xticklabels:
			for label in axes.get_xticklabels():
				label.set_visible(False)
		
	def draw(self):
		for p in self.subplots:
			p.draw()

	def figsetup(self, size=(14,8), legend=0):
		width, height = self.figure.get_size_inches()

		def wabs2rel(x): return x / width
		def habs2rel(x): return x / height

		lrborder = .75
		tbborder = .45
		hspace = .2
		wspace = .2
		
		self.figure.subplots_adjust(
				left=wabs2rel(lrborder),
				right=1-wabs2rel(lrborder + legend),
				top=1-habs2rel(tbborder),
				bottom=habs2rel(tbborder),
				hspace=habs2rel(hspace),
				wspace=wabs2rel(wspace),
		)
