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
from enthought.traits.ui.table_column import ObjectColumn
from enthought.traits.ui.extras.checkbox_column import CheckboxColumn

import os
import wx

import string
import matplotlib.cm

import logging
logger = logging.getLogger(__name__)

from ... import gui

from . import subplots, datasources, datasinks


class Tab(traits.HasTraits):
	pass


class TraitsSavedMeta(traits.HasTraits.__metaclass__):
	def __new__(mcs, name, bases, dict):
		if 'traits_saved' not in dict:
			dict['traits_saved'] = ()
		for base in bases:
			if 'traits_saved' in base.__dict__:
				dict['traits_saved'] = tuple(i for i in base.__dict__['traits_saved'] if 'traits_not_saved' not in dict or i not in dict['traits_not_saved']) + dict['traits_saved']
		return traits.HasTraits.__metaclass__.__new__(mcs, name, bases, dict)


class SerializableTab(Tab):
	__metaclass__ = TraitsSavedMeta
	context = traits.Instance(traits.HasTraits)
	_modified = traits.Bool(False)

	def __init__(self, *args, **kwargs):
		super(SerializableTab, self).__init__(*args, **kwargs)
		self.on_trait_change(self.set_modified, list(self.traits_saved))

	def _delayed_from_serialized(self, src):
		with self.context.canvas.hold():
			# trait_set has to be called separately for each trait to respect the ordering of traits_saved
			for id in self.traits_saved:
				if id in src:
					try: 
						self.trait_set(**dict(((id, src[id]),)))
					except:
						gui.support.Message.exception(title='Warning', message='Warning: incompatible project file', desc='Could not restore property "{0}" for graph "{1}". This graph might not be completely functional.'.format(id, self.label))
					del src[id]
				# else: silently ignore
			if src: # complain about unknown properties
				gui.support.Message.show(
					title='Warning', message='Warning: incompatible project file',
					desc='Ignoring unknown properties "{0}" for graph "{1}". This graph might not be completely functional.'.format('", "'.join(src.keys()), self.label)
				)
  

	def from_serialized(self, src):
		if hasattr(self, 'traits_saved'):
			wx.CallAfter(lambda: self._delayed_from_serialized(src))

	def get_serialized(self):
		if hasattr(self, 'traits_saved'):
			return dict((id, getattr(self, id)) for id in self.traits_saved)
		else:
			return dict()

	def clear_modified(self):
		self._modified = False

	def set_modified(self):
		self._modified = True


class SubplotGUI(SerializableTab):
	# required attributes: id, label
	desc = '' # not required
	filename = traits.File
	reload = traits.Button
	simultaneity_offset = traits.Float(0.)
	time_dilation_factor = traits.Float(1.)

	plot = traits.Instance(subplots.Subplot)
	visible = traits.Bool(True)
	size = traits.Range(1, 10)
	number = 0

	# Magic attribute with "class level" "extension inheritance". Does this make any sense?
	# It means that when you derive a class from this class, you only have to
	# specify the attributes that are "new" in the derived class, any
	# attributed listed in one of the parent classes will be added
	# automatically.
	# Anyway, this is possible thanks to the TraitsSavedMeta metaclass.
	traits_saved = 'visible', 'filename', 'simultaneity_offset', 'time_dilation_factor', 'size'
	# traits_not_saved = ... can be used to specify parameters that should not be copied in a derived classes

	relativistic_group = traitsui.Group(
		traitsui.Item('simultaneity_offset', label='Simultaneity offset (s)', editor=gui.support.FloatEditor()),
		traitsui.Item('time_dilation_factor', editor=traitsui.RangeEditor(low=.999, high=1.001)),
		show_border=True,
		label='Relativistic corrections',
	)

	def __init__(self, *args, **kwargs):
		super(SubplotGUI, self).__init__(*args, **kwargs)
		self.__class__.number += 1
		if self.__class__.number != 1:
			self.label = '{0} {1}'.format(self.label, self.__class__.number)

	def rebuild_figure(self):
		self.context.canvas.rebuild()

	def rebuild(self):
		def callback():
			self.plot.clear()
			self.plot.draw()
			with self.context.callbacks.general_blockade():
				self.context.plot.autoscale(self.plot)
		self.context.canvas.rebuild_subgraph(callback)

	def redraw(self):
		self.context.canvas.redraw()

	def _visible_changed(self):
		self.rebuild_figure()

	@traits.on_trait_change('simultaneity_offset, time_dilation_factor')
	def relativistics_changed(self):
		self.plot.adjust_time(self.simultaneity_offset, self.time_dilation_factor)
		self.rebuild()

	def reset_autoscale(self):
		pass

	def _size_changed(self):
		self.plot.size = self.size
		self.rebuild_figure()


def TimeTrendChannelListEditor():
	return traitsui.TableEditor(
		sortable = True,
		configurable = False,
		show_column_labels = False,
		auto_size = False,
		columns = [
			CheckboxColumn(name='checked', width=0.1),
			ObjectColumn(name='label', editable=False, width=0.5, horizontal_alignment='left'),
		],
	)


def DoubleTimeTrendChannelListEditor():
	return traitsui.TableEditor(
		sortable = True,
		configurable = False,
		auto_size = False,
		columns = [
			CheckboxColumn(name='checked', label='L', width=0.1),
			CheckboxColumn(name='checked2', label='R', width=0.1),
			ObjectColumn(name='label', label='Name', editable=False, width=0.5, horizontal_alignment='left'),
		],
	)


class TimeTrendChannel(traits.HasTraits):
	id = traits.Str
	label = traits.Str
	checked = traits.Bool(False)
	checked2 = traits.Bool(False)


class TimeTrendGUI(SubplotGUI):
	plotfactory = subplots.MultiTrend
	sinkfactory = datasinks.MultiTrendTextSink
	legend = traits.Enum('auto', 'off', 'upper right', 'upper left', 'lower left', 'lower right', 'center left', 'center right', 'lower center', 'upper center', 'center')
	ylimits = traits.Instance(gui.support.LogAxisLimits, args=())
	yauto = traits.DelegatesTo('ylimits', 'auto')
	ymin = traits.DelegatesTo('ylimits', 'min')
	ymax = traits.DelegatesTo('ylimits', 'max')
	ylog = traits.DelegatesTo('ylimits', 'log')
	channel_names = traits.List(traits.Str)
	channelobjs = traits.Property(traits.List(TimeTrendChannel), depends_on='channel_names')
	selected_primary_channels = traits.Property(depends_on='channelobjs.checked')
	data = traits.Instance(datasources.DataSource)

	traits_saved = 'legend', 'yauto', 'ymin', 'ymax', 'ylog', 'selected_primary_channels'

	def _plot_default(self):
		plot = self.plotfactory()
		plot.set_ylim_callback(self.ylim_callback)
		return plot

	def filter_channels(self, channels):
		return channels

	@traits.cached_property
	def _get_channelobjs(self):
		return list(self.filter_channels(TimeTrendChannel(id=name, label=name) for name in self.channel_names))

	def _get_selected_primary_channels(self):
		return [chan.id for chan in self.channelobjs if chan.checked]

	def _set_selected_primary_channels(self, value):
		value = set(value) # to speed up membership tests
		for chan in self.channelobjs:
			if chan.id in value:
				chan.checked = True
			else:
				chan.checked = False

	def ylim_callback(self, ax):
		with self.context.callbacks.avoid(self.ylimits):
			self.ymin, self.ymax = ax.get_ylim()
		if not self.context.callbacks.is_avoiding(self.ylimits):
			self.yauto = False
		logger.info('%s.ylim_callback: %s', self.__class__.__name__, self.ylimits)

	def update_channel_names(self):
		if self.channel_names:
			uncheck = False
		else:
			uncheck = True
		self.channel_names = list(self.data.iterchannelnames())
		if uncheck:
			self.channelobjs[0].checked = False # the TableEditor checks the first checkbox when it's initialized...

	@traits.on_trait_change('filename, reload')
	def load_file(self):
		if self.filename:
			try:
				self.data = self.datafactory(self.filename)
			except:
				gui.support.Message.file_open_failed(self.filename, parent=self.context.uiparent)
				self.filename = ''
				return False
			self.update_channel_names()
			self.settings_changed()
			return True
		return False

	@traits.on_trait_change('selected_primary_channels')
	def settings_changed(self):
		if not self.data:
			return
		self.plot.set_data(self.data.selectchannels(lambda chan: chan.id in self.selected_primary_channels))
		self.rebuild()

	@traits.on_trait_change('ymin, ymax, yauto')
	@gui.figure.CallbackLoopManager.decorator('ylimits')
	def ylim_changed(self):
		logger.info('%s.ylim_changed: %s', self.__class__.__name__, self.ylimits)
		self.ymin, self.ymax = self.plot.set_ylim(self.ylimits.min, self.ylimits.max, self.ylimits.auto)
		self.redraw()

	@gui.figure.CallbackLoopManager.decorator('ylimits')
	def _ylog_changed(self):
		self.plot.set_ylog(self.ylog)
		self.redraw()

	def reset_autoscale(self):
		super(TimeTrendGUI, self).reset_autoscale()
		self.yauto = True

	def _legend_changed(self):
		if self.legend == 'off':
			legend = False
		elif self.legend == 'auto':
			legend = 'best'
		else:
			legend = self.legend
		self.plot.set_legend(legend)
		self.redraw()

	def export(self, destdir):
		return self.sinkfactory().save(self.plot, destdir, self.label)

	def get_general_view_group(self):
		return traitsui.Group(
			traitsui.Item('visible'),
			traitsui.Item('filename', editor=gui.support.FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
			traitsui.Item('reload', show_label=False),
			traitsui.Item('legend'),
			traitsui.Item('size'),
			show_border=True,
			label='General',
		)

	yaxis_group = traitsui.Group(
		traitsui.Item('channelobjs', label='Channels', editor=TimeTrendChannelListEditor()),
		traitsui.Item('ylimits', style='custom', label='Limits'),
		show_border=True,
		label='Y-axis'
	)

	def traits_view(self):
		return gui.support.PanelView(
			self.get_general_view_group(),
			traitsui.Include('yaxis_group'),
			traitsui.Include('relativistic_group'),
		)


class DoubleTimeTrendGUI(TimeTrendGUI):
	plotfactory = subplots.DoubleMultiTrend
	selected_secondary_channels = traits.Property(depends_on='channelobjs.checked2')

	ylimits2 = traits.Instance(gui.support.LogAxisLimits, args=())
	yauto2 = traits.DelegatesTo('ylimits2', 'auto')
	ymin2 = traits.DelegatesTo('ylimits2', 'min')
	ymax2 = traits.DelegatesTo('ylimits2', 'max')
	ylog2 = traits.DelegatesTo('ylimits2', 'log')

	traits_saved = 'selected_secondary_channels', 'yauto2', 'ymin2', 'ymax2', 'ylog2'

	def _get_selected_secondary_channels(self):
		return [chan.id for chan in self.channelobjs if chan.checked2]

	def _set_selected_secondary_channels(self, value):
		value = set(value) # to speed up membership tests
		for chan in self.channelobjs:
			if chan.id in value:
				chan.checked2 = True
			else:
				chan.checked2 = False

	def ylim_callback(self, ax):
		if ax is self.plot.axes:
			with self.context.callbacks.avoid(self.ylimits):
				self.ymin, self.ymax = ax.get_ylim()
			if not self.context.callbacks.is_avoiding(self.ylimits):
				self.yauto = False
			logger.info('%s.ylim_callback primary: %s', self.__class__.__name__, self.ylimits)
		elif ax is self.plot.secondaryaxes:
			with self.context.callbacks.avoid(self.ylimits2):
				self.ymin2, self.ymax2 = ax.get_ylim()
			if not self.context.callbacks.is_avoiding(self.ylimits2):
				self.yauto2 = False
			logger.info('%s.ylim_callback secondary: %s', self.__class__.__name__, self.ylimits2)

	# extend the callback protection to include ylimits2 as well
	@traits.on_trait_change('ymin, ymax, yauto')
	@gui.figure.CallbackLoopManager.decorator('ylimits', 'ylimits2')
	def ylim_changed(self):
		# we cannot call ylim_changed directly, because it is protected by the CallbackloopManager
		super(DoubleTimeTrendGUI, self).ylim_changed.original(self)

	@traits.on_trait_change('ymin2, ymax2, yauto2')
	@gui.figure.CallbackLoopManager.decorator('ylimits', 'ylimits2')
	def ylim2_changed(self):
		logger.info('%s.ylim2_changed: %s', self.__class__.__name__, self.ylimits2)
		self.ymin2, self.ymax2 = self.plot.set_ylim2(self.ylimits2.min, self.ylimits2.max, self.ylimits2.auto)
		self.redraw()

	@gui.figure.CallbackLoopManager.decorator('ylimits2')
	def _ylog2_changed(self):
		self.plot.set_ylog2(self.ylog2)
		self.redraw()

	def reset_autoscale(self):
		super(DoubleTimeTrendGUI, self).reset_autoscale()
		self.yauto2 = True

	@traits.on_trait_change('selected_primary_channels, selected_secondary_channels')
	def settings_changed(self):
		if not self.data:
			return
		self.plot.set_data(
			self.data.selectchannels(lambda chan: chan.id in self.selected_primary_channels),
			self.data.selectchannels(lambda chan: chan.id in self.selected_secondary_channels),
		)
		self.rebuild()

	yaxis_group = traitsui.Group(
		traitsui.Item('channelobjs', label='Channels', editor=DoubleTimeTrendChannelListEditor()),
		traitsui.Item('ylimits', style='custom', label='Left limits'),
		traitsui.Item('ylimits2', style='custom', label='Right limits'),
		show_border=True,
		label='Y-axes'
	)

	def traits_view(self):
		return gui.support.PanelView(
			self.get_general_view_group(),
			traitsui.Include('yaxis_group'),
			traitsui.Include('relativistic_group'),
		)


class XlimitsGUI(traits.HasTraits):
	xlimits = traits.Instance(gui.support.LogAxisLimits, args=())
	xauto = traits.DelegatesTo('xlimits', 'auto')
	xmin = traits.DelegatesTo('xlimits', 'min')
	xmax = traits.DelegatesTo('xlimits', 'max')
	xlog = traits.DelegatesTo('xlimits', 'log')

	traits_saved = 'xauto', 'xmin', 'xmax', 'xlog'

	@traits.on_trait_change('xmin, xmax, xauto')
	@gui.figure.CallbackLoopManager.decorator('xlimits')
	def xlim_changed(self):
		logger.info('%s.xlim_changed: %s', self.__class__.__name__, self.xlimits)
		self.xmin, self.xmax = self.plot.set_xlim(self.xlimits.min, self.xlimits.max, self.xlimits.auto)
		self.redraw()

	@gui.figure.CallbackLoopManager.decorator('xlimits')
	def _xlog_changed(self):
		self.plot.set_xlog(self.xlog)
		self.redraw()

	def xlim_callback(self, ax):
		with self.context.callbacks.avoid(self.xlimits):
			self.xmin, self.xmax = ax.get_xlim()
		if not self.context.callbacks.is_avoiding(self.xlimits):
			self.xauto = False
		logger.info('%s.xlim_callback: %s', self.__class__.__name__, self.xlimits)

	def reset_autoscale(self):
		self.xauto = True


class CSVConfigurationHandler(traitsui.Handler):
	def close(self, info, is_ok=None):
		if not is_ok:
			return True

		obj = info.ui.context['object']

		data = obj.datafactory()
		data.set_config(filename=obj.filename, delimiter=obj.csv_delimiter, skip_lines=obj.csv_skip_lines, time_type=obj.time_type, time_strptime=obj.time_format, time_column=obj.time_column)
		try:
			data.load(probe=True)
		except:
			gui.support.Message.exception('The file does not load correctly.', desc='Check the output below and resolve the problem.', title='Loading failed.', parent=info.ui.control)
			return False
		else:
			data.load()
			obj.data = data
			obj.update_channel_names()
			return True
			

class CSVGUI(DoubleTimeTrendGUI):
	id = 'csv'
	label = 'Plain text (experimental)'
	desc = 'Flexible reader for CSV / tab separated / ASCII files.\n\nAccepts times as unix timestamp (seconds sinds 1970-1-1 00:00:00 UTC), Labview timestamp (seconds since since 1904-1-1 00:00:00 UTC), Matplotlib timestamps (days since 0001-01-01 UTC, plus 1) or arbitrary strings (strptime format).'

	datafactory = datasources.CSV
	filter = 'ASCII text files (*.txt, *.csv, *.tab)', '*.txt;*.csv;*.tab',

	csv_delimiter = traits.Enum('\t', ',', ';');
	csv_skip_lines = traits.Int(0)

	time_type = traits.Enum('unix', 'labview', 'matplotlib', 'strptime')
	time_custom = traits.Property(depends_on='time_type')
	time_format = traits.Str('%Y-%m-%d %H:%M:%S')
	time_column = traits.Str('auto')
	time_column_options = traits.Property(depends_on='channel_names')

	edit_configuration = traits.Button()

	traits_saved = 'time_type', 'time_format', 'time_column', 'live_phase'

	def _get_time_custom(self):
		return self.time_type == 'strptime'

	def filter_channels(self, channels):
		if self.time_column == 'auto':
			if self.data:
				check = set(self.data.time_channel_headers)
			else:
				check = set()
		else:
			check = set([self.time_column])
		return (chan for chan in channels if chan.id not in check)

	@traits.cached_property
	def _get_time_column_options(self):
		return gui.support.EnumMapping([('auto', '(auto)')] + self.channel_names)

	def _time_column_changed(self):
		self.channel_names = list(self.channel_names) # trigger rebuild of traits depending on channel_names

	# adjust the inherited on_trait_change(filename, reload) event handler; don't respond to filename changes
	@traits.on_trait_change('reload')
	def load_file(self):
		self.data.load()
		self.update_channel_names()
		self.settings_changed()

	def traits_view(self):
		return gui.support.PanelView(
			traitsui.Group(
				traitsui.Item('visible'),
				traitsui.Item('edit_configuration', show_label=False, editor=traitsui.ButtonEditor(label='Select file...')),
				traitsui.Item('reload', show_label=False),
				label='General',
				show_border=True,
			),
			traitsui.Include('yaxis_group'),
			traitsui.Include('relativistic_group'),
		)

	def _edit_configuration_fired(self):
		if self.edit_traits(view='configuration_view').result:
			self.settings_changed()

	def configuration_view(self):
		return traitsui.View(
			traitsui.Group(
				traitsui.Group(
					traitsui.Item('filename', editor=gui.support.FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
					traitsui.Item('csv_delimiter', label='Delimiter', editor=traitsui.EnumEditor(values=gui.support.EnumMapping([('\t', 'tab'), ',', ';']))),
					traitsui.Item('csv_skip_lines', label='Skip header lines'), 
					label='Data',
					show_border=True,
				),
				traitsui.Group(
					traitsui.Item('time_type', label='Type', editor=traitsui.EnumEditor(values=gui.support.EnumMapping((('unix', 'Unix timestamp (seconds since 1-1-1970 00:00:00 UTC)'), ('matplotlib', 'Matplotlib (days since 1-1-0001 00:00:00 UTC, plus 1)'), ('labview', 'LabVIEW (seconds since 1-1-1904 00:00:00 UTC'), ('strptime', 'Custom (strptime format)'))))),
					traitsui.Item('time_format', label='Format string', enabled_when='time_custom'),
					traitsui.Item('time_column', label='Column', editor=traitsui.EnumEditor(name='time_column_options')),
					label='Time data',
					show_border=True,
				),
				layout='normal',
			),
			handler=CSVConfigurationHandler(),
			buttons=traitsui.OKCancelButtons,
			width=500,
			kind='livemodal',
		)



class FalseColorMap(traits.HasTraits):
	colormap = traits.Enum(sorted((m for m in matplotlib.cm.datad if not m.endswith("_r")), key=string.lower))
	default_colormap = 'spectral'
	interpolation = traits.Enum('nearest', 'bilinear', 'bicubic')

	climits = traits.Instance(gui.support.LogAxisLimits, args=())
	cauto = traits.DelegatesTo('climits', 'auto')
	cmin = traits.DelegatesTo('climits', 'min')
	cmax = traits.DelegatesTo('climits', 'max')
	clog = traits.DelegatesTo('climits', 'log')

	traits_saved = 'colormap', 'interpolation', 'cauto', 'cmin', 'cmax', 'clog'

	def __init__(self, *args, **kwargs):
		self.trait_set(trait_change_notify=False, colormap=self.default_colormap)
		super(FalseColorMap, self).__init__(*args, **kwargs)

	def _colormap_changed(self):
		self.plot.set_colormap(self.colormap)
		self.redraw()

	def _interpolation_changed(self):
		self.plot.set_interpolation(self.interpolation)
		self.redraw()

	def clim_callback(self, cmin, cmax):
		self.cmin = cmin
		self.cmax = cmax
		logger.info('%s.clim_callback: %s', self.__class__.__name__, self.climits)

	@traits.on_trait_change('cmin, cmax, cauto, clog')
	@gui.figure.CallbackLoopManager.decorator('climits')
	def clim_changed(self):
		logger.info('%s.clim_changed: %s', self.__class__.__name__, self.climits)
		self.plot.set_clim(self.climits.min, self.climits.max, self.climits.auto, self.climits.log)
		self.rebuild()

	false_color_group = traitsui.Group(
				traitsui.Item('size'),
				traitsui.Item('colormap'),
				traitsui.Item('interpolation', editor=traitsui.EnumEditor(values=gui.support.EnumMapping([('nearest', 'none'), 'bilinear', 'bicubic']))),
				traitsui.Item('climits', style='custom', label='Color scale'),
				show_border=True,
				label='Display',
	)


class Time2DGUI(TimeTrendGUI, FalseColorMap):
	plotfactory = subplots.Time2D

	def _plot_default(self):
		plot = self.plotfactory()
		plot.set_ylim_callback(self.ylim_callback)
		plot.set_clim_callback(self.clim_callback)
		return plot

	@traits.on_trait_change('filename, reload')
	def load_file(self):
		super(Time2DGUI, self).load_file()
		self.plot.set_data(self.data)
		self.rebuild()

	def settings_changed(self):
		pass

	def get_general_view_group(self):
		return traitsui.Group(
			traitsui.Item('visible'),
			traitsui.Item('filename', editor=gui.support.FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
			traitsui.Item('reload', show_label=False),
			show_border=True,
			label='General',
		)

	false_color_group = traitsui.Group(
		traitsui.Item('size'),
		traitsui.Item('colormap'),
		traitsui.Item('interpolation', editor=traitsui.EnumEditor(values=gui.support.EnumMapping([('nearest', 'none'), 'bilinear', 'bicubic']))),
		show_border=True,
		label='Display',
	)

	limits_group = traitsui.Group(
		traitsui.Item('ylimits', style='custom', label='Y scale'),
		traitsui.Item('climits', style='custom', label='Color scale'),
		show_border=True,
		label='Limits',
	)

	def traits_view(self):
		return gui.support.PanelView(
			self.get_general_view_group(),
			traitsui.Include('false_color_group'),
			traitsui.Include('limits_group'),
			traitsui.Include('relativistic_group'),
		)


class ImageGUI(SubplotGUI):
	pass


class FalseColorImageGUI(FalseColorMap, ImageGUI):
	def _plot_default(self):
		plot = self.plotfactory()
		plot.set_clim_callback(self.clim_callback)
		plot.set_colormap(self.colormap)
		return plot


class RGBImageGUI(ImageGUI):
	id = 'rgbimage'
	label = 'Image'
	desc = 'Any bitmap image (PNG, JPEG, TIFF, BMP, ...)'
	filenames = traits.List(traits.Str)
	filename_count = traits.Property(traits.Int, depends_on='filenames')
	short_filenames = traits.Property(traits.List(traits.Str), depends_on='filenames')
	select_files = traits.Button
	selected_filename = traits.Str
	selected_index = traits.Int

	traits_saved = 'filenames', 'selected_index'
	traits_not_saved = 'filename',

	plotfactory = subplots.Image	
	datafactory = datasources.RGBImage

	def _plot_default(self):
		plot = self.plotfactory()
		plot.mode = 'single frame'
		return plot

	@traits.cached_property
	def _get_short_filenames(self):
		return [os.path.basename(i) for i in self.filenames]

	def _get_filename_count(self):
		return len(self.filenames)

	def _selected_filename_changed(self):
		self.selected_index = self.short_filenames.index(self.selected_filename)

	@traits.on_trait_change('reload, selected_index')
	def file_changed(self):
		if self.selected_index >= self.filename_count:
			self.selected_index = self.filename_count - 1
			return
		self.selected_filename = self.short_filenames[self.selected_index]
		self.plot.set_data(self.datafactory(self.filenames[self.selected_index]))
		self.rebuild()

	def _filenames_changed(self):
		self.file_changed()

	def _select_files_fired(self):
		dlg = wx.FileDialog(
			self.context.uiparent,
			defaultDir=self.context.prefs.get_path('rgbimage'),
			style=wx.FD_OPEN|wx.FD_MULTIPLE,
			wildcard='All files|*'
		)
		if dlg.ShowModal() != wx.ID_OK:
			return
		self.context.prefs.set_path('rgbimage', dlg.GetDirectory())
		self.filenames = dlg.GetPaths()

	def traits_view(self):
		return gui.support.PanelView(
			traitsui.Group(
				traitsui.Item('visible'),
				traitsui.Item('select_files', show_label=False),
				traitsui.Item('selected_filename', label='File', editor=traitsui.EnumEditor(name='short_filenames')),
				traitsui.Item('selected_index', label='Number', editor=traitsui.RangeEditor(low=0, high_name='filename_count', mode='spinner')),
				traitsui.Item('reload', show_label=False),
				show_border=True,
				label='General',
			),
		)
