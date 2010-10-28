# keep this import at top to ensure proper matplotlib backend selection
from mplfigure import MPLFigureEditor

from . import plot, util, panels, version

from enthought.traits.api import *
from enthought.traits.ui.api import *
import matplotlib.figure, matplotlib.transforms
import wx
import datetime


class DateTimeSelector(HasTraits):
	date = Date(datetime.date.today())
	time = Time(datetime.time())
	datetime = Property(depends_on='date, time')
	mpldt = Property(depends_on='datetime')

	def _get_datetime(self):
		return datetime.datetime.combine(self.date, self.time)

	def _set_datetime(self, dt):
		self.date = dt.date()
		self.time = dt.time()

	def _get_mpldt(self):
		return util.mpldtfromdatetime(self.datetime)

	def _set_mpldt(self, f):
		self.datetime = util.datetimefrommpldt(f)

	traits_view = View(
		HGroup(
			Item('time', editor=TimeEditor(strftime='%H:%M:%D')),
			Item('date'),
			show_labels=False,
	))


class MainTab(panels.Tab):
	xmin = Instance(DateTimeSelector, args=())
	xmax = Instance(DateTimeSelector, args=())
	tablabel = 'Main'
	status = Str('')

	taboptions = (
		panels.CameraFramePanel,
		panels.CameraTrendPanel,
		panels.QMSPanel,
		panels.GasCabinetPanel,
		panels.TPDirkPanel,
	)
	tabdict = dict((klass.tablabel, klass) for klass in taboptions)
	tablabels = [klass.tablabel for klass in taboptions]

	add = Button()
	subgraph_type = Enum(*tablabels)

	mainwindow = Any

	def _add_fired(self):
		self.mainwindow.add_tab(self.tabdict[self.subgraph_type](update_canvas=self.mainwindow.update_canvas, autoscale=self.mainwindow.plot.autoscale, redraw_figure=self.mainwindow.redraw_figure))
	
	def xlim_callback(self, ax):
		self.xmin.mpldt, self.xmax.mpldt = ax.get_xlim()

	@on_trait_change('xmin.mpldt')
	def _xmin_mpldt_changed(self):
		if self.mainwindow.plot.master_axes.get_xlim()[0] != self.xmin.mpldt:
			self.mainwindow.plot.master_axes.set_xlim(xmin=self.xmin.mpldt)
			self.mainwindow.update_canvas()

	@on_trait_change('xmax.mpldt')
	def _xmax_mpldt_changed(self):
		if self.mainwindow.plot.master_axes.get_xlim()[1] != self.xmax.mpldt:
			self.mainwindow.plot.master_axes.set_xlim(xmax=self.xmax.mpldt)
			self.mainwindow.update_canvas()

	traits_view = View(Group(
		Group(
			Item('xmin', style='custom'),
			Item('xmax', style='custom'),
			label='Graph settings',
			show_border=True,
		),
		Group(
			Item('subgraph_type', show_label=False, style='custom', editor=EnumEditor(values=tablabels, format_func=lambda x: x, cols=1)),
			Item('add', show_label=False),
			label='Add subgraph',
			show_border=True,
		),
		Group(
			Item('status', show_label=False, style='readonly'),
			label='Cursor',
			show_border=True,
		),
		layout='normal',
	))


class PythonTab(panels.Tab):
	shell = PythonValue({})
	traits_view = View(
		Item('shell', show_label=False, editor=ShellEditor(share=False))
	)

	tablabel = 'Python'


class App(HasTraits):
	plot = Instance(plot.Plot)
	figure = Instance(matplotlib.figure.Figure)
	maintab = Instance(MainTab)
	status = DelegatesTo('maintab')

	tabs = List(Instance(panels.Tab))

	def on_figure_resize(self, event):
		self.plot.setup_margins()
		self.update_canvas()

	def update_canvas(self):
		wx.CallAfter(self.figure.canvas.draw)

	def add_tab(self, tab):
		self.tabs.append(tab)

	def _maintab_default(self):
		return MainTab(mainwindow=self)

	def _tabs_changed(self):
		self.redraw_figure()

	def _tabs_items_changed(self, event):
		#for removed in event.removed: FIXME doesn't work...
		#	if isinstance(removed, MainTab):
		#		self.tabs = [removed] + self.tabs
		#	elif isinstance(removed, PythonShell):
		#		self.tabs = [self.tabs[0], removed] + self.tabs[1:]
		self.redraw_figure()

	def _tabs_default(self):
		return [self.maintab, PythonTab()]

	def redraw_figure(self):
		self.plot.clear()
		[self.plot.add_subplot(tab.plot) for tab in self.tabs if isinstance(tab, panels.SubplotPanel) and tab.visible]
		self.plot.setup()
		self.plot.draw()
		self.plot.autoscale()
		self.update_canvas()

	def _plot_default(self):
		p = plot.Plot.newmatplotlibfigure()
		p.setup()

		# At this moment, the figure has not yet been initialized properly, so delay these calls.
		# This has to be a lambda statement to make a closure on the variables 'p' and 'self'
		wx.CallAfter(lambda: (
						p.figure.canvas.mpl_connect('resize_event', self.on_figure_resize), 
						p.set_xlim_callback(self.maintab.xlim_callback)
		))
		return p

	def _figure_default(self):
		return self.plot.figure

	traits_view = View(
			HSplit(
				Item('figure', editor=MPLFigureEditor(status='status'), dock='vertical'),
				Item('tabs', style='custom', width=200, editor=ListEditor(use_notebook=True, deletable=True, page_name='.tablabel')),
				show_labels=False,
			),
			resizable=True,
			height=700, width=1100,
			buttons=NoButtons,
			title='Spacetime %s' % version.version
		)

	def run(self):
		self.configure_traits()


if __name__ == '__main__':
	app = App()
	app.run()
