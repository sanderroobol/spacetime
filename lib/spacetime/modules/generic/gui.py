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

from enthought.traits.api import *
from enthought.traits.ui.api import *
from enthought.traits.ui.table_column import ObjectColumn
from enthought.traits.ui.extras.checkbox_column import CheckboxColumn

import os
import wx

import string
import matplotlib.cm

import logging
logger = logging.getLogger(__name__)

from ... import gui

from . import subplots
from . import datasources


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
	context = Instance(HasTraits)
	_modified = Bool(False)

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
	filename = File
	reload = Button
	simultaneity_offset = Float(0.)
	time_dilation_factor = Float(1.)

	plot = Instance(subplots.Subplot)
	visible = Bool(True)
	size = Range(1, 10)
	number = 0

	# Magic attribute with "class level" "extension inheritance". Does this make any sense?
	# It means that when you derive a class from this class, you only have to
	# specify the attributes that are "new" in the derived class, any
	# attributed listed in one of the parent classes will be added
	# automatically.
	# Anyway, this is possible thanks to the TraitsSavedMeta metaclass.
	traits_saved = 'visible', 'filename', 'simultaneity_offset', 'time_dilation_factor', 'size'
	# traits_not_saved = ... can be used to specify parameters that should not be copied in a derived classes

	relativistic_group = Group(
		Item('simultaneity_offset', label='Simultaneity offset (s)', editor=gui.support.FloatEditor()),
		Item('time_dilation_factor', editor=RangeEditor(low=.999, high=1.001)),
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

	@on_trait_change('simultaneity_offset, time_dilation_factor')
	def relativistics_changed(self):
		self.plot.adjust_time(self.simultaneity_offset, self.time_dilation_factor)
		self.rebuild()

	def reset_autoscale(self):
		pass

	def _size_changed(self):
		self.plot.size = self.size
		self.rebuild_figure()


def TimeTrendChannelListEditor():
	return TableEditor(
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
	return TableEditor(
		sortable = True,
		configurable = False,
		auto_size = False,
		columns = [
			CheckboxColumn(name='checked', label='L', width=0.1),
			CheckboxColumn(name='checked2', label='R', width=0.1),
			ObjectColumn(name='label', label='Name', editable=False, width=0.5, horizontal_alignment='left'),
		],
	)


class TimeTrendChannel(HasTraits):
	id = Str
	label = Str
	checked = Bool(False)
	checked2 = Bool(False)


class TimeTrendGUI(SubplotGUI):
	plotfactory = subplots.MultiTrend
	legend = Enum('auto', 'off', 'upper right', 'upper left', 'lower left', 'lower right', 'center left', 'center right', 'lower center', 'upper center', 'center')
	ylimits = Instance(gui.support.LogAxisLimits, args=())
	yauto = DelegatesTo('ylimits', 'auto')
	ymin = DelegatesTo('ylimits', 'min')
	ymax = DelegatesTo('ylimits', 'max')
	ylog = DelegatesTo('ylimits', 'log')
	channel_names = List(Str)
	channelobjs = Property(List(TimeTrendChannel), depends_on='channel_names')
	selected_primary_channels = Property(depends_on='channelobjs.checked')
	data = Instance(datasources.DataSource)

	traits_saved = 'legend', 'yauto', 'ymin', 'ymax', 'ylog', 'selected_primary_channels'

	def _plot_default(self):
		plot = self.plotfactory()
		plot.set_ylim_callback(self.ylim_callback)
		return plot

	def filter_channels(self, channels):
		return channels

	@cached_property
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

	@on_trait_change('filename, reload')
	def load_file(self):
		if self.filename:
			try:
				self.data = self.datafactory(self.filename)
			except:
				gui.support.Message.file_open_failed(self.filename, parent=self.context.uiparent)
				self.filename = ''
				return False
			if self.channel_names:
				uncheck = False
			else:
				uncheck = True
			self.channel_names = list(self.data.iterchannelnames())
			if uncheck:
				self.channelobjs[0].checked = False # the TableEditor checks the first checkbox when it's initialized...
			self.settings_changed()
			return True
		return False

	@on_trait_change('selected_primary_channels')
	def settings_changed(self):
		if not self.data:
			return
		self.plot.set_data(self.data.selectchannels(lambda chan: chan.id in self.selected_primary_channels))
		self.rebuild()

	@on_trait_change('ymin, ymax, yauto')
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

	def get_general_view_group(self):
		return Group(
			Item('visible'),
			Item('filename', editor=gui.support.FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
			Item('reload', show_label=False),
			Item('legend'),
			Item('size'),
			show_border=True,
			label='General',
		)

	yaxis_group = Group(
		Item('channelobjs', label='Channels', editor=TimeTrendChannelListEditor()),
		Item('ylimits', style='custom', label='Limits'),
		show_border=True,
		label='Y-axis'
	)

	def traits_view(self):
		return gui.support.PanelView(
			self.get_general_view_group(),
			Include('yaxis_group'),
			Include('relativistic_group'),
		)


class DoubleTimeTrendGUI(TimeTrendGUI):
	plotfactory = subplots.DoubleMultiTrend
	selected_secondary_channels = Property(depends_on='channelobjs.checked2')

	ylimits2 = Instance(gui.support.LogAxisLimits, args=())
	yauto2 = DelegatesTo('ylimits2', 'auto')
	ymin2 = DelegatesTo('ylimits2', 'min')
	ymax2 = DelegatesTo('ylimits2', 'max')
	ylog2 = DelegatesTo('ylimits2', 'log')

	traits_saved = 'selected_secondary_channels', 'yauto2', 'ymin2', 'ymax2', 'ylog2'

	def _plot_default(self):
		plot = self.plotfactory()
		plot.set_ylim_callback(self.ylim_callback)
		return plot

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

	@on_trait_change('ymin2, ymax2, yauto2')
	@gui.figure.CallbackLoopManager.decorator('ylimits2')
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

	@on_trait_change('selected_primary_channels, selected_secondary_channels')
	def settings_changed(self):
		if not self.data:
			return
		self.plot.set_data(
			self.data.selectchannels(lambda chan: chan.id in self.selected_primary_channels),
			self.data.selectchannels(lambda chan: chan.id in self.selected_secondary_channels),
		)
		self.rebuild()

	yaxis_group = Group(
		Item('channelobjs', label='Channels', editor=DoubleTimeTrendChannelListEditor()),
		Item('ylimits', style='custom', label='Left limits'),
		Item('ylimits2', style='custom', label='Right limits'),
		show_border=True,
		label='Y-axes'
	)

	def traits_view(self):
		return gui.support.PanelView(
			self.get_general_view_group(),
			Include('yaxis_group'),
			Include('relativistic_group'),
		)


class XlimitsGUI(HasTraits):
	xlimits = Instance(gui.support.LogAxisLimits, args=())
	xauto = DelegatesTo('xlimits', 'auto')
	xmin = DelegatesTo('xlimits', 'min')
	xmax = DelegatesTo('xlimits', 'max')
	xlog = DelegatesTo('xlimits', 'log')

	traits_saved = 'xauto', 'xmin', 'xmax', 'xlog'

	@on_trait_change('xmin, xmax, xauto')
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


class CSVGUI(DoubleTimeTrendGUI):
	id = 'csv'
	label = 'Plain text (experimental)'
	desc = 'Flexible reader for CSV / tab separated / ASCII files.\n\nAccepts times as unix timestamp (seconds sinds 1970-1-1 00:00:00 UTC), Labview timestamp (seconds since since 1904-1-1 00:00:00 UTC), Matplotlib timestamps (days since 0001-01-01 UTC, plus 1) or arbitrary strings (strptime format).'

	datafactory = datasources.CSV
	filter = 'ASCII text files (*.txt, *.csv, *.tab)', '*.txt;*.csv;*.tab',

	time_type = Enum('unix', 'labview', 'matplotlib', 'custom')
	time_custom = Property(depends_on='time_type')
	time_format = Str('%Y-%m-%d %H:%M:%S')
	time_column = Str('auto')
	time_column_options = Property(depends_on='channel_names')

	traits_saved = 'time_type', 'time_format', 'time_column'

	def _get_time_custom(self):
		return self.time_type == 'custom'

	def filter_channels(self, channels):
		if self.time_column == 'auto':
			if self.data:
				check = set(self.data.time_channel_headers)
			else:
				check = set()
		else:
			check = set([self.time_column])
		return (chan for chan in channels if chan.id not in check)

	@cached_property
	def _get_time_column_options(self):
		return gui.support.EnumMapping([('auto', '(auto)')] + self.channel_names)

	def _time_column_changed(self):
		self.channel_names = list(self.channel_names) # trigger rebuild of traits depending on channel_names

	@on_trait_change('selected_primary_channels, selected_secondary_channels, time_type, time_format, time_column')
	def settings_changed(self):
		if not self.data:
			return
		if self.time_column == 'auto':
			self.data.time_column = 'auto'
		else:
			self.data.time_column = self.channel_names.index(self.time_column)
		if self.time_custom:
			self.data.time_type = 'strptime'
			self.data.time_strptime = self.time_format
		else:
			self.data.time_type = self.time_type
		super(CSVGUI, self).settings_changed()

	def traits_view(self):
		return gui.support.PanelView(
			self.get_general_view_group(),
			Group(
				Item('time_type', label='Type'),
				Item('time_format', label='Format string', enabled_when='time_custom'),
				Item('time_column', label='Column', editor=EnumEditor(name='time_column_options')),
				label='Time data',
				show_border=True,
			),
			Include('yaxis_group'),
			Include('relativistic_group'),
		)


class Time2DGUI(TimeTrendGUI):
	colormap = Enum(sorted((m for m in matplotlib.cm.datad if not m.endswith("_r")), key=string.lower))
	interpolation = Enum('nearest', 'bilinear', 'bicubic')

	climits = Instance(gui.support.LogAxisLimits, args=())
	cauto = DelegatesTo('climits', 'auto')
	cmin = DelegatesTo('climits', 'min')
	cmax = DelegatesTo('climits', 'max')
	clog = DelegatesTo('climits', 'log')

	traits_saved = 'colormap', 'interpolation', 'cauto', 'cmin', 'cmax', 'clog'

	plotfactory = subplots.Time2D

	def __init__(self, *args, **kwargs):
		self.trait_set(trait_change_notify=False, colormap='spectral')
		super(Time2DGUI, self).__init__(*args, **kwargs)

	def _colormap_changed(self):
		self.plot.set_colormap(self.colormap)
		self.redraw()

	def _interpolation_changed(self):
		self.plot.set_interpolation(self.interpolation)
		self.redraw()

	@on_trait_change('cmin, cmax, cauto, clog')
	def clim_changed(self):
		self.plot.set_clim(self.climits.min, self.climits.max, self.climits.auto, self.climits.log)
		self.rebuild()

	@on_trait_change('filename, reload')
	def load_file(self):
		super(Time2DGUI, self).load_file()
		self.plot.set_data(self.data)
		self.rebuild()

	def settings_changed(self):
		pass

	def traits_view(self):
		return gui.support.PanelView(
			Group(
				Item('visible'),
				Item('filename', editor=gui.support.FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
				Item('reload', show_label=False),
				show_border=True,
				label='General',
			),
			Group(
				Item('size'),
				Item('colormap'),
				Item('interpolation', editor=EnumEditor(values=gui.support.EnumMapping([('nearest', 'none'), 'bilinear', 'bicubic']))),
				show_border=True,
				label='Display',
			),
			Group(
				Item('ylimits', style='custom', label='Y scale'),
				Item('climits', style='custom', label='Color scale'),
				show_border=True,
				label='Limits',
			),
			# FIXME Include('relativistic_group'),
		)


class ImageGUI(SubplotGUI): # FIXME: this should be the base class for the Camera stuff too
	pass


class RGBImageGUI(ImageGUI):
	id = 'rgbimage'
	label = 'Image'
	desc = 'Any bitmap image (PNG, JPEG, TIFF, BMP, ...)'
	filenames = List(Str)
	filename_count = Property(Int, depends_on='filenames')
	short_filenames = Property(List(Str), depends_on='filenames')
	select_files = Button
	selected_filename = Str
	selected_index = Int

	traits_saved = 'filenames', 'selected_index'
	traits_not_saved = 'filename',

	plotfactory = subplots.Image	
	datafactory = datasources.RGBImage

	def _plot_default(self):
		plot = self.plotfactory()
		plot.mode = 'single frame'
		return plot

	@cached_property
	def _get_short_filenames(self):
		return [os.path.basename(i) for i in self.filenames]

	def _get_filename_count(self):
		return len(self.filenames)

	def _selected_filename_changed(self):
		self.selected_index = self.short_filenames.index(self.selected_filename)

	@on_trait_change('reload, selected_index')
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
			Group(
				Item('visible'),
				Item('select_files', show_label=False),
				Item('selected_filename', label='File', editor=EnumEditor(name='short_filenames')),
				Item('selected_index', label='Number', editor=RangeEditor(low=0, high_name='filename_count', mode='spinner')),
				Item('reload', show_label=False),
				show_border=True,
				label='General',
			),
		)
