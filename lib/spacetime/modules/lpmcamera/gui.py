# This file is part of Spacetime.
#
# Copyright (C) 2010-2012 Leiden University.
# Written by Sander Roobol.
#
# Spacetime is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Spacetime is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import enthought.traits.api as traits
import enthought.traits.ui.api as traitsui
import numpy

from ..generic import filters
from ..generic.gui import SerializableComponent, SubplotGUI, DoubleTimeTrendGUI, XlimitsGUI, FalseColorImageGUI, SingleFrameAnimation
from ..generic.subplots import Image
from ...gui import support

from . import datasources, subplots


class FourierFilterHandler(traitsui.Handler):
	def close(self, info, is_ok=None):
		ff = info.ui.context['object']
		if not is_ok or not ff.transferfunc:
			return True

		try:
			func = filters.code2func(ff.transferfunc, ff.preexec, variable='f')
			func(numpy.linspace(-100., 100., 100))
		except:
			support.Message.exception(message='The filter function does not evaluate properly.', desc='Check the output below and resolve the problem.', title='Invalid filter', parent=info.ui.control)
			return False
		else:
			return True


class FourierFilter(SerializableComponent):
	preexec = traits.Str()
	transferfunc = traits.Str()

	windows = [
		'none', 'triang', 'blackman', 'hamming', 'hann', 'bartlett', 'flattop', 'parzen', 'bohman', 'blackmanharris', 'nuttall', 'barthann',
		('kaiser', 'beta'),
		('gaussian', 'stddev'),
		('general_gaussian', 'power', 'width'),
		('slepian', 'width'),
		('chebwin', 'attenuation'),
	]
	window_mapping = dict((i,()) if isinstance(i, basestring) else (i[0], i[1:]) for i in windows)
	window = traits.Enum([i if isinstance(i, basestring) else i[0] for i in windows])
	window_p1 = traits.Float(1)
	window_p2 = traits.Float(1)
	needs_p1 = traits.Property(depends_on='window')	
	needs_p2 = traits.Property(depends_on='window')

	traits_saved = 'preexec', 'transferfunc', 'window', 'window_p1', 'window_p2'

	def _get_needs_p1(self):
		return len(self.window_mapping[self.window]) >= 1

	def _get_needs_p2(self):
		return len(self.window_mapping[self.window]) >= 2

	def get_window_tuple(self):
		if self.window == 'none':
			return None
		else:
			window = self.window, self.window_p1, self.window_p2
			return window[:1+len(self.window_mapping[self.window])] # chop of unneeded parameters

	def get_callable(self, variable):
		return filters.code2func(self.transferfunc, self.preexec, variable=variable)

	def __nonzero__(self):
		return bool(self.transferfunc)

	def traits_view(self):
		window_enum = []
		for w in self.windows:
			if isinstance(w, basestring):
				window_enum.append(w)
			else:
				if len(w) == 2:
					label = '{0} (parameter: {1})'.format(*w)
				elif len(w) == 3:
					label = '{0} (parameters: {1}, {2})'.format(*w)
				window_enum.append((w[0], label))
		return traitsui.View(
			traitsui.VGroup(
				traitsui.Group(
					traitsui.Item('transferfunc', style='custom', tooltip="Transfer function of the filter, as a function of frequency 'f'. Must be a single expression. May contain other variables, if they are defined below."),
					show_border=True,
					show_labels=False,
					label='Transfer function',
				),
				traitsui.Group(
					traitsui.Item('preexec', style='custom', tooltip='Any Python code to be executed before evaluating the transfer function. Can be used to define parameters.'),
					show_border=True,
					show_labels=False,
					label='Pre-execution code',

				),
				traitsui.Group(
					traitsui.Item('window', editor=traitsui.EnumEditor(values=support.EnumMapping(window_enum))),
					traitsui.Item('window_p1', label='Window parameter 1', editor=support.FloatEditor(), enabled_when='needs_p1'),
					traitsui.Item('window_p2', label='Window parameter 2', editor=support.FloatEditor(), enabled_when='needs_p2'),
					show_border=True,
					label='Windowing',

				),
		
			),
			kind='modal',
			height=400,
			width=300,
			buttons=traitsui.OKCancelButtons,
			handler=FourierFilterHandler,
		)


class CameraGUI(SubplotGUI):
	data = traits.Instance(datasources.Camera)

	firstframe = traits.Int(0)
	lastframe = traits.Int(0)
	stepframe = traits.Range(1, 1000000000)
	framecount = traits.Int(0)
	direction = traits.Enum(1, 2)

	edit_fourierfilter = traits.Button
	fourierfilter = traits.Instance(FourierFilter, args=())

	traits_saved = 'firstframe', 'lastframe', 'stepframe', 'direction', 'fourierfilter.*'

	def _direction_changed(self):
		self.data.direction = self.direction
		self.rebuild()

	def _edit_fourierfilter_fired(self):
		if self.fourierfilter.edit_traits().result:
			self.settings_changed()


class CameraFrameGUIHandler(traitsui.Handler):
	def object_mode_changed(self, info):
		if info.mode.value == 'single frame':
			info.firstframe.label_control.SetLabel('Frame:')
		else:
			info.firstframe.label_control.SetLabel('First frame:')


class CameraFrameGUI(FalseColorImageGUI, CameraGUI, SingleFrameAnimation):
	id = 'camera'
	label = 'Camera'
	desc = 'Reads Camera RAW files and plots one or more images.'

	plotfactory = Image

	default_colormap = 'afmhot'

	channel = traits.Int(0)
	channelcount = traits.Int(0)

	filter_list = (
		('bgs_line-by-line', 'line-by-line background subtraction', filters.array(filters.bgs_line_by_line)),
		('bgs_plane',        'plane background subtraction',        filters.array(filters.bgs_plane)),
		('diff_line',        'line-by-line differential',           filters.array(filters.diff_line)),
	)
	filter_map = dict((i, f) for (i, s, f) in filter_list)
	filter = traits.Enum('none', *[i for (i, s, f) in filter_list])

	clip = traits.Float(4.)
	rotate = traits.Bool(False)

	mode = traits.Enum('single frame', 'film strip')

	is_singleframe = traits.Property(depends_on='mode')
	is_filmstrip = traits.Property(depends_on='mode')

	traits_saved = 'channel', 'filter', 'clip', 'rotate', 'mode'

	animation_framenumber_trait = 'firstframe'
	animation_framenumber_low = 0
	animation_framenumber_high = 'framecount'

	def _get_is_singleframe(self):
		return self.mode == 'single frame'

	def _get_is_filmstrip(self):
		return self.mode == 'film strip'

	def _plot_default(self):
		p = super(CameraFrameGUI, self)._plot_default()
		p.mode = self.mode
		return p

	def _mode_changed(self):
		self.plot.mode = self.mode
		self.select_data()
		self.rebuild_figure()

	def _filename_changed(self):
		self.data = datasources.Camera(self.filename)
		self.channelcount = self.data.getchannelcount() - 1
		self.framecount = self.data.getframecount() - 1
		self.firstframe = self.lastframe = 0
		self.settings_changed()

	def _rotate_changed(self):
		self.plot.set_rotate(self.rotate)
		self.redraw()

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
		if self.fourierfilter:
			data = data.apply_filter(filters.fourier(self.fourierfilter.get_callable('f'), self.fourierfilter.get_window_tuple()))
		if self.filter in self.filter_map:
			data = data.apply_filter(self.filter_map[self.filter])
		if self.cauto and self.clip > 0:
			data = data.apply_filter(filters.ClipStdDev(self.clip))
		self.plot.set_data(data)
		self.plot.tzoom = self.stepframe

	# replace the inherited clim_changed() to make sure select_data() is called before rebuild()
	@traits.on_trait_change('cmin, cmax, cauto, clog')
	def clim_changed(self, name, new):
		# we need callback protection, but cannot use the decorator since we will call the inherited method
		if self.context.callbacks.is_avoiding(self.climits):
			return
		if name == 'cauto':
			self.select_data()
		super(CameraFrameGUI, self).clim_changed()

	@traits.on_trait_change('filter, channel') # when these traits change, we want color autoscaling back
	def settings_changed_rescale(self):
		if self.cauto:
			self.settings_changed()
		else:
			self.cauto = True # this will also call select_data() and rebuild()

	@traits.on_trait_change('clip, lastframe, stepframe')
	def settings_changed(self):
		self.select_data()
		self.rebuild()

	traits_view = support.PanelView(
		traitsui.Group(
			traitsui.Item('visible'),
			traitsui.Item('filename', editor=support.FileEditor(filter=['Camera RAW files (*.raw)', '*.raw', 'All files', '*'], entries=0)),
			traitsui.Item('channel', editor=support.RangeEditor(low=0, high_name='channelcount', mode='spinner')),
			traitsui.Item('mode', style='custom'),
			traitsui.Item('firstframe', label='First frame', editor=support.RangeEditor(low=0, high_name='framecount', mode='spinner')),
			traitsui.Item('lastframe', label='Last frame', enabled_when='is_filmstrip', editor=support.RangeEditor(low=0, high_name='framecount', mode='spinner')),
			traitsui.Item('stepframe', label='Key frame mode', enabled_when='is_filmstrip', editor=support.RangeEditor()),
			traitsui.Item('direction', editor=traitsui.EnumEditor(values=support.EnumMapping([(1, 'L2R'), (2, 'R2L')]))),
			show_border=True,
			label='General',
		),
		traitsui.Group(
			traitsui.Item('size'),
			traitsui.Item('scalebar'),
			traitsui.Item('colormap'),
			traitsui.Item('interpolation', editor=traitsui.EnumEditor(values=support.EnumMapping([('nearest', 'none'), 'bilinear', 'bicubic']))),
			traitsui.Item('climits', style='custom', label='Color scale'),
			traitsui.Item('clip', label='Color clipping', enabled_when='cauto', tooltip='When autoscaling, clip colorscale at <number> standard deviations away from the average (0 to disable)', editor=support.FloatEditor()),
			traitsui.Item('rotate', label='Rotate image', tooltip='Plot scanlines vertically (always enabled in film strip mode)', enabled_when='is_singleframe'),
			traitsui.Item('filter', label='Filtering', editor=traitsui.EnumEditor(values=support.EnumMapping([('none', 'none')] + [(i, s) for (i, s, f) in filter_list]))),
			traitsui.Item('edit_fourierfilter', show_label=False, editor=traitsui.ButtonEditor(label='1D Fourier options...')),
			show_border=True,
			label='Display',
		),
		traitsui.Include('relativistic_group'),
		handler=CameraFrameGUIHandler()
	)


class CameraTrendGUI(DoubleTimeTrendGUI, CameraGUI, XlimitsGUI):
	id = 'cameratrend'
	label = 'Camera Trend'
	desc = 'Reads Camera RAW files and makes graphs of one or more channels as a function of time, frequency (performing FFT) or versus another channel.'

	filter = 'Camera RAW files (*.raw)', '*.raw'
	plotfactory = subplots.CameraTrend

	averaging = traits.Bool(True)
	direction = traits.Enum(1, 2, 3)

	xaxis_type = traits.Str('time')
	xaxis_type_options = traits.Property(depends_on='channel_names')
	prev_xaxis_type = None
	fft = traits.Property(depends_on='xaxis_type')
	not_fft = traits.Property(depends_on='fft')
	independent_x = traits.Property(depends_on='xaxis_type')

	traits_saved = 'averaging', 'xaxis_type'

	def _get_fft(self):
		return self.xaxis_type == 'fft'

	def _get_not_fft(self):
		return not self.fft

	def _get_independent_x(self):
		return self.xaxis_type != 'time'

	@traits.cached_property
	def _get_xaxis_type_options(self):
		return support.EnumMapping([('time', 'Time'), ('fft', 'Frequency (FFT)')] + [(i, 'Channel {0}'.format(i)) for i in self.channel_names])

	def reset_autoscale(self):
		DoubleTimeTrendGUI.reset_autoscale(self)
		XlimitsGUI.reset_autoscale(self)

	def _plot_default(self):
		plot = super(CameraTrendGUI, self)._plot_default()
		plot.set_xlim_callback(self.xlim_callback)
		return plot

	@traits.on_trait_change('filename')
	def load_file(self):
		if self.filename:
			try:
				self.data = datasources.Camera(self.filename)
			except:
				support.Message.file_open_failed(self.filename, parent=self.context.uiparent)
				self.filename = ''
				return
			self.channel_names = list(self.data.iterchannelnames())
			self.framecount = self.data.getframecount() - 1
			self.lastframe = min(self.framecount, 25)
			self.settings_changed()

	def _xaxis_type_changed(self):
		with self.context.canvas.hold():
			self._firstframe_changed() # this makes sure that firstframe <= lastframe and calls settings_changed()
			if self.prev_xaxis_type is None or (
					self.prev_xaxis_type != self.xaxis_type
					and 'time' in (self.prev_xaxis_type, self.xaxis_type)
				):
				self.rebuild_figure()
			self.prev_xaxis_type = self.xaxis_type

	def _firstframe_changed(self):
		if (self.fft and self.firstframe != self.lastframe) or self.firstframe > self.lastframe:
			self.lastframe = self.firstframe
			# settings_changed() will be triggered because lastframe changes
		else:
			self.settings_changed()

	@traits.on_trait_change('averaging, lastframe, stepframe, selected_primary_channels, selected_secondary_channels')
	def settings_changed(self):
		if not self.data:
			self.plot.fft = self.fft
			self.rebuild()
			return
		# FIXME: implement a smarter first/last frame selection, don't redraw everything
		if self.fft:
			data = self.data.selectframes(self.firstframe, self.firstframe, 1)
		else:
			data = self.data.selectframes(self.firstframe, self.lastframe, self.stepframe)
		self.data.averaging = self.averaging
		self.plot.fft = self.data.fft = self.fft

		if self.fourierfilter:
			self.data.fourierfilter = self.fourierfilter.get_callable('f')
			self.data.fourierwindow = self.fourierfilter.get_window_tuple()
		else:
			self.data.fourierfilter = False

		y1 = data.selectchannels(lambda chan: chan.id in self.selected_primary_channels)
		y2 = data.selectchannels(lambda chan: chan.id in self.selected_secondary_channels)
		if self.xaxis_type in self.channel_names:
			self.plot.set_data(y1, y2, data.selectchannels(lambda chan: chan.id == self.xaxis_type))
		else:
			self.plot.set_data(y1, y2)
		self.rebuild()

	traits_view = support.PanelView(
		traitsui.Group(
			traitsui.Item('visible'),
			traitsui.Item('filename', editor=support.FileEditor(filter=['Camera RAW files (*.raw)', '*.raw', 'All files', '*'], entries=0)),
			traitsui.Item('firstframe', label='First frame', editor=support.RangeEditor(low=0, high_name='framecount', mode='spinner')),
			traitsui.Item('lastframe', label='Last frame', editor=support.RangeEditor(low=0, high_name='framecount', mode='spinner'), enabled_when='not_fft'),
			traitsui.Item('stepframe', label='Key frame mode', enabled_when='not_fft', editor=support.RangeEditor()),
			traitsui.Item('direction', editor=traitsui.EnumEditor(values=support.EnumMapping([(1, 'L2R'), (2, 'R2L'), (3, 'both')]))),
			traitsui.Item('averaging', tooltip='Per-line averaging', enabled_when='not_fft'),
			traitsui.Item('edit_fourierfilter', show_label=False, editor=traitsui.ButtonEditor(label='1D fourier options...')),
			traitsui.Item('legend'),
			traitsui.Item('size'),
			show_border=True,
			label='General',
		),
		traitsui.Group(
			traitsui.Item('xaxis_type', label='Data', editor=traitsui.EnumEditor(name='xaxis_type_options')),
			traitsui.Item('xlimits', style='custom', label='Limits', enabled_when='independent_x'),
			show_border=True,
			label='X-axis',
		),
		traitsui.Include('yaxis_group'),
		traitsui.Include('relativistic_group'),
	)
