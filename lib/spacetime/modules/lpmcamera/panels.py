import string

from enthought.traits.api import *
from enthought.traits.ui.api import *

import matplotlib.cm

from ..generic.panels import SubplotPanel, DoubleTimeTrendPanel, XlimitsPanel
from ..generic.subplots import Image
from ...gui import support

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
	id = 'camera'
	label = 'Camera'
	desc = 'Reads Camera RAW files and plots one or more images.'

	channel = Int(0)
	channelcount = Int(0)

	filter_list = (
		('bgs_line-by-line', 'line-by-line background subtraction', filters.array(filters.bgs_line_by_line)),
		('bgs_plane',        'plane background subtraction',        filters.array(filters.bgs_plane)),
		('diff_line',        'line-by-line differential',           filters.array(filters.diff_line)),
	)
	filter_map = dict((i, f) for (i, s, f) in filter_list)
	filter = Enum('none', *[i for (i, s, f) in filter_list])

	clip = Float(4.)
	colormap = Enum(sorted((m for m in matplotlib.cm.datad if not m.endswith("_r")), key=string.lower))
	interpolation = Enum('nearest', 'bilinear', 'bicubic')
	zoom = Bool(False)
	rotate = Bool(True)

	mode = Enum('single frame', 'film strip')

	is_singleframe = Property(depends_on='mode')
	is_filmstrip = Property(depends_on='mode')

	traits_saved = 'channel', 'filter', 'clip', 'colormap', 'interpolation', 'zoom', 'rotate', 'mode'
	
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
		if self.filter in self.filter_map:
			data = data.apply_filter(self.filter_map[self.filter])
		if self.clip > 0:
			data = data.apply_filter(filters.ClipStdDev(self.clip))
		self.plot.set_data(data)
		self.plot.tzoom = self.stepframe

	@on_trait_change('channel, filter, clip, lastframe, stepframe')
	def settings_changed(self):
		self.select_data()
		self.redraw()

	traits_view = support.PanelView(
		Group(
			Item('visible'),
			Item('filename', editor=support.FileEditor(filter=['Camera RAW files (*.raw)', '*.raw', 'All files', '*'], entries=0)),
			Item('channel', editor=RangeEditor(low=0, high_name='channelcount', mode='spinner')),
			Item('mode', style='custom'),
			Item('firstframe', label='First frame', editor=RangeEditor(low=0, high_name='framecount', mode='spinner')),
			Item('lastframe', label='Last frame', enabled_when='is_filmstrip', editor=RangeEditor(low=0, high_name='framecount', mode='spinner')),
			Item('stepframe', label='Key frame mode', enabled_when='is_filmstrip'),
			Item('direction', editor=EnumEditor(values=support.EnumMapping([(1, 'L2R'), (2, 'R2L')]))),
			show_border=True,
			label='General',
		),
		Group(
			Item('colormap'),
			Item('interpolation', editor=EnumEditor(values=support.EnumMapping([('nearest', 'none'), 'bilinear', 'bicubic']))),
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
			Item('filter', label='Filtering', editor=EnumEditor(values=support.EnumMapping([(i, s) for (i, s, f) in filter_list]))),
			Item('clip', label='Color clipping', tooltip='Clip colorscale at <number> standard deviations away from the average (0 to disable)', editor=support.FloatEditor()),
			show_border=True,
			label='Filters',
		),
		Include('relativistic_group'),
		handler=CameraFramePanelHandler()
	)


class CameraTrendPanel(DoubleTimeTrendPanel, CameraPanel, XlimitsPanel):
	id = 'cameratrend'
	label = 'Camera Trend'
	desc = 'Reads Camera RAW files and makes graphs of one or more channels as a function of time, frequency (performing FFT) or versus another channel.'

	filter = 'Camera RAW files (*.raw)', '*.raw'
	plotfactory = subplots.CameraTrend

	averaging = Bool(True)
	direction = Enum(1, 2, 3)

	xaxis_type = Str('time')
	xaxis_type_options = Property(depends_on='channels')
	prev_xaxis_type = None
	fft = Property(depends_on='xaxis_type')
	not_fft = Property(depends_on='fft')
	independent_x = Property(depends_on='xaxis_type')

	traits_saved = 'averaging', 'xaxis_type'

	def _get_fft(self):
		return self.xaxis_type == 'fft'

	def _get_not_fft(self):
		return not self.fft

	def _get_independent_x(self):
		return self.xaxis_type != 'time'

	def _get_xaxis_type_options(self):
		return support.EnumMapping([('time', 'Time'), ('fft', 'Frequency (FFT)')] + [(i, 'Channel {0}'.format(i)) for i in self.channels])

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
				support.Message.file_open_failed(self.filename, parent=self.parent)
				self.filename = ''
				return
			self.channels = list(self.data.iterchannelnames())
			self.framecount = self.data.getframecount() - 1
			self.lastframe = min(self.framecount, 25)
			self.settings_changed()

	def _xaxis_type_changed(self):
		with self.drawmgr.hold():
			self._firstframe_changed() # this makes sure that firstframe <= lastframe and calls settings_changed()
			if self.prev_xaxis_type is None or (
					self.prev_xaxis_type != self.xaxis_type
					and 'time' in (self.prev_xaxis_type, self.xaxis_type)
				):
				self.redraw_figure()
			self.prev_xaxis_type = self.xaxis_type

	def _firstframe_changed(self):
		if (self.fft and self.firstframe != self.lastframe) or self.firstframe > self.lastframe:
			self.lastframe = self.firstframe
			# settings_changed() will be triggered because lastframe changes
		else:
			self.settings_changed()

	@on_trait_change('averaging, lastframe, stepframe, selected_primary_channels, selected_secondary_channels')
	def settings_changed(self):
		if not self.data:
			return
		# FIXME: implement a smarter first/last frame selection, don't redraw everything
		if self.fft:
			data = self.data.selectframes(self.firstframe, self.firstframe, 1)
		else:
			data = self.data.selectframes(self.firstframe, self.lastframe, self.stepframe)
		self.data.averaging = self.averaging
		self.plot.fft = self.data.fft = self.fft

		y1 = data.selectchannels(lambda chan: chan.id in self.selected_primary_channels)
		y2 = data.selectchannels(lambda chan: chan.id in self.selected_secondary_channels)
		if self.xaxis_type in self.channels:
			self.plot.set_data(y1, y2, data.selectchannels(lambda chan: chan.id == self.xaxis_type))
		else:
			self.plot.set_data(y1, y2)
		self.redraw()

	traits_view = support.PanelView(
		Group(
			Item('visible'),
			Item('filename', editor=support.FileEditor(filter=['Camera RAW files (*.raw)', '*.raw', 'All files', '*'], entries=0)),
			Item('firstframe', label='First frame', editor=RangeEditor(low=0, high_name='framecount', mode='spinner')),
			Item('lastframe', label='Last frame', editor=RangeEditor(low=0, high_name='framecount', mode='spinner'), enabled_when='not_fft'),
			Item('stepframe', label='Key frame mode', enabled_when='not_fft'),
			Item('direction', editor=EnumEditor(values=support.EnumMapping([(1, 'L2R'), (2, 'R2L'), (3, 'both')]))),
			Item('averaging', tooltip='Per-line averaging', enabled_when='not_fft'),
			Item('legend'),
			show_border=True,
			label='General',
		),
		Group(
			Item('xaxis_type', label='Data', editor=EnumEditor(name='xaxis_type_options')),
			Item('xlimits', style='custom', label='Limits', enabled_when='independent_x'),
			show_border=True,
			label='X-axis',
		),
		Include('left_yaxis_group'),
		Include('right_yaxis_group'),
		Include('relativistic_group'),
	)
