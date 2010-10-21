# keep this import at top to ensure proper matplotlib backend selection
from mplfigure import MPLFigureEditor

import subplots
import datasources
import filters
import plot

from enthought.traits.api import *
from enthought.traits.ui.api import *
import matplotlib.figure, matplotlib.transforms, matplotlib.cm
import string
import wx


class Tab(HasTraits):
	pass


class SubplotPanel(Tab):
	filename = File
	plot = Instance(subplots.Subplot)
	update_canvas = Callable
	autoscale = Callable
	number = 0

	def __init__(self, *args, **kwargs):
		super(SubplotPanel, self).__init__(*args, **kwargs)
		self.__class__.number += 1
		if self.__class__.number != 1:
			self.tablabel = '%s %d' % (self.tablabel, self.__class__.number)

	def redraw(self):
		self.plot.clear()
		self.plot.draw()
		self.autoscale()
		self.update_canvas()


class CameraPanel(SubplotPanel):
	data = Instance(datasources.Camera)

	firstframe = Int(0)
	lastframe = Int(0)
	stepframe = Range(1, 1000000000)
	framecount = Int(0)
	direction = Enum(1, 2)

	def _direction_changed(self):
		self.data.direction = self.direction
		self.redraw()


class CameraFramePanel(CameraPanel):
	channel = Int(0)
	channelcount = Int(0)
	bgsubtract = Bool(True)
	clip = Float(4.)
	colormap = Enum(sorted((m for m in matplotlib.cm.datad if not m.endswith("_r")), key=string.lower))
	interpolation = Enum('nearest', 'bilinear', 'bicubic')
	zoom = Button

	tablabel = 'Camera'
	
	def __init__(self, *args, **kwargs):
		super(CameraFramePanel, self).__init__(*args, **kwargs)
		self.colormap = 'gist_heat'

	def _plot_default(self):
		p = subplots.Image()
		p.set_colormap(self.colormap)
		return p

	def _colormap_changed(self):
		self.plot.set_colormap(self.colormap)
		self.update_canvas()

	def _interpolation_changed(self):
		self.plot.set_interpolation(self.interpolation)
		self.update_canvas()

	def _filename_changed(self):
		self.data = datasources.Camera(self.filename)
		self.channelcount = self.data.getchannelcount() - 1
		self.framecount = self.data.getframecount() - 1
		self.lastframe = min(self.framecount, 25)
		self.settings_changed()

	def _zoom_fired(self):
		self.plot.axes.set_xlim(*self.plot.axes.dataLim.intervalx)
		self.update_canvas()

	@on_trait_change('channel, bgsubtract, clip, firstframe, lastframe, stepframe')
	def settings_changed(self):
		if not self.data:
			return
		# FIXME: implement a smarter first/last frame selection, don't redraw everything
		data = self.data.selectchannel(self.channel).selectframes(self.firstframe, self.lastframe, self.stepframe)
		if self.bgsubtract:
			data = data.apply_filter(filters.BGSubtractLineByLine)
		if self.clip > 0:
			data = data.apply_filter(filters.ClipStdDev(self.clip))
		self.plot.tzoom = self.stepframe
		self.plot.set_data(data)
		self.redraw()

	traits_view = View(Group(
		Group(
			Item('filename', editor=FileEditor(filter=['Camera RAW files (*.raw)', '*.raw', 'All files', '*'], entries=0)),
			Item('channel', editor=RangeEditor(low=0, high_name='channelcount')),
			Item('firstframe', label='First frame', editor=RangeEditor(low=0, high_name='framecount')),
			Item('lastframe', label='Last frame', editor=RangeEditor(low=0, high_name='framecount')),
			Item('stepframe', label='Key frame mode'),
			Item('direction', editor=EnumEditor(values={1:'1:L2R', 2:'2:R2L'})),
			show_border=True,
			label='General',
		),
		Group(
			Item('colormap'),
			Item('interpolation', editor=EnumEditor(values={'nearest':'1:none', 'bilinear':'2:bilinear', 'bicubic':'3:bicubic'})),
			Item('zoom', show_label=False, label='Zoom to fit'),
			show_border=True,
			label='Display',
		),
		Group(
			Item('bgsubtract', label='Backgr. subtr.', tooltip='Line-by-line linear background subtraction'),
			Item('clip', label='Color clipping', tooltip='Clip colorscale at <number> standard deviations away from the average (0 to disable)'),
			show_border=True,
			label='Filters',
		),
		layout='normal',
	))


class TimeTrendPanel(SubplotPanel):
	legend = Bool(True)
	ymin = Float(0.)
	ymax = Float(1.)
	channels = List(Str)
	selected_primary_channels = List(Str)
	data = Instance(datasources.DataSource)

	def _plot_default(self):
		plot = self.plotfactory()
		plot.set_ylim_callback(self.ylim_callback)
		return plot

	def ylim_callback(self, ax):
		self.ymin, self.ymax = ax.get_ylim()

	def _filename_changed(self):
		self.data = self.datafactory(self.filename)
		self.channels = list(self.data.iterchannelnames())
		self.redraw()

	@on_trait_change('selected_primary_channels')
	def settings_changed(self):
		self.plot.set_data(self.data.selectchannels(lambda chan: chan.id in self.selected_primary_channels))
		self.redraw()

	def _ymin_changed(self):
		if self.plot.axes.get_ylim()[0] != self.ymin:
			self.plot.axes.set_ylim(ymin=self.ymin)
			self.update_canvas()

	def _ymax_changed(self):
		if self.plot.axes.get_ylim()[1] != self.ymax:
			self.plot.axes.set_ylim(ymax=self.ymax)
			self.update_canvas()

	def _legend_changed(self):
		self.plot.set_legend(self.legend)
		self.update_canvas()

	left_yaxis_group = Group(
		Item('channels', editor=ListStrEditor(editable=False, multi_select=True, selected='selected_primary_channels')),
		Item('ymin'),
		Item('ymax'),
		show_border=True,
		label='Left y-axis'
	)

	def traits_view(self):
		return View(Group(
			Group(
				Item('filename', editor=FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
				Item('legend'),
				show_border=True,
				label='General',
			),
			Include('left_yaxis_group'),
			layout='normal',
		))


class DoubleTimeTrendPanel(TimeTrendPanel):
	selected_secondary_channels = List(Str)
	ymin2 = Float(0.)
	ymax2 = Float(1.)

	def _plot_default(self):
		plot = self.plotfactory()
		plot.set_ylim_callback(self.ylim_callback)
		return plot

	def ylim_callback(self, ax):
		if ax is self.plot.axes:
			self.ymin, self.ymax = ax.get_ylim()
		elif ax is self.plot.secondaryaxes:
			self.ymin2, self.ymax2 = ax.get_ylim()

	def _ymin2_changed(self):
		if self.plot.secondaryaxes.get_ylim()[0] != self.ymin2:
			self.plot.secondaryaxes.set_ylim(ymin=self.ymin2)
			self.update_canvas()

	def _ymax2_changed(self):
		if self.plot.secondaryaxes.get_ylim()[1] != self.ymax2:
			self.plot.secondaryaxes.set_ylim(ymax=self.ymax2)
			self.update_canvas()

	@on_trait_change('selected_primary_channels, selected_secondary_channels')
	def settings_changed(self):
		self.plot.set_data(
			self.data.selectchannels(lambda chan: chan.id in self.selected_primary_channels),
			self.data.selectchannels(lambda chan: chan.id in self.selected_secondary_channels),
		)
		self.redraw()

	right_yaxis_group = Group(
		Item('channels', editor=ListStrEditor(editable=False, multi_select=True, selected='selected_secondary_channels')),
		Item('ymin2', label='Ymin'),
		Item('ymax2', label='Ymax'),
		show_border=True,
		label='Right y-axis'
	)

	def traits_view(self):
		return View(Group(
			Group(
				Item('filename', editor=FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
				Item('legend'),
				show_border=True,
				label='General',
			),
			Include('left_yaxis_group'),
			Include('right_yaxis_group'),
			layout='normal',
		))


class CameraTrendPanel(DoubleTimeTrendPanel, CameraPanel):
	tablabel = 'Camera Trend'
	plotfactory = subplots.DoubleMultiTrend
	filter = 'Camera RAW files (*.raw)', '*.raw'

	framecount = Int(0)
	average = Int(100)

	def _filename_changed(self):
		self.data = datasources.Camera(self.filename)
		self.channels = list(self.data.iterchannelnames())
		self.framecount = self.data.getframecount() - 1
		self.lastframe = min(self.framecount, 25)
		self.settings_changed()

	@on_trait_change('average, firstframe, lastframe, stepframe, selected_primary_channels, selected_secondary_channels')
	def settings_changed(self):
		if not self.data:
			return
		# FIXME: implement a smarter first/last frame selection, don't redraw everything
		data = self.data.selectframes(self.firstframe, self.lastframe, self.stepframe)
		if self.average > 0:
			data = data.apply_filter(filters.average(self.average))
		self.plot.set_data(
			data.selectchannels(lambda chan: chan.id in self.selected_primary_channels),
			data.selectchannels(lambda chan: chan.id in self.selected_secondary_channels),
		)
		self.redraw()

	traits_view = View(Group(
		Group(
			Item('filename', editor=FileEditor(filter=['Camera RAW files (*.raw)', '*.raw', 'All files', '*'], entries=0)),
			Item('firstframe', label='First frame', editor=RangeEditor(low=0, high_name='framecount')),
			Item('lastframe', label='Last frame', editor=RangeEditor(low=0, high_name='framecount')),
			Item('stepframe', label='Key frame mode'),
			Item('direction', editor=EnumEditor(values={1:'1:L2R', 2:'2:R2L'})), # FIXME: for trends, it should be possible to show both!
			Item('average', tooltip='N-point averaging'),
			Item('legend'),
			show_border=True,
			label='General',
		),
		Include('left_yaxis_group'),
		Include('right_yaxis_group'),
		layout='normal',
	))


class QMSPanel(TimeTrendPanel):
	tablabel = 'QMS'
	datafactory = datasources.QMS
	plotfactory = subplots.QMS
	filter = 'Quadera ASCII files (*.asc)', '*.asc'


class TPDirkPanel(DoubleTimeTrendPanel):
	tablabel = 'TPDirk'
	plotfactory = subplots.TPDirk
	datafactory = datasources.TPDirk
	filter = 'Dirk\'s ASCII files (*.txt)', '*.txt'

	def _filename_changed(self):
		self.data = self.datafactory(self.filename)
		self.plot.set_data(self.data)
		self.redraw()

	def traits_view(self):
		return View(Group(
			Group(
				Item('filename', editor=FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
				Item('legend'),
				show_border=True,
				label='General',
			),
			Group(
				Item('ymin'),
				Item('ymax'),
				show_border=True,
				label='Left y-axis'
			),
			Group(
				Item('ymin2', label='Ymin'),
				Item('ymax2', label='Ymax'),
				show_border=True,
				label='Right y-axis'
			),
			layout='normal',
		))


class GasCabinetPanel(DoubleTimeTrendPanel):
	tablabel = 'Gas cabinet'
	plotfactory = subplots.GasCabinet
	datafactory = datasources.GasCabinet
	filter = 'ASCII text files (*.txt)', '*.txt',


class MainTab(Tab):
	xmin = Float
	xmax = Float
	dateformats = (
		('YY-MM-DD HH:MM:SS', '%y-%m-%d %H:%M:%S'),
		('HH:MM:SS', '%H:%M:%S'),
		('HH:MM', '%H:%M'),
		('MM:SS', '%M:%S'),
	)
	dateformat = Enum(*[i[1] for i in dateformats])
	tablabel = 'Main'

	taboptions = (
		CameraFramePanel,
		CameraTrendPanel,
		QMSPanel,
		GasCabinetPanel,
		TPDirkPanel,
	)
	tabdict = dict((klass.tablabel, klass) for klass in taboptions)
	tablabels = [klass.tablabel for klass in taboptions]

	add = Button()
	subgraph_type =  Enum(*tablabels)

	mainwindow = Any

	def __init__(self, *args, **kwargs):
		super(MainTab, self).__init__(*args, **kwargs)
		self.dateformat = '%H:%M:%S'

	def _add_fired(self):
		self.mainwindow.add_tab(self.tabdict[self.subgraph_type](update_canvas=self.mainwindow.update_canvas, autoscale=self.mainwindow.autoscale))

	def _dateformat_changed(self):
		self.mainwindow.plot.dateformat = self.dateformat
		self.mainwindow.plot.setup_xaxis_labels()
		self.mainwindow.update_canvas()

	traits_view = View(Group(
		Group(
			Item('dateformat', editor=EnumEditor(values=dict((b, '%d:%s' % (i, a)) for (i, (a, b)) in enumerate(dateformats)))),
			Item('xmin'),
			Item('xmax'),
			label='Graph settings',
			show_border=True,
		),
		Group(
			Item('subgraph_type', show_label=False, style='custom', editor=EnumEditor(values=tablabels, format_func=lambda x: x, cols=1)),
			Item('add', show_label=False),
			label='Add subgraph',
			show_border=True,
		),
		layout='normal',
	))


class PythonTab(Tab):
	shell = PythonValue({})
	traits_view = View(
		Item('shell', show_label=False, editor=ShellEditor(share=False))
	)

	tablabel = 'Python'


class MainWindow(HasTraits):
	plot = Instance(plot.Plot)
	figure = Instance(matplotlib.figure.Figure)

	tabs = List(Instance(Tab))

	def on_figure_resize(self, event):
		self.plot.setup_margins()
		self.update_canvas()

	def update_canvas(self):
		wx.CallAfter(self.figure.canvas.draw)

	def autoscale(self):
		# NOTE: this is a workaround for matplotlib's internal autoscaling routines. 
		# it imitates axes.autoscale_view(), but only takes the dataLim into account when
		# there are actually some lines or images in the graph
		axes = [tab.plot.axes for tab in self.tabs if isinstance(tab, SubplotPanel)]
		if not axes:
			return
		for ax in axes:
			ax.autoscale_view(scalex=False)

		dl = [ax.dataLim for ax in axes if ax.lines or ax.images]
		if not dl:
			x0, x1 = 1000., 1001.
		else:
			bb = matplotlib.transforms.BboxBase.union(dl)
			x0, x1 = bb.intervalx
		XL = axes[0].xaxis.get_major_locator().view_limits(x0, x1)
		axes[0].set_xbound(XL)

	def add_tab(self, tab):
		self.tabs.append(tab)

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
		return [MainTab(mainwindow=self), PythonTab()]

	def redraw_figure(self):
		self.plot.clear()
		[self.plot.add_subplot(tab.plot) for tab in self.tabs if isinstance(tab, SubplotPanel)]
		self.plot.setup()
		self.plot.draw()
		self.autoscale()
		self.update_canvas()

	def _plot_default(self):
		p = plot.Plot.newmatplotlibfigure()
		p.setup()
		# At this moment, p.figure.canvas has not yet been initialized, so delay this call
		wx.CallAfter(lambda: p.figure.canvas.mpl_connect('resize_event', self.on_figure_resize))
		return p

	def _figure_default(self):
		return self.plot.figure

	traits_view = View(
			HSplit(
				Item('figure', editor=MPLFigureEditor(), dock='vertical'),
				Item('tabs', style='custom', width=200, editor=ListEditor(use_notebook=True, deletable=True, page_name='.tablabel')),
				show_labels=False,
			),
			resizable=True,
			height=700, width=1100,
			buttons=NoButtons,
		)


if __name__ == '__main__':
	mainwindow = MainWindow()
	mainwindow.configure_traits()
