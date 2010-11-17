from enthought.traits.api import *
from enthought.traits.ui.api import *
import matplotlib.cm
import string

from . import subplots, datasources, filters


class Tab(HasTraits):
	pass


class SubplotPanel(Tab):
	filename = File
	reload = Button

	plot = Instance(subplots.Subplot)
	update_canvas = Callable
	autoscale = Callable
	redraw_figure = Callable
	visible = Bool(True)
	number = 0
	hold = False

	def __init__(self, *args, **kwargs):
		super(SubplotPanel, self).__init__(*args, **kwargs)
		self.__class__.number += 1
		if self.__class__.number != 1:
			self.tablabel = '%s %d' % (self.tablabel, self.__class__.number)

	def redraw(self):
		if not self.hold:
			self.plot.clear()
			self.plot.draw()
			self.autoscale(self.plot.axes)
			self.update_canvas()

	def _visible_changed(self):
		self.redraw_figure()


class CameraPanel(SubplotPanel):
	data = Instance(datasources.Camera)

	firstframe = Int(0)
	lastframe = Int(0)
	stepframe = Range(1, 1000000000)
	framecount = Int(1000000000) # force different range selector
	direction = Enum(1, 2)

	def _direction_changed(self):
		self.data.direction = self.direction
		self.redraw()


class CameraFramePanelHandler(Handler):
	def object_mode_changed(self, info):
		if info.mode.value == 'single frame':
			info.lastframe.enabled = False
			info.stepframe.enabled = False
			info.zoom.enabled = False
			info.rotate.enabled = True
			info.firstframe.label_control.SetLabel('Frame:')
		else:
			info.lastframe.enabled = True
			info.stepframe.enabled = True
			info.zoom.enabled = True
			info.rotate.enabled = False
			info.firstframe.label_control.SetLabel('First frame:')


class CameraFramePanel(CameraPanel):
	channel = Int(0)
	channelcount = Int(1000000000)
	bgsubtract = Bool(True)
	clip = Float(4.)
	colormap = Enum(sorted((m for m in matplotlib.cm.datad if not m.endswith("_r")), key=string.lower))
	interpolation = Enum('nearest', 'bilinear', 'bicubic')
	zoom = Bool(False)
	rotate = Bool(True)

	mode = Enum('single frame', 'film strip')

	tablabel = 'Camera'
	
	def __init__(self, *args, **kwargs):
		super(CameraFramePanel, self).__init__(*args, **kwargs)
		self.colormap = 'afmhot'

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
		self.update_canvas()

	def _interpolation_changed(self):
		self.plot.set_interpolation(self.interpolation)
		self.update_canvas()

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
			self.autoscale()
		self.update_canvas()

	def _rotate_changed(self):
		self.plot.set_rotate(self.rotate)
		self.update_canvas()

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

	traits_view = View(Group(
		Group(
			Item('visible'),
			Item('filename', editor=FileEditor(filter=['Camera RAW files (*.raw)', '*.raw', 'All files', '*'], entries=0)),
			Item('channel', editor=RangeEditor(low=0, high_name='channelcount')),
			Item('mode', style='custom'),
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
			Group(
				Item('rotate', label='Rotate image', tooltip='Plot scanlines vertically'),
				show_border=True,
				label='Single frame',
			),
			Group(
				Item('zoom', label='Zoom to fit'),
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
		layout='normal',
	),
		handler=CameraFramePanelHandler()
	)


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

	@on_trait_change('filename, reload')
	def load_file(self):
		if self.filename:
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
				Item('visible'),
				Item('filename', editor=FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
				Item('reload', show_label=False),
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
				Item('visible'),
				Item('filename', editor=FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
				Item('reload', show_label=False),
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

	averaging = Bool(True)

	def _filename_changed(self):
		self.data = datasources.Camera(self.filename)
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

	traits_view = View(Group(
		Group(
			Item('visible'),
			Item('filename', editor=FileEditor(filter=['Camera RAW files (*.raw)', '*.raw', 'All files', '*'], entries=0)),
			Item('firstframe', label='First frame', editor=RangeEditor(low=0, high_name='framecount')),
			Item('lastframe', label='Last frame', editor=RangeEditor(low=0, high_name='framecount')),
			Item('stepframe', label='Key frame mode'),
			Item('direction', editor=EnumEditor(values={1:'1:L2R', 2:'2:R2L'})), # FIXME: for trends, it should be possible to show both!
			Item('averaging', tooltip='Per-line averaging'),
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

	@on_trait_change('filename, reload')
	def load_file(self):
		if self.filename:
			self.data = self.datafactory(self.filename)
			self.plot.set_data(self.data)
			self.redraw()

	def traits_view(self):
		return View(Group(
			Group(
				Item('visible'),
				Item('filename', editor=FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
				Item('reload', show_label=False),
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
	tablabel = 'LPM gas cabinet'
	plotfactory = subplots.GasCabinet
	datafactory = datasources.GasCabinet
	filter = 'ASCII text files (*.txt)', '*.txt',


class OldGasCabinetPanel(DoubleTimeTrendPanel):
	tablabel = 'Prototype gas cabinet'
	plotfactory = subplots.GasCabinet
	datafactory = datasources.OldGasCabinet
	filter = 'ASCII text files (*.txt)', '*.txt',
