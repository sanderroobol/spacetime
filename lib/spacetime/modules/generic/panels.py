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
			for id in src:
				if id in self.traits_saved:
					try: 
						self.trait_set(**dict(((id, src[id]),)))
					except:
						gui.support.Message.exception(title='Warning', message='Warning: incompatible project file', desc='Could not restore property "{0}" for graph "{1}". This graph might not be completely functional.'.format(id, self.label))
				else:
					gui.support.Message.show(title='Warning', message='Warning: incompatible project file', desc='Ignoring unknown property "{0}" for graph "{1}". This graph might not be completely functional.'.format(id, self.label))
  

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


class SubplotPanel(SerializableTab):
	# required attributes: id, label
	desc = '' # not required
	filename = File
	reload = Button
	simultaneity_offset = Float(0.)
	time_dilation_factor = Float(1.)

	plot = Instance(subplots.Subplot)
	visible = Bool(True)
	number = 0

	# Magic attribute with "class level" "extension inheritance". Does this make any sense?
	# It means that when you derive a class from this class, you only have to
	# specify the attributes that are "new" in the derived class, any
	# attributed listed in one of the parent classes will be added
	# automatically.
	# Anyway, this is possible thanks to the TraitsSavedMeta metaclass.
	traits_saved = 'visible', 'filename', 'simultaneity_offset', 'time_dilation_factor'
	# traits_not_saved = ... can be used to specify parameters that should not be copied in a derived classes

	relativistic_group = Group(
		Item('simultaneity_offset', label='Simultaneity offset (s)', editor=gui.support.FloatEditor()),
		Item('time_dilation_factor', editor=RangeEditor(low=.999, high=1.001)),
		show_border=True,
		label='Relativistic corrections',
	)

	def __init__(self, *args, **kwargs):
		super(SubplotPanel, self).__init__(*args, **kwargs)
		self.__class__.number += 1
		if self.__class__.number != 1:
			self.label = '{0} {1}'.format(self.label, self.__class__.number)

	def redraw_figure(self):
		self.context.canvas.redraw_figure()

	def redraw(self):
		self.context.canvas.redraw_subgraph(lambda: (
			self.plot.clear(),
			self.plot.draw(),
			self.context.plot.autoscale(self.plot),
		))

	def update(self):
		self.context.canvas.update_canvas()

	def _visible_changed(self):
		self.redraw_figure()

	@on_trait_change('simultaneity_offset, time_dilation_factor')
	def relativistics_changed(self):
		self.plot.adjust_time(self.simultaneity_offset, self.time_dilation_factor)
		self.redraw()

	def reset_autoscale(self):
		pass


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


class TimeTrendChannel(HasTraits):
	id = Str
	label = Str
	checked = Bool(False)


class TimeTrendPanel(SubplotPanel):
	plotfactory = subplots.MultiTrend
	legend = Enum('auto', 'off', 'upper right', 'upper left', 'lower left', 'lower right', 'center left', 'center right', 'lower center', 'upper center', 'center')
	ylimits = Instance(gui.support.LogAxisLimits, args=())
	yauto = DelegatesTo('ylimits', 'auto')
	ymin = DelegatesTo('ylimits', 'min')
	ymax = DelegatesTo('ylimits', 'max')
	ylog = DelegatesTo('ylimits', 'log')
	channels = List(Str)
	primary_channels = Property(List(TimeTrendChannel), depends_on='channels')
	selected_primary_channels = Property(depends_on='primary_channels.checked')
	data = Instance(datasources.DataSource)

	traits_saved = 'legend', 'yauto', 'ymin', 'ymax', 'ylog', 'selected_primary_channels'

	def _plot_default(self):
		plot = self.plotfactory()
		plot.set_ylim_callback(self.ylim_callback)
		return plot

	def filter_channels(self, channels):
		return channels

	@cached_property
	def _get_primary_channels(self):
		return list(self.filter_channels(TimeTrendChannel(id=name, label=name) for name in self.channels))

	def _get_selected_primary_channels(self):
		return [chan.id for chan in self.primary_channels if chan.checked]

	def _set_selected_primary_channels(self, value):
		value = set(value) # to speed up membership tests
		for chan in self.primary_channels:
			if chan.id in value:
				chan.checked = True
			else:
				chan.checked = False

	@gui.figure.DrawManager.avoid_callback_loop('ylimits')
	def ylim_callback(self, ax):
		self.ymin, self.ymax = ax.get_ylim()
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
				return
			self.channels = list(self.data.iterchannelnames())
			self.settings_changed()

	@on_trait_change('selected_primary_channels')
	def settings_changed(self):
		if not self.data:
			return
		self.plot.set_data(self.data.selectchannels(lambda chan: chan.id in self.selected_primary_channels))
		self.redraw()

	@on_trait_change('ymin, ymax, yauto')
	@gui.figure.DrawManager.avoid_callback_loop('ylimits')
	def ylim_changed(self):
		logger.info('%s.ylim_changed: %s', self.__class__.__name__, self.ylimits)
		self.ymin, self.ymax = self.plot.set_ylim(self.ylimits.min, self.ylimits.max, self.ylimits.auto)
		self.update()

	@gui.figure.DrawManager.avoid_callback_loop('ylimits')
	def _ylog_changed(self):
		self.plot.set_ylog(self.ylog)
		self.update()

	def reset_autoscale(self):
		super(TimeTrendPanel, self).reset_autoscale()
		self.yauto = True

	def _legend_changed(self):
		if self.legend == 'off':
			legend = False
		elif self.legend == 'auto':
			legend = 'best'
		else:
			legend = self.legend
		self.plot.set_legend(legend)
		self.update()

	def get_general_view_group(self):
		return Group(
			Item('visible'),
			Item('filename', editor=gui.support.FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
			Item('reload', show_label=False),
			Item('legend'),
			show_border=True,
			label='General',
		)

	left_yaxis_group = Group(
		Item('primary_channels', editor=TimeTrendChannelListEditor()),
		Item('ylimits', style='custom', label='Limits'),
		show_border=True,
		label='Left y-axis'
	)

	def traits_view(self):
		return gui.support.PanelView(
			self.get_general_view_group(),
			Include('left_yaxis_group'),
			Include('relativistic_group'),
		)


class DoubleTimeTrendPanel(TimeTrendPanel):
	plotfactory = subplots.DoubleMultiTrend
	secondary_channels = Property(List(TimeTrendChannel), depends_on='channels')
	selected_secondary_channels = Property(depends_on='secondary_channels.checked')

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

	@cached_property
	def _get_secondary_channels(self):
		return list(self.filter_channels(TimeTrendChannel(id=name, label=name) for name in self.channels))

	def _get_selected_secondary_channels(self):
		return [chan.id for chan in self.secondary_channels if chan.checked]

	def _set_selected_secondary_channels(self, value):
		value = set(value) # to speed up membership tests
		for chan in self.secondary_channels:
			if chan.id in value:
				chan.checked = True
			else:
				chan.checked = False

	@gui.figure.DrawManager.avoid_callback_loop('ylimits', 'ylimits2')
	def ylim_callback(self, ax):
		if ax is self.plot.axes:
			self.ymin, self.ymax = ax.get_ylim()
			self.yauto = False
			logger.info('%s.ylim_callback primary: %s', self.__class__.__name__, self.ylimits)
		elif ax is self.plot.secondaryaxes:
			self.ymin2, self.ymax2 = ax.get_ylim()
			self.yauto2 = False
			logger.info('%s.ylim_callback secondary: %s', self.__class__.__name__, self.ylimits2)

	@on_trait_change('ymin2, ymax2, yauto2')
	@gui.figure.DrawManager.avoid_callback_loop('ylimits2')
	def ylim2_changed(self):
		logger.info('%s.ylim2_changed: %s', self.__class__.__name__, self.ylimits2)
		self.ymin2, self.ymax2 = self.plot.set_ylim2(self.ylimits2.min, self.ylimits2.max, self.ylimits2.auto)
		self.update()

	@gui.figure.DrawManager.avoid_callback_loop('ylimits2')
	def _ylog2_changed(self):
		self.plot.set_ylog2(self.ylog2)
		self.update()

	def reset_autoscale(self):
		super(DoubleTimeTrendPanel, self).reset_autoscale()
		self.yauto2 = True

	@on_trait_change('selected_primary_channels, selected_secondary_channels')
	def settings_changed(self):
		if not self.data:
			return
		self.plot.set_data(
			self.data.selectchannels(lambda chan: chan.id in self.selected_primary_channels),
			self.data.selectchannels(lambda chan: chan.id in self.selected_secondary_channels),
		)
		self.redraw()

	right_yaxis_group = Group(
		Item('secondary_channels', editor=TimeTrendChannelListEditor()),
		Item('ylimits2', style='custom', label='Limits'),
		show_border=True,
		label='Right y-axis'
	)

	def traits_view(self):
		return gui.support.PanelView(
			self.get_general_view_group(),
			Include('left_yaxis_group'),
			Include('right_yaxis_group'),
			Include('relativistic_group'),
		)


class XlimitsPanel(HasTraits):
	xlimits = Instance(gui.support.LogAxisLimits, args=())
	xauto = DelegatesTo('xlimits', 'auto')
	xmin = DelegatesTo('xlimits', 'min')
	xmax = DelegatesTo('xlimits', 'max')
	xlog = DelegatesTo('xlimits', 'log')

	traits_saved = 'xauto', 'xmin', 'xmax', 'xlog'

	@on_trait_change('xmin, xmax, xauto')
	@gui.figure.DrawManager.avoid_callback_loop('xlimits')
	def xlim_changed(self):
		logger.info('%s.xlim_changed: %s', self.__class__.__name__, self.xlimits)
		self.xmin, self.xmax = self.plot.set_xlim(self.xlimits.min, self.xlimits.max, self.xlimits.auto)
		self.update()

	@gui.figure.DrawManager.avoid_callback_loop('xlimits')
	def _xlog_changed(self):
		self.plot.set_xlog(self.xlog)
		self.update()

	@gui.figure.DrawManager.avoid_callback_loop('xlimits')
	def xlim_callback(self, ax):
		self.xmin, self.xmax = ax.get_xlim()
		self.xauto = False
		logger.info('%s.xlim_callback: %s', self.__class__.__name__, self.xlimits)

	def reset_autoscale(self):
		self.xauto = True


class CSVPanel(DoubleTimeTrendPanel):
	id = 'csv'
	label = 'Plain text (experimental)'
	desc = 'Flexible reader for CSV / tab separated / ASCII files.\n\nAccepts times as unix timestamp (seconds sinds 1970-1-1 00:00:00 UTC), Labview timestamp (seconds since since 1904-1-1 00:00:00 UTC), Matplotlib timestamps (days since 0001-01-01 UTC, plus 1) or arbitrary strings (strptime format).'

	datafactory = datasources.CSV
	filter = 'ASCII text files (*.txt, *.csv, *.tab)', '*.txt;*.csv;*.tab',

	time_type = Enum('unix', 'labview', 'matplotlib', 'custom')
	time_custom = Property(depends_on='time_type')
	time_format = Str('%Y-%m-%d %H:%M:%S')
	time_column = Str('auto')
	time_column_options = Property(depends_on='channels')

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
		return gui.support.EnumMapping([('auto', '(auto)')] + self.channels)

	def _time_column_changed(self):
		self.channels = list(self.channels) # trigger rebuild of primary_channels and secondary_channels

	@on_trait_change('selected_primary_channels, selected_secondary_channels, time_type, time_format, time_column')
	def settings_changed(self):
		if not self.data:
			return
		if self.time_column == 'auto':
			self.data.time_column = 'auto'
		else:
			self.data.time_column = self.channels.index(self.time_column)
		if self.time_custom:
			self.data.time_type = 'strptime'
			self.data.time_strptime = self.time_format
		else:
			self.data.time_type = self.time_type
		super(CSVPanel, self).settings_changed()

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
			Include('left_yaxis_group'),
			Include('right_yaxis_group'),
			Include('relativistic_group'),
		)


class Time2DPanel(TimeTrendPanel):
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
		super(Time2DPanel, self).__init__(*args, **kwargs)

	def _colormap_changed(self):
		self.plot.set_colormap(self.colormap)
		self.update()

	def _interpolation_changed(self):
		self.plot.set_interpolation(self.interpolation)
		self.update()

	@on_trait_change('cmin, cmax, cauto, clog')
	def clim_changed(self):
		self.plot.set_clim(self.climits.min, self.climits.max, self.climits.auto, self.climits.log)
		self.redraw()

	@on_trait_change('filename, reload')
	def load_file(self):
		super(Time2DPanel, self).load_file()
		self.plot.set_data(self.data)
		self.redraw()

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
