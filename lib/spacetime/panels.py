from enthought.traits.api import *
from enthought.traits.ui.api import *
import matplotlib.cm
import string
import wx

from . import subplots, datasources, filters, uiutil


def PanelView(*args, **kwargs):
	if 'handler' in kwargs:
		newkwargs = kwargs.copy()
		del newkwargs['handler']
		return View(Group(*args, layout='normal', scrollable=True, **newkwargs), handler=kwargs['handler'])
	return View(Group(*args, layout='normal', scrollable=True, **kwargs))


class Tab(HasTraits):
	pass


class TraitsSavedMeta(HasTraits.__metaclass__):
	def __new__(mcs, name, bases, dict):
		if 'traits_saved' not in dict:
			dict['traits_saved'] = ()
		for base in bases:
			if 'traits_saved' in base.__dict__:
				dict['traits_saved'] = tuple(i for i in base.__dict__['traits_saved'] if 'traits_not_saved' not in dict or i not in dict['traits_not_saved']) + dict['traits_saved']
		return HasTraits.__metaclass__.__new__(mcs, name, bases, dict)


class SerializableTab(Tab):
	__metaclass__ = TraitsSavedMeta
	drawmgr = Instance(uiutil.DrawManager)

	def _delayed_from_serialized(self, src):
		with self.drawmgr.hold():
			# trait_set has to be called separately for each trait to respect the ordering of traits_saved
			for id in self.traits_saved:
				if id in src: # silently ignore unknown settings for backward and forward compatibility
					 self.trait_set(**dict(((id, src[id]),)))

	def from_serialized(self, src):
		if hasattr(self, 'traits_saved'):
			wx.CallAfter(lambda: self._delayed_from_serialized(src))

	def get_serialized(self):
		if hasattr(self, 'traits_saved'):
			return dict((id, getattr(self, id)) for id in self.traits_saved)
		else:
			return dict()


class SubplotPanel(SerializableTab):
	filename = File
	reload = Button
	simultaneity_offset = Float(0.)
	time_dilation_factor = Float(1.)

	plot = Instance(subplots.Subplot)
	visible = Bool(True)
	number = 0

	autoscale = Callable

	# Magic attribute with "class level" "extension inheritance". Does this make any sense?
	# It means that when you derive a class from this class, you only have to
	# specify the attributes that are "new" in the derived class, any
	# attributed listed in one of the parent classes will be added
	# automatically.
	# Anyway, this is possible thanks to the TraitsSavedMeta metaclass.
	traits_saved = 'visible', 'filename', 'simultaneity_offset', 'time_dilation_factor'
	# traits_not_saved = ... can be used to specify parameters that should not be copied in a derived classes

	relativistic_group = Group(
		Item('simultaneity_offset', label='Simultaneity offset (s)', editor=uiutil.FloatEditor()),
		Item('time_dilation_factor', editor=RangeEditor(low=.999, high=1.001)),
		show_border=True,
		label='Relativistic corrections',
	)

	def __init__(self, *args, **kwargs):
		super(SubplotPanel, self).__init__(*args, **kwargs)
		self.__class__.number += 1
		if self.__class__.number != 1:
			self.tablabel = '%s %d' % (self.tablabel, self.__class__.number)

	def redraw_figure(self):
		self.drawmgr.redraw_figure()

	def redraw(self):
		self.drawmgr.redraw_subgraph(lambda: (
			self.plot.clear(),
			self.plot.draw(),
			self.autoscale(self.plot),
		))

	def update(self):
		self.drawmgr.update_canvas()

	def _visible_changed(self):
		self.redraw_figure()

	@on_trait_change('simultaneity_offset, time_dilation_factor')
	def relativistics_changed(self):
		self.plot.adjust_time(self.simultaneity_offset, self.time_dilation_factor)
		self.redraw()


class CameraPanel(SubplotPanel):
	data = Instance(datasources.Camera)

	firstframe = Int(0)
	lastframe = Int(0)
	stepframe = Range(1, 1000000000)
	framecount = Int(0)
	direction = Enum(1, 2)

	traits_saved = 'firstframe', 'lastframe', 'stepframe', 'direction'

	def _direction_changed(self):
		self.data.direction = self.direction
		self.redraw()


class CameraFramePanelHandler(Handler):
	def object_mode_changed(self, info):
		if info.mode.value == 'single frame':
			info.firstframe.label_control.SetLabel('Frame:')
		else:
			info.firstframe.label_control.SetLabel('First frame:')


class CameraFramePanel(CameraPanel):
	channel = Int(0)
	channelcount = Int(0)
	bgsubtract = Bool(True)
	clip = Float(4.)
	colormap = Enum(sorted((m for m in matplotlib.cm.datad if not m.endswith("_r")), key=string.lower))
	interpolation = Enum('nearest', 'bilinear', 'bicubic')
	zoom = Bool(False)
	rotate = Bool(True)

	mode = Enum('single frame', 'film strip')

	is_singleframe = Property(depends_on='mode')
	is_filmstrip = Property(depends_on='mode')

	tablabel = 'Camera'

	traits_saved = 'channel', 'bgsubtract', 'clip', 'colormap', 'interpolation', 'zoom', 'rotate', 'mode'
	
	def __init__(self, *args, **kwargs):
		super(CameraFramePanel, self).__init__(*args, **kwargs)
		self.colormap = 'afmhot'

	def _get_is_singleframe(self):
		return self.mode == 'single frame'

	def _get_is_filmstrip(self):
		return self.mode == 'film strip'

	def _plot_default(self):
		p = subplots.Image()
		p.mode = self.mode
		p.set_colormap(self.colormap)
		return p

	def _mode_changed(self):
		self.plot.mode = self.mode
		self.select_data()
		self.redraw_figure()

	def _colormap_changed(self):
		self.plot.set_colormap(self.colormap)
		self.update()

	def _interpolation_changed(self):
		self.plot.set_interpolation(self.interpolation)
		self.update()

	def _filename_changed(self):
		self.data = datasources.Camera(self.filename)
		self.channelcount = self.data.getchannelcount() - 1
		self.framecount = self.data.getframecount() - 1
		self.firstframe = self.lastframe = 0
		self.settings_changed()

	def _zoom_changed(self):
		# FIXME: this does not remember state
		if self.zoom:
			self.plot.axes.set_xlim(*self.plot.axes.dataLim.intervalx)
		else:
			self.autoscale(self.plot)
		self.update()

	def _rotate_changed(self):
		self.plot.set_rotate(self.rotate)
		self.update()

	def _firstframe_changed(self):
		if self.mode == 'single frame' or self.firstframe > self.lastframe:
			self.lastframe = self.firstframe
			# settings_changed() will be triggered because lastframe changes
		else:
			self.settings_changed()

	def select_data(self):
		if not self.data:
			return
		if self.mode == 'single frame':
			data = self.data.selectchannel(self.channel).selectframes(self.firstframe, self.firstframe, 1)
		else:
			# FIXME: implement a smarter first/last frame selection, don't redraw everything
			data = self.data.selectchannel(self.channel).selectframes(self.firstframe, self.lastframe, self.stepframe)
		if self.bgsubtract:
			data = data.apply_filter(filters.BGSubtractLineByLine)
		if self.clip > 0:
			data = data.apply_filter(filters.ClipStdDev(self.clip))
		self.plot.set_data(data)
		self.plot.tzoom = self.stepframe

	@on_trait_change('channel, bgsubtract, clip, lastframe, stepframe')
	def settings_changed(self):
		self.select_data()
		self.redraw()

	traits_view = PanelView(
		Group(
			Item('visible'),
			Item('filename', editor=uiutil.FileEditor(filter=['Camera RAW files (*.raw)', '*.raw', 'All files', '*'], entries=0)),
			Item('channel', editor=RangeEditor(low=0, high_name='channelcount', mode='spinner')),
			Item('mode', style='custom'),
			Item('firstframe', label='First frame', editor=RangeEditor(low=0, high_name='framecount', mode='spinner')),
			Item('lastframe', label='Last frame', enabled_when='is_filmstrip', editor=RangeEditor(low=0, high_name='framecount', mode='spinner')),
			Item('stepframe', label='Key frame mode', enabled_when='is_filmstrip'),
			Item('direction', editor=EnumEditor(values={1:'1:L2R', 2:'2:R2L'})),
			show_border=True,
			label='General',
		),
		Group(
			Item('colormap'),
			Item('interpolation', editor=EnumEditor(values={'nearest':'1:none', 'bilinear':'2:bilinear', 'bicubic':'3:bicubic'})),
			Group(
				Item('rotate', label='Rotate image', tooltip='Plot scanlines vertically', enabled_when='is_singleframe'),
				show_border=True,
				label='Single frame',
			),
			Group(
				Item('zoom', label='Zoom to fit', enabled_when='is_filmstrip'),
				show_border=True,
				label='Film strip'
			),
			show_border=True,
			label='Display',
		),
		Group(
			Item('bgsubtract', label='Backgr. subtr.', tooltip='Line-by-line linear background subtraction'),
			Item('clip', label='Color clipping', tooltip='Clip colorscale at <number> standard deviations away from the average (0 to disable)'),
			show_border=True,
			label='Filters',
		),
		Include('relativistic_group'),
		handler=CameraFramePanelHandler()
	)


class TimeTrendPanel(SubplotPanel):
	plotfactory = subplots.MultiTrend
	legend = Bool(True)
	ylimits = Instance(uiutil.LogAxisLimits, args=())
	yauto = DelegatesTo('ylimits', 'auto')
	ymin = DelegatesTo('ylimits', 'min')
	ymax = DelegatesTo('ylimits', 'max')
	ylog = DelegatesTo('ylimits', 'log')
	channels = List(Str)
	selected_primary_channels = List(Str)
	data = Instance(datasources.DataSource)

	traits_saved = 'legend', 'yauto', 'ymin', 'ymax', 'ylog', 'selected_primary_channels'

	def _plot_default(self):
		plot = self.plotfactory()
		plot.set_ylim_callback(self.ylim_callback)
		return plot

	def ylim_callback(self, ax):
		self.ymin, self.ymax = ax.get_ylim()

	@on_trait_change('filename, reload')
	def load_file(self):
		if self.filename:
			try:
				self.data = self.datafactory(self.filename)
			except:
				uiutil.Message.file_open_failed(self.filename)
				self.filename = ''
				return
			self.channels = list(self.data.iterchannelnames())
			self.settings_changed()

	@on_trait_change('selected_primary_channels')
	def settings_changed(self):
		self.plot.set_data(self.data.selectchannels(lambda chan: chan.id in self.selected_primary_channels))
		self.redraw()

	@on_trait_change('ymin, ymax, yauto')
	def ylim_changed(self):
		self.plot.set_ylim(self.ylimits.min, self.ylimits.max, self.ylimits.auto)
		self.update()

	def _ylog_changed(self):
		self.plot.set_ylog(self.ylog)
		self.update()

	def _legend_changed(self):
		self.plot.set_legend(self.legend)
		self.update()

	left_yaxis_group = Group(
		Item('channels', editor=ListStrEditor(editable=False, multi_select=True, selected='selected_primary_channels')),
		Item('ylimits', style='custom', label='Limits'),
		show_border=True,
		label='Left y-axis'
	)

	def traits_view(self):
		return PanelView(
			Group(
				Item('visible'),
				Item('filename', editor=uiutil.FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
				Item('reload', show_label=False),
				Item('legend'),
				show_border=True,
				label='General',
			),
			Include('left_yaxis_group'),
			Include('relativistic_group'),
		)


class DoubleTimeTrendPanel(TimeTrendPanel):
	plotfactory = subplots.DoubleMultiTrend
	selected_secondary_channels = List(Str)

	ylimits2 = Instance(uiutil.LogAxisLimits, args=())
	yauto2 = DelegatesTo('ylimits2', 'auto')
	ymin2 = DelegatesTo('ylimits2', 'min')
	ymax2 = DelegatesTo('ylimits2', 'max')
	ylog2 = DelegatesTo('ylimits2', 'log')

	traits_saved = 'selected_secondary_channels', 'yauto2', 'ymin2', 'ymax2', 'ylog2'

	def _plot_default(self):
		plot = self.plotfactory()
		plot.set_ylim_callback(self.ylim_callback)
		return plot

	def ylim_callback(self, ax):
		if ax is self.plot.axes:
			self.ymin, self.ymax = ax.get_ylim()
		elif ax is self.plot.secondaryaxes:
			self.ymin2, self.ymax2 = ax.get_ylim()

	@on_trait_change('ymin2, ymax2, yauto2')
	def ylim2_changed(self):
		self.plot.set_ylim2(self.ylimits2.min, self.ylimits2.max, self.ylimits2.auto)
		self.update()

	def _ylog2_changed(self):
		self.plot.set_ylog2(self.ylog2)
		self.update()

	@on_trait_change('selected_primary_channels, selected_secondary_channels')
	def settings_changed(self):
		self.plot.set_data(
			self.data.selectchannels(lambda chan: chan.id in self.selected_primary_channels),
			self.data.selectchannels(lambda chan: chan.id in self.selected_secondary_channels),
		)
		self.redraw()

	right_yaxis_group = Group(
		Item('channels', editor=ListStrEditor(editable=False, multi_select=True, selected='selected_secondary_channels')),
		Item('ylimits2', style='custom', label='Limits'),
		show_border=True,
		label='Right y-axis'
	)

	def traits_view(self):
		return PanelView(
			Group(
				Item('visible'),
				Item('filename', editor=uiutil.FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
				Item('reload', show_label=False),
				Item('legend'),
				show_border=True,
				label='General',
			),
			Include('left_yaxis_group'),
			Include('right_yaxis_group'),
			Include('relativistic_group'),
		)


class CameraTrendPanel(DoubleTimeTrendPanel, CameraPanel):
	tablabel = 'Camera Trend'
	filter = 'Camera RAW files (*.raw)', '*.raw'

	averaging = Bool(True)

	traits_saved = 'averaging',

	@on_trait_change('filename')
	def load_file(self):
		if self.filename:
			try:
				self.data = datasources.Camera(self.filename)
			except:
				uiutil.Message.file_open_failed(self.filename)
				self.filename = ''
				return
			self.channels = list(self.data.iterchannelnames())
			self.framecount = self.data.getframecount() - 1
			self.lastframe = min(self.framecount, 25)
			self.settings_changed()

	@on_trait_change('averaging, firstframe, lastframe, stepframe, selected_primary_channels, selected_secondary_channels')
	def settings_changed(self):
		if not self.data:
			return
		# FIXME: implement a smarter first/last frame selection, don't redraw everything
		data = self.data.selectframes(self.firstframe, self.lastframe, self.stepframe)
		self.data.averaging = self.averaging
		self.plot.set_data(
			data.selectchannels(lambda chan: chan.id in self.selected_primary_channels),
			data.selectchannels(lambda chan: chan.id in self.selected_secondary_channels),
		)
		self.redraw()

	traits_view = PanelView(
		Group(
			Item('visible'),
			Item('filename', editor=uiutil.FileEditor(filter=['Camera RAW files (*.raw)', '*.raw', 'All files', '*'], entries=0)),
			Item('firstframe', label='First frame', editor=RangeEditor(low=0, high_name='framecount', mode='spinner')),
			Item('lastframe', label='Last frame', editor=RangeEditor(low=0, high_name='framecount', mode='spinner')),
			Item('stepframe', label='Key frame mode'),
			Item('direction', editor=EnumEditor(values={1:'1:L2R', 2:'2:R2L'})), # FIXME: for trends, it should be possible to show both!
			Item('averaging', tooltip='Per-line averaging'),
			Item('legend'),
			show_border=True,
			label='General',
		),
		Include('left_yaxis_group'),
		Include('right_yaxis_group'),
		Include('relativistic_group'),
	)


class CVPanel(CameraTrendPanel):
	tablabel = 'Cyclic voltammetry'
	plotfactory = subplots.CV
	voltage_channel = Int(0)
	current_channel = Int(0)
	channelcount = Int(0)

	traits_not_saved = 'selected_primary_channels', 'selected_secondary_channels'
	traits_saved = 'voltage_channel', 'current_channel'

	@on_trait_change('filename')
	def load_file(self):
		if self.filename:
			try:
				self.data = datasources.Camera(self.filename)
			except:
				uiutil.Message.file_open_failed(self.filename)
				self.filename = ''
				return
			self.channelcount = self.data.getchannelcount() - 1
			self.framecount = self.data.getframecount() - 1
			self.lastframe = min(self.framecount, 25)
			self.settings_changed()

	def _firstframe_changed(self):
		if self.firstframe > self.lastframe:
			self.lastframe = self.firstframe
			# settings_changed() will be triggered because lastframe changes
		else:
			self.settings_changed()

	@on_trait_change('averaging, lastframe, stepframe, voltage_channel, current_channel')
	def settings_changed(self):
		if not self.data:
			return
		# FIXME: implement a smarter first/last frame selection, don't redraw everything
		data = self.data.selectframes(self.firstframe, self.lastframe, self.stepframe)
		self.data.averaging = self.averaging
		self.plot.set_data(
			data.selectchannels(lambda chan: chan.id == str(self.voltage_channel)),
			data.selectchannels(lambda chan: chan.id == str(self.current_channel)),
		)
		self.redraw()

	traits_view = PanelView(
		Group(
			Item('visible'),
			Item('filename', editor=uiutil.FileEditor(filter=['Camera RAW files (*.raw)', '*.raw', 'All files', '*'], entries=0)),
			Item('firstframe', label='First frame', editor=RangeEditor(low=0, high_name='framecount', mode='spinner')),
			Item('lastframe', label='Last frame', editor=RangeEditor(low=0, high_name='framecount', mode='spinner')),
			Item('stepframe', label='Key frame mode'),
			Item('direction', editor=EnumEditor(values={1:'1:L2R', 2:'2:R2L'})), # FIXME: for trends, it should be possible to show both!
			Item('averaging', tooltip='Per-line averaging'),
			show_border=True,
			label='General',
		),
		Group(
			Item('voltage_channel', editor=RangeEditor(low=0, high_name='channelcount', mode='spinner')),
			Item('current_channel', editor=RangeEditor(low=0, high_name='channelcount', mode='spinner')),
			show_border=True,
			label='Channels',
		),
		Include('relativistic_group'),
	)


class QMSPanel(TimeTrendPanel):
	tablabel = 'QMS'
	datafactory = datasources.QMS
	plotfactory = subplots.QMS
	filter = 'Quadera ASCII files (*.asc)', '*.asc'

	def __init__(self, *args, **kwargs):
		super(QMSPanel, self).__init__(*args, **kwargs)
		self.ylog = True


class TPDirkPanel(DoubleTimeTrendPanel):
	tablabel = 'TPDirk'
	plotfactory = subplots.TPDirk
	datafactory = datasources.TPDirk
	filter = 'Dirk\'s ASCII files (*.txt)', '*.txt'

	def __init__(self, *args, **kwargs):
		super(TPDirkPanel, self).__init__(*args, **kwargs)
		self.ylog = True

	@on_trait_change('filename, reload')
	def load_file(self):
		if self.filename:
			try:
				self.data = self.datafactory(self.filename)
			except:
				uiutil.Message.file_open_failed(self.filename)
				self.filename = ''
				return
			self.plot.set_data(self.data)
			self.redraw()

	def traits_view(self):
		return PanelView(
			Group(
				Item('visible'),
				Item('filename', editor=uiutil.FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
				Item('reload', show_label=False),
				Item('legend'),
				show_border=True,
				label='General',
			),
			Group(
				Item('ylimits', style='custom', label='Left limits'),
				Item('ylimits2', style='custom', label='Right limits'),
				show_border=True,
				label='Y axes'
			),
			Include('relativistic_group'),
		)


class GasCabinetPanel(DoubleTimeTrendPanel):
	tablabel = 'LPM gas cabinet'
	plotfactory = subplots.GasCabinet
	datafactory = datasources.GasCabinet
	filter = 'ASCII text files (*.txt)', '*.txt',


class OldGasCabinetPanel(DoubleTimeTrendPanel):
	tablabel = 'Prototype gas cabinet'
	plotfactory = subplots.GasCabinet
	datafactory = datasources.OldGasCabinet
	filter = 'ASCII text files (*.txt)', '*.txt',


class ReactorEnvironmentPanel(DoubleTimeTrendPanel):
	tablabel = 'Reactor Environment logger'
	datafactory = datasources.ReactorEnvironment
	filter = 'ASCII text files (*.txt)', '*.txt',
