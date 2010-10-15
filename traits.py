
import wx

import matplotlib
# We want matplotlib to use a wxPython backend
matplotlib.use('WXAgg')
import matplotlib.figure, matplotlib.transforms, matplotlib.backends.backend_wx, matplotlib.backends.backend_wxagg

from enthought.traits.api import *
from enthought.traits.ui.api import *
from enthought.traits.ui.wx.editor import Editor
from enthought.traits.ui.basic_editor_factory import BasicEditorFactory
from enthought.traits.ui.instance_choice import InstanceFactoryChoice

import glob
import os
import numpy


import subplots
import datasources
import filters
import plot


class _MPLFigureEditor(Editor):
	scrollable  = True

	def init(self, parent):
		self.control = self._create_canvas(parent)
		self.set_tooltip()

	def update_editor(self):
		pass

	def _create_canvas(self, parent):
		""" Create the MPL canvas. """
		# The panel lets us add additional controls.
		panel = wx.Panel(parent, -1, style=wx.CLIP_CHILDREN)
		sizer = wx.BoxSizer(wx.VERTICAL)
		panel.SetSizer(sizer)
		# matplotlib commands to create a canvas
		mpl_control = matplotlib.backends.backend_wxagg.FigureCanvasWxAgg(panel, -1, self.value)
		sizer.Add(mpl_control, 1, wx.LEFT | wx.TOP | wx.GROW)
		toolbar = matplotlib.backends.backend_wx.NavigationToolbar2Wx(mpl_control)
		sizer.Add(toolbar, 0, wx.EXPAND)
		self.value.canvas.SetMinSize((10,10))
		return panel


class MPLFigureEditor(BasicEditorFactory):
	klass = _MPLFigureEditor


class Tab(HasTraits):
	pass


class Subgraph(Tab):
	filename = File
	plot = Instance(subplots.Subplot)
	redraw = Callable
	autoscale = Callable
	number = 0

	def __init__(self, *args, **kwargs):
		super(Subgraph, self).__init__(*args, **kwargs)
		self.__class__.number += 1
		if self.__class__.number != 1:
			self.tablabel = '%s %d' % (self.tablabel, self.__class__.number)

	def update(self):
		self.plot.clear()
		self.plot.draw()
		self.autoscale()
		self.redraw()


class CameraSubgraph(Subgraph):
	channel = Int(0)
	channelcount = Int(0)
	firstframe = Int(0)
	lastframe = Int(0)
	framecount = Int(0)
	bgsubtract = Bool(True)
	clip = Float(4.)
	data = Instance(datasources.Camera)

	tablabel = 'Camera'

	def _plot_default(self):
		return subplots.Image()

	def _filename_changed(self):
		self.data = datasources.Camera(self.filename)
		self.channelcount = self.data.getchannelcount() - 1
		self.framecount = self.data.getframecount() - 1
		self.lastframe = min(self.framecount, 25)
		self.settings_changed()

	@on_trait_change('channel, bgsubtract, clip, firstframe, lastframe')
	def settings_changed(self):
		if not self.data:
			return
		# FIXME: implement a smarter first/last frame selection, don't redraw everything
		data = self.data.selectchannel(self.channel).selectframes(self.firstframe, self.lastframe)
		if self.bgsubtract:
			data = data.apply_filter(filters.BGSubtractLineByLine)
		if self.clip > 0:
			data = data.apply_filter(filters.ClipStdDev(self.clip))
		self.plot.retarget(data)
		self.update()

	traits_view = View(
		Item('filename', editor=FileEditor(filter=['Camera RAW files (*.raw)', '*.raw', 'All files', '*'], entries=0)),
		Item('channel', editor=RangeEditor(low=0, high_name='channelcount')),
		Item('firstframe', label='First frame', editor=RangeEditor(low=0, high_name='framecount')),
		Item('lastframe', label='Last frame', editor=RangeEditor(low=0, high_name='framecount')),
		Item('bgsubtract', label='Backgr. subtr.', tooltip='Line-by-line linear background subtraction'),
		Item('clip', label='Color clipping', tooltip='Clip colorscale at <number> standard deviations away from the average (0 to disable)'),
	)


class TimeTrendSubgraph(Subgraph):
	legend = Bool
	ymin = Float
	ymax = Float

	def _ymin_changed(self):
		self.plot.axes.set_ylim(ymin=self.ymin)
		self.redraw()

	def _ymax_changed(self):
		self.plot.axes.set_ylim(ymax=self.ymax)
		self.redraw()


class QMSSubgraph(TimeTrendSubgraph):
	channels = List(Str)
	selected_channels = List(Str)
	data = Instance(datasources.QMS)

	tablabel = 'QMS'

	def _plot_default(self):
		return subplots.QMS()

	def _filename_changed(self):
		self.data = datasources.QMS(self.filename)
		self.channels = [str(i) for i in self.data.masses]
		self.settings_changed()

	@on_trait_change('selected_channels')
	def settings_changed(self):
		masses = [int(i) for i in self.selected_channels]
		self.plot.retarget(self.data.selectchannels(lambda d: d.mass in masses))
		self.update()

	traits_view = View(
		Item('filename', editor=FileEditor(filter=['Quadera ASCII files (*.asc)', '*.asc', 'All files', '*'], entries=0)),
		Item('channels', editor=ListStrEditor(editable=False, multi_select=True, selected='selected_channels')),
		Item('ymin'),
		Item('ymax'),
		Item('legend'),
	)


class GasCabinetSubgraph(TimeTrendSubgraph):
	channels = List(Str)
	chantups = List(Tuple(Str, Str))
	selected_primary_channels = List(Int)
	selected_secondary_channels = List(Int)
	ymin2 = Float
	ymax2 = Float

	tablabel = 'Gas cabinet'

	def _plot_default(self):
		return subplots.GasCabinet()

	def _ymin2_changed(self):
		self.plot.secondaryaxes.set_ylim(ymin=self.ymin)
		self.redraw()

	def _ymax2_changed(self):
		self.plot.secondaryaxes.set_ylim(ymax=self.ymax)
		self.redraw()

	def _filename_changed(self):
		self.data = datasources.GasCabinet(self.filename)
		self.channels = []
		self.chantups = []
		for c in self.data.controllers:
			for p in self.data.parameters:
				self.channels.append("%s %s" % (c, p))
				self.chantups.append((c, p))
		self.settings_changed()

	@on_trait_change('selected_primary_channels, selected_secondary_channels')
	def settings_changed(self):
		first = [self.chantups[i] for i in self.selected_primary_channels]
		second = [self.chantups[i] for i in self.selected_secondary_channels]
		self.plot.retarget(
			self.data.selectchannels(lambda d: (d.controller, d.parameter) in first),
			self.data.selectchannels(lambda d: (d.controller, d.parameter) in second),
		)
		self.update()

	traits_view = View(
		Item('filename', editor=FileEditor(filter=['ASCII text files (*.txt)', '*.txt', 'All files', '*'], entries=0)),
		Item('channels', label='Left y-axis', editor=ListStrEditor(editable=False, multi_select=True, selected_index='selected_primary_channels')),
		Item('ymin'),
		Item('ymax'),
		Item('channels', label='Right y-axis', editor=ListStrEditor(editable=False, multi_select=True, selected_index='selected_secondary_channels')),
		Item('ymin2'),
		Item('ymax2'),
		Item('legend'),
	)



class GeneralSettings(Tab):
	xmin = Float
	xmax = Float
	dateformat = Enum('HH:MM:SS', 'HH:MM', 'MM:SS', 'MonthDD HH:MM:SS', 'YY-MM-DD HH:MM:SS')

	taboptions = (
		CameraSubgraph,
		QMSSubgraph,
		GasCabinetSubgraph,
	)
	tabdict = dict((klass.tablabel, klass) for klass in taboptions)
	tablabels = [klass.tablabel for klass in taboptions]

	add = Button()
	subgraph_type =  Enum(*tablabels)

	mainwindow = Any

	def _add_fired(self):
		self.mainwindow.add_tab(self.tabdict[self.subgraph_type](redraw=self.mainwindow.redraw_graph, autoscale=self.mainwindow.autoscale))

	traits_view = View(VFlow(
		Group(
			Item('dateformat'),
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
	))


class PythonShell(Tab):
	shell = PythonValue({})
	traits_view = View(
		Item('shell', show_label=False, editor=ShellEditor(share=False))
	)

	tablabel = 'Python'


class MainWindow(HasTraits):
	mainfig = Instance(plot.Plot)
	figure = Instance(matplotlib.figure.Figure)

	tabs = List(Instance(Tab))

	def redraw_graph(self):
		#self.mainfig.reformat_xaxis()
		wx.CallAfter(self.figure.canvas.draw)

	def autoscale(self):
		# NOTE: this is a workaround for matplotlib's internal autoscaling routines. 
		# it imitates axes.autoscale_view(), but only takes the dataLim into account when
		# there are actually some lines or images in the graph
		axes = [tab.plot.axes for tab in self.tabs if isinstance(tab, Subgraph)]
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
		self.rebuild_figure()

	def _tabs_items_changed(self, event):
		#for removed in event.removed:
		#	if not isinstance(removed, Subgraph):
		#		FIXME: veto!
		self.rebuild_figure()

	def _tabs_default(self):
		return [GeneralSettings(mainwindow=self), PythonShell()]

	def rebuild_figure(self):
		self.mainfig.clear()
		[self.mainfig.add_subplot(tab.plot) for tab in self.tabs if isinstance(tab, Subgraph)]
		self.mainfig.setup()
		[tab.update() for tab in self.tabs if isinstance(tab, Subgraph)]
		self.redraw_graph()

	def _mainfig_default(self):
		figure = plot.Plot.newmatplotlibfigure()
		figure.setup()
		return figure

	def _figure_default(self):
		return self.mainfig.figure

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
