import string

from enthought.traits.api import *
from enthought.traits.ui.api import *

import matplotlib.cm

from ..generic.panels import SubplotPanel, PanelView, DoubleTimeTrendPanel, XlimitsPanel
from ..generic.subplots import Image
from ... import uiutil

from . import datasources, subplots, filters


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
		p = Image()
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


class CameraTrendPanel(DoubleTimeTrendPanel, CameraPanel, XlimitsPanel):
	tablabel = 'Camera Trend'
	filter = 'Camera RAW files (*.raw)', '*.raw'
	plotfactory = subplots.CameraTrend

	averaging = Bool(True)
	direction = Enum(1, 2, 3)
	fft = Bool(False)
	not_fft = Property(depends_on='fft')

	traits_saved = 'averaging', 'fft'

	def _get_not_fft(self):
		return not self.fft

	def _fft_changed(self):
		self.plot.fft = self.fft
		with self.drawmgr.hold():
			self.settings_changed()
			self.redraw_figure()

	def reset_autoscale(self):
		DoubleTimeTrendPanel.reset_autoscale(self)
		XlimitsPanel.reset_autoscale(self)

	def _plot_default(self):
		plot = super(CameraTrendPanel, self)._plot_default()
		plot.set_xlim_callback(self.xlim_callback)
		return plot

	@on_trait_change('filename')
	def load_file(self):
		if self.filename:
			try:
				self.data = datasources.Camera(self.filename)
			except:
				uiutil.Message.file_open_failed(self.filename, parent=self.parent)
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
		if self.fft:
			data = self.data.selectframes(self.firstframe, self.firstframe, 1)
		else:
			data = self.data.selectframes(self.firstframe, self.lastframe, self.stepframe)
		self.data.averaging = self.averaging
		self.data.fft = self.fft
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
			Item('lastframe', label='Last frame', editor=RangeEditor(low=0, high_name='framecount', mode='spinner'), enabled_when='not_fft'),
			Item('stepframe', label='Key frame mode', enabled_when='not_fft'),
			Item('direction', editor=EnumEditor(values={1:'1:L2R', 2:'2:R2L', 3:'3:both'})),
			Item('averaging', tooltip='Per-line averaging', enabled_when='not_fft'),
			Item('fft', label='FFT', tooltip='Perform Fast Fourier Transform'),
			Item('legend'),
			show_border=True,
			label='General',
		),
		Include('left_yaxis_group'),
		Include('right_yaxis_group'),
		Group(
			Item('xlimits', style='custom', label='Limits', enabled_when='fft'),
			show_border=True,
			label='X-axis',
		),
		Include('relativistic_group'),
	)
