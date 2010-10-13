
import wx

import matplotlib
# We want matplotlib to use a wxPython backend
matplotlib.use('WXAgg')
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.backends.backend_wx import NavigationToolbar2Wx

from enthought.traits.api import *
from enthought.traits.ui.api import *
from enthought.traits.ui.wx.editor import Editor
from enthought.traits.ui.basic_editor_factory import BasicEditorFactory
from enthought.traits.ui.instance_choice import InstanceFactoryChoice

import glob
import os
import numpy


from redesign import MainFigure
import subplots
import datasources
import filters


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
		mpl_control = FigureCanvas(panel, -1, self.value)
		sizer.Add(mpl_control, 1, wx.LEFT | wx.TOP | wx.GROW)
		toolbar = NavigationToolbar2Wx(mpl_control)
		sizer.Add(toolbar, 0, wx.EXPAND)
		self.value.canvas.SetMinSize((10,10))
		return panel


class MPLFigureEditor(BasicEditorFactory):
	klass = _MPLFigureEditor

class Subgraph(HasTraits):
	filename = File
	axes = Instance(Axes)
	plot = Instance(subplots.Subplot)
	redraw = Callable

	def build(self, axes):
		self.axes = axes

	def update(self):
		while len(self.axes.lines):
			del self.axes.lines[-1]
		self.plot.build(self.axes)
		self.redraw()


class SubgraphCamera(Subgraph):
	channel = Int(0)
	bgsubtract = Bool(True)
	clip = Float(4.)
	data = Instance(datasources.Camera)

	def _filename_changed(self):
		self.data = datasources.Camera(self.filename)
		self.settings_changed()

	@on_trait_change('channel, bgsubtract, clip')
	def settings_changed(self):
		data = self.data.selectchannel(self.channel)
		if self.bgsubtract:
			data = data.apply_filter(filters.BGSubtractLineByLine)
		if self.clip > 0:
			data = data.apply_filter(filters.ClipStdDev(self.clip))
		self.plot = subplots.Image(data)
		self.update()

	traits_view = View(
		Item('filename'),
		Item('channel'),
		Item('bgsubtract', label='Backgr. subtr.'),
		Item('clip', label='Color clipping'),
	)


class TimeTrendSubgraph(Subgraph):
	legend = Bool
	ymin = Float
	ymax = Float

	def _ymin_changed(self):
		self.axes.set_ylim(ymin=self.ymin)
		self.redraw()

	def _ymax_changed(self):
		self.axes.set_ylim(ymax=self.ymax)
		self.redraw()


class SubgraphQMS(TimeTrendSubgraph):
	channels = List(Str)
	selected_channels = List(Str)
	data = Instance(datasources.QMS)

	def _filename_changed(self):
		self.data = datasources.QMS(self.filename)
		self.channels = [str(i) for i in self.data.masses]
		self.settings_changed()

	@on_trait_change('selected_channels')
	def settings_changed(self):
		masses = [int(i) for i in self.selected_channels]
		self.plot = subplots.QMS(self.data.selectchannels(lambda d: d.mass in masses)) # FIXME
		self.update()

	traits_view = View(
		Item('filename'),
		Item('channels', editor=ListStrEditor(editable=False, multi_select=True, selected='selected_channels')),
		Item('ymin'),
		Item('ymax'),
		Item('legend'),
	)


class SubgraphGasCabinet(TimeTrendSubgraph):
	channels = List(Str)
	chantups = List(Tuple(Str, Str))
	selected_primary_channels = List(Int)
	selected_secondary_channels = List(Int)
	ymin2 = Float
	ymax2 = Float

	secondaryaxes = Instance(Axes) # FIXME: hack
	secondarydata = True

	def _ymin2_changed(self):
		self.secondaryaxes.set_ylim(ymin=self.ymin)
		self.redraw()

	def _ymax2_changed(self):
		self.secondaryaxes.set_ylim(ymax=self.ymax)
		self.redraw()

	def update(self):
		while len(self.secondaryaxes.lines):
			del self.secondaryaxes.lines[-1]
		self.plot.secondaryaxes = self.secondaryaxes # FIXME: hack continued
		super(SubgraphGasCabinet, self).update()

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
		self.plot = subplots.MultiTrend(
			self.data.selectchannels(lambda d: (d.controller, d.parameter) in first),
			self.data.selectchannels(lambda d: (d.controller, d.parameter) in second),
			formatter=subplots.GasCabinetFormatter())
		self.update()

	traits_view = View(
		Item('filename'),
		Item('channels', label='Left y-axis', editor=ListStrEditor(editable=False, multi_select=True, selected_index='selected_primary_channels')),
		Item('ymin'),
		Item('ymax'),
		Item('channels', label='Right y-axis', editor=ListStrEditor(editable=False, multi_select=True, selected_index='selected_secondary_channels')),
		Item('ymin2'),
		Item('ymax2'),
		Item('legend'),

	)

class GeneralSettings(HasTraits):
	xmin = Float
	xmax = Float
	dateformat = Enum('HH:MM:SS', 'HH:MM', 'MM:SS', 'MonthDD HH:MM:SS', 'YY-MM-DD HH:MM:SS')


class MainWindow(HasTraits):
	mainfig = Instance(MainFigure)
	figure = Instance(Figure)

	camera = Instance(SubgraphCamera)
	qms = Instance(SubgraphQMS)
	gascab = Instance(SubgraphGasCabinet)
	general = Instance(GeneralSettings, args=())

	def redraw_graph(self):
		#self.mainfig.reformat_xaxis()
		wx.CallAfter(self.figure.canvas.draw)

	def _camera_default(self):
		return SubgraphCamera(redraw=self.redraw_graph)

	def _qms_default(self):
		return SubgraphQMS(redraw=self.redraw_graph)

	def _gascab_default(self):
		return SubgraphGasCabinet(redraw=self.redraw_graph)

	def _mainfig_default(self):
		figure = MainFigure()
		figure.add_plot(self.camera)
		figure.add_plot(self.qms)
		figure.add_plot(self.gascab)
		figure.build()
		return figure

	def _figure_default(self):
		return self.mainfig.figure

	traits_view = View(
			HSplit(
				Item('figure', editor=MPLFigureEditor(), dock='vertical'),
				Group(
					Item('general', style='custom', dock='tab', width=200),
					Item('camera', label='Camera', style='custom', dock='tab'),
					Item('qms', label='QMS', style='custom', dock='tab'),
					Item('gascab', label='Gas cabinet', style='custom', dock='tab'),
					layout='tabbed', show_labels=False,
				),
				show_labels=False
			),
			resizable=True,
			height=700, width=1100,
			buttons=NoButtons
		)


if __name__ == '__main__':
	MainWindow().configure_traits()
