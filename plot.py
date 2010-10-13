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
		plot.build()
		plot.draw()
		matplotlib.pylab.show()
		return plot

	def add_subplot(self, subplot):
		self.subplots.append(subplot)

	def build(self):
		top = None
		for i, p in enumerate(self.subplots):
			if top:
				axes = self.figure.add_subplot(len(self.subplots), 1, i+1, sharex=top)
			else:
				top = axes = self.figure.add_subplot(len(self.subplots), 1, i+1)
			try:
				if p.secondarydata: # FIXME: this is not really nice
					p.secondaryaxes = axes.twinx()
					p.secondaryaxes.xaxis_date()
			except AttributeError:
				pass
			if i + 1 != len(self.subplots):
				self.hide_xticklabels(axes)
			p.build(axes)
			axes.xaxis_date()
		self.reformat_xaxis()

	def draw(self):
		pass

	def reformat_xaxis(self):
		if self.figure.axes:
			self.figure.axes[-1].xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M:%S'))

	@staticmethod
	def hide_xticklabels(ax):
		for label in ax.get_xticklabels():
			label.set_visible(False)

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
