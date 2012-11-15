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
from enthought.pyface.api import ProgressDialog

import os
import wx
import glob
import operator
import string
import matplotlib.cm
import PIL.Image
import math

import logging
logger = logging.getLogger(__name__)

from ... import gui, util

from . import subplots, datasources, datasinks
from ..lpmcamera import filters


class Tab(traits.HasTraits):
	pass


class TraitsSavedMeta(traits.HasTraits.__metaclass__):
	def __new__(mcs, name, bases, dict):
		# Join traits_saved from current class and all its base classes.
		# Order is maintained during loading: traits_saved is evaluated from
		# left to right, and parent traits get restored before child traits.
		# The order of base classes is also respected in case of multiple
		# inherintance.
		# A child can override traits from a parent in two ways:
		# - a trait will be skipped completely if it is mentioned in traits_not_saved
		# - if a trait is mentioned by both parent and child, the child will take precedence

		saved = []
		for i in reversed(dict.get('traits_saved', ())):
			if '*' in i:
				if i.endswith('.*') and '.' not in i[:-2]:
					prefix = i[:-2]
					sub = dict[prefix]
					if isinstance(sub, traits.Instance) and issubclass(sub.klass, SerializableComponent):
						saved.extend('{0}.{1}'.format(prefix, j) for j in reversed(sub.klass.traits_saved))
					else:
						raise RuntimeError('traits_saved {0}.* pattern does correspond to a SerializableComponent'.format(sub))
				else:
					raise RuntimeError('bad traits_saved pattern, * can only be used in the form foo.*')
			else:
				saved.append(i)

		not_saved = set(dict.get('traits_not_saved', ()))
		
		for base in bases:
			for i in reversed(base.__dict__.get('traits_saved', ())):
				if i not in not_saved and i not in saved:
					saved.append(i)

		dict['traits_saved'] = tuple(reversed(saved))
		return traits.HasTraits.__metaclass__.__new__(mcs, name, bases, dict)


class SerializableBase(traits.HasTraits):
	__metaclass__ = TraitsSavedMeta

	def _getitem_serialized(self, key):
		if '.' in key:
			prefix, suffix = key.split('.', 1)
			src = getattr(self, prefix)
			if isinstance(src, SerializableComponent):
				return src._getitem_serialized(suffix)
			else:
				raise ValueError('prefix {0} is not a SerializableComponent'.format(prefix))
		else:
			return getattr(self, key)

	def get_serialized(self):
		if hasattr(self, 'traits_saved'):
			return dict((id, self._getitem_serialized(id)) for id in self.traits_saved)
		else:
			return dict()

	def _setitem_serialized(self, key, value):
		if '.' in key:
			prefix, suffix = key.split('.', 1)
			dest = getattr(self, prefix)
			if isinstance(dest, SerializableComponent):
				dest._setitem_serialized(suffix, value)
			else:
				raise ValueError('prefix {0} is not a SerializableComponent'.format(prefix))
		else:
			self.trait_set(**{key: value})


class SerializableComponent(SerializableBase):
	parent = traits.Instance(traits.HasTraits)
	context = traits.DelegatesTo('parent')

	def activate(self):
		pass

	def copy_from(self, source, deep=True):
		self.copy_traits(source, self.traits_saved)


class ActivationComponent(SerializableComponent):
	active = traits.Bool(False)
	gui_active = False
	traits_saved = 'active',

	def activate(self):
		self.active = True
	
	def activate_gui(self):
		self.gui_active = True


class NonLiveComponentHandler(traitsui.Handler):
	def close(self, info, is_ok=None):
		obj = info.ui.context['object']
		obj.gui_active = False
		return True


class NonLiveComponentEditor(SerializableComponent):
	traits_not_saved = 'active', 

	@classmethod
	def edit_nonlive(cls, source):
		obj = cls(id=source.id, parent=source.parent)
		obj.copy_from(source, deep=True)
		obj.activate_gui()

		if obj.edit_traits().result:
			source.copy_from(obj, deep=False)
			source.activate()
			return True
		return False


class SerializableTab(SerializableBase, Tab):
	context = traits.Instance(traits.HasTraits)
	_modified = traits.Bool(False)

	def __init__(self, *args, **kwargs):
		super(SerializableTab, self).__init__(*args, **kwargs)

		# don't simply pass in list(self.traits_saved) to work around a bug in on_trait_change
		for i in self.traits_saved:
			self.on_trait_change(self.set_modified, i)

	def _delayed_from_serialized(self, src):
		with self.context.canvas.hold():
			# trait_set has to be called separately for each trait to respect the ordering of traits_saved
			for id in self.traits_saved:
				if id in src:
					try: 
						self._setitem_serialized(id, src[id])
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
		logger.debug('%s.ylim_callback: %s', self.__class__.__name__, self.ylimits)

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
		logger.debug('%s.ylim_changed: %s', self.__class__.__name__, self.ylimits)
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
			logger.debug('%s.ylim_callback primary: %s', self.__class__.__name__, self.ylimits)
		elif ax is self.plot.secondaryaxes:
			with self.context.callbacks.avoid(self.ylimits2):
				self.ymin2, self.ymax2 = ax.get_ylim()
			if not self.context.callbacks.is_avoiding(self.ylimits2):
				self.yauto2 = False
			logger.debug('%s.ylim_callback secondary: %s', self.__class__.__name__, self.ylimits2)

	# extend the callback protection to include ylimits2 as well
	@traits.on_trait_change('ymin, ymax, yauto')
	@gui.figure.CallbackLoopManager.decorator('ylimits', 'ylimits2')
	def ylim_changed(self):
		# we cannot call ylim_changed directly, because it is protected by the CallbackloopManager
		super(DoubleTimeTrendGUI, self).ylim_changed.original(self)

	@traits.on_trait_change('ymin2, ymax2, yauto2')
	@gui.figure.CallbackLoopManager.decorator('ylimits', 'ylimits2')
	def ylim2_changed(self):
		logger.debug('%s.ylim2_changed: %s', self.__class__.__name__, self.ylimits2)
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
		logger.debug('%s.xlim_changed: %s', self.__class__.__name__, self.xlimits)
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
		logger.debug('%s.xlim_callback: %s', self.__class__.__name__, self.xlimits)

	def reset_autoscale(self):
		self.xauto = True


class CSVConfigurationHandler(traitsui.Handler):
	def close(self, info, is_ok=None):
		if not is_ok:
			return True

		obj = info.ui.context['object']

		data = obj.parent.datafactory()
		data.set_config(filename=obj.filename, delimiter=obj.delimiter, skip_lines=obj.skip_lines, time_type=obj.time_type, time_strptime=obj.time_format.strip(), time_column=obj.time_column)
		try:
			data.load(probe=True)
		except:
			gui.support.Message.exception('The file does not load correctly.', desc='Check the output below and resolve the problem.', title='Loading failed.', parent=info.ui.control)
			return False
		else:
			return True


class CSVConfiguration(ActivationComponent):
	filename = traits.File

	delimiter = traits.Enum('\t', ',', ';');
	skip_lines = traits.Int(0)

	time_type = traits.Enum('unix', 'labview', 'matplotlib', 'strptime')
	time_format = traits.Str('%Y-%m-%d %H:%M:%S')
	time_column = traits.Any('auto')

	active = traits.Bool(False)

	traits_saved = 'filename', 'delimiter', 'skip_lines', 'time_type', 'time_format', 'time_column', 'active'

	def get_datasource(self):
		data = self.parent.datafactory()
		data.set_config(filename=self.filename, delimiter=self.delimiter, skip_lines=self.skip_lines, time_type=self.time_type, time_strptime=self.time_format.strip(), time_column=self.time_column)
		data.load()
		return data


class CSVConfigurationEditor(CSVConfiguration, NonLiveComponentEditor):
	filter = 'ASCII text files (*.txt, *.csv, *.tab)', '*.txt;*.csv;*.tab',

	time_custom = traits.Property(depends_on='time_type')
	time_column_options = traits.Property(depends_on='filename, delimiter, skip_lines')

	def _get_time_custom(self):
		return self.time_type == 'strptime'

	@traits.cached_property
	def _get_time_column_options(self):
		return gui.support.EnumMapping([('auto', '(auto)')] + list(enumerate(self.parent.datafactory.probe_column_names(self.filename, self.delimiter, self.skip_lines))))

	def traits_view(self):
		return traitsui.View(
			traitsui.Group(
				traitsui.Group(
					traitsui.Item('filename', editor=gui.support.FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
					traitsui.Item('delimiter', label='Delimiter', editor=traitsui.EnumEditor(values=gui.support.EnumMapping([('\t', 'tab'), ',', ';']))),
					traitsui.Item('skip_lines', label='Skip header lines'), 
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


class CSVGUI(DoubleTimeTrendGUI):
	id = 'csv'
	label = 'Plain text'
	desc = 'Flexible reader for CSV / tab separated / ASCII files.\n\nAccepts times as unix timestamp (seconds sinds 1970-1-1 00:00:00 UTC), Labview timestamp (seconds since since 1904-1-1 00:00:00 UTC), Matplotlib timestamps (days since 0001-01-01 UTC, plus 1) or arbitrary strings (strptime format).'

	datafactory = datasources.CSV
	configuration = traits.Instance(CSVConfiguration)
	edit_configuration = traits.Button()

	traits_saved = 'configuration.*', 'selected_primary_channels', 'selected_secondary_channels'
	traits_not_saved = 'filename', 

	def _configuration_default(self):
		config = CSVConfiguration(id=self.id+'.configuration', parent=self)
		config.on_trait_change(self.load_file, 'active')
		return config

	def filter_channels(self, channels):
		if self.configuration.time_column == 'auto':
			if self.data:
				check = set(self.data.time_channel_headers)
			else:
				check = set()
		else:
			check = set([self.configuration.time_column])
		return (chan for chan in channels if chan.id not in check)

	# also responds to changes to configuration.active, dynamically defined in _configuration_default()
	@traits.on_trait_change('reload')
	def load_file(self):
		if self.configuration.active:
			self.data = self.configuration.get_datasource()
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
		CSVConfigurationEditor.edit_nonlive(self.configuration)


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
		logger.debug('%s.clim_callback: %s', self.__class__.__name__, self.climits)

	@traits.on_trait_change('cmin, cmax, cauto, clog')
	@gui.figure.CallbackLoopManager.decorator('climits')
	def clim_changed(self):
		logger.debug('%s.clim_changed: %s', self.__class__.__name__, self.climits)
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


class SingleFrameAnimation(traits.HasTraits):
	def animate(self):
		for i in range(self.animation_firstframe, self.animation_lastframe + 1):
			setattr(self, self.animation_framenumber_trait, i)
			yield

	animation_firstframe = traits.Int(0)
	animation_lastframe = traits.Int(0)
	animation_framecount = traits.Property(depends_on='animation_firstframe, animation_lastframe')

	#animation_framenumber_trait = 'another_trait' # trait to be animated
	#animation_framenumber_low = 0                 # int or trait name
	#animation_framenumber_high = 'some_trait'     # idem 

	def _get_animation_framecount(self):
		return self.animation_lastframe - self.animation_firstframe + 1

	def animation_view(self):
		if isinstance(self.animation_framenumber_low, basestring):
			lkey ='low_name'
		else:
			lkey = 'low'
		if isinstance(self.animation_framenumber_high, basestring):
			hkey ='high_name'
		else:
			hkey = 'high'
		rangeopts = {'mode':'spinner', lkey:self.animation_framenumber_low, hkey:self.animation_framenumber_high}
		return traitsui.View(traitsui.Group(
			traitsui.Group(
				traitsui.Item('animation_firstframe', label='First', editor=traitsui.RangeEditor(**rangeopts)),
				traitsui.Item('animation_lastframe', label='Last', editor=traitsui.RangeEditor(**rangeopts)),
				label='Frames',
				show_border=True,
			)
		))


class ImageGUI(SubplotGUI):
	colormap = 'gray'

	def _plot_default(self):
		plot = self.plotfactory()
		plot.set_colormap(self.colormap)
		plot.mode = 'single frame'
		return plot

	def reset_autoscale(self):
		self.rebuild()


class FalseColorImageGUI(FalseColorMap, ImageGUI):
	def _plot_default(self):
		plot = self.plotfactory()
		plot.set_clim_callback(self.clim_callback)
		plot.set_colormap(self.colormap)
		return plot


def ImageListEditor():
	return traitsui.TableEditor(
		sortable = True,
		configurable = False,
		show_column_labels = True,
		auto_size = False,
		columns = [
			CheckboxColumn(name='checked', label='', editable=False, width=0.05, horizontal_alignment='left'),
			ObjectColumn(name='id', label='#', editable=False, width=0.05, horizontal_alignment='left'),
			ObjectColumn(name='shortpath', label='Filename', editable=False, width=0.35, horizontal_alignment='left'),
			ObjectColumn(name='timestr', label='Timestamp', editable=False, width=0.35, horizontal_alignment='left'),
			ObjectColumn(name='exposure', editable=False, width=0.2, horizontal_alignment='left'),
		],
	)

def ImageListPreviewEditor():
	return traitsui.TableEditor(
		sortable = True,
		configurable = False,
		show_column_labels = True,
		auto_size = False,
		columns = [
			ObjectColumn(name='shortpath', label='Filename', editable=False, width=0.4, horizontal_alignment='left'),
			ObjectColumn(name='timestr', label='Timestamp', editable=False, width=0.45, horizontal_alignment='left'),
			ObjectColumn(name='exposure', editable=False, width=0.15, horizontal_alignment='left'),
		],
	)


class ImageFile(traits.HasTraits):
	id = traits.Int
	checked = traits.Bool
	shortpath = traits.Property(depends_on='path')
	path = traits.Str
	timestamp = traits.Float()
	timestr = traits.Property(depends_on='timestamp')
	exposure = traits.Float(0)
	parent = traits.Any

	@traits.cached_property
	def _get_shortpath(self):
		return os.path.basename(self.path)

	@traits.cached_property
	def _get_timestr(self):
		return util.datetimefrommpldt(self.timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')

	@classmethod
	def probefile(cls, parent, id, path, probefunc):
		timestamp, exposure = probefunc(id, path)
		return cls(parent=parent, id=id, checked=(id == 0), path=path, timestamp=timestamp, exposure=exposure)

	def _checked_changed(self):
		if self.checked and self.parent:
			for f in self.parent:
				if f.checked and f is not self:
					f.checked = False
					return

	@classmethod
	def copy(cls, org, parent):
		return cls(id=org.id, checked=org.checked, path=org.path, timestamp=org.timestamp, exposure=org.exposure, parent=parent)


class RGBImageConfiguration(ActivationComponent):
	directory = traits.Directory
	pattern = traits.Str('*')
	files = traits.List(traits.Instance(ImageFile))

	time_source = traits.Enum('header', 'ctime', 'mtime', 'manual')

	time_start = traits.DelegatesTo('time_start_editor', 'mpldt')
	time_start_editor = traits.Instance(gui.support.DateTimeSelector, args=())
	time_exposure = traits.Float(1)
	time_delay = traits.Float(0)

	traits_saved = 'directory', 'pattern', 'time_source', 'time_start', 'time_exposure', 'time_delay', 'time_source', 'active'

	def copy_from(self, source, deep=True):
		super(RGBImageConfiguration, self).copy_from(source, deep)
		if deep:
			self.files = []
			files = [ImageFile.copy(f, parent=self.files) for f in source.files]
			self.files.extend(files)
		else:
			self.files = source.files

	def activate(self):
		self.trait_setq(active=True)

	def get_timestamp(self, i, fn):
		try:
			if self.time_source == 'manual':
				return self.time_start + i * (self.time_exposure + self.time_delay) / 864e5, self.time_exposure # 864e5 ms per day
			elif self.time_source in ('ctime', 'mtime'):
				return util.mpldtfromtimestamp(getattr(os.stat(fn), 'st_' + self.time_source)), 0
			elif self.time_source == 'header':
				return datasources.RGBImage.autodetect_timeinfo(fn)
		except:
			return 0., 0.

	def sort_files(self, files):
		if self.time_source != 'manual':
			files = sorted(files, key=operator.attrgetter('timestamp'))
			for i, f in enumerate(files):
				f.id = i
		return files

	def get_files(self, reload=False):
		chunksize = self.parent.probe_progress_chunksize

		if reload or not self.files:
			filenames = glob.glob(os.path.join(self.directory, self.pattern))
			chunkcount = int(math.ceil(float(len(filenames)) / chunksize))
			if chunkcount > 1:
				progress = ProgressDialog(title="Images", message="Loading images", max=chunkcount, can_cancel=False, parent=self.parent.context.uiparent)
			else:
				progress = gui.support.DummyProgressDialog()

			files = []
			progress.open()
			for i in range(chunkcount):
				eiter = enumerate(filenames[chunksize*i:chunksize*(i+1)], chunksize*i)
				files.extend(ImageFile.probefile(files, i, fn, self.get_timestamp) for (i, fn) in eiter)
				progress.update(i)
			progress.update(progress.max)
			progress.close()
		self.files = self.sort_files(files)


class RGBImageConfigurationEditor(RGBImageConfiguration, NonLiveComponentEditor):
	traits_nonlive_synced = 'files',

	time_manual = traits.Property(traits.Bool, depends_on='time_source')

	@traits.cached_property
	def _get_time_manual(self):
		return self.time_source == 'manual'

	@traits.on_trait_change('directory, pattern')
	def reload_files(self):
		if self.gui_active:
			self.get_files(reload=True)

	@traits.on_trait_change('time_source')
	def retime_files(self):
		if not self.gui_active:
			return
		chunksize = self.parent.probe_progress_chunksize
		chunkcount = int(math.ceil(float(len(self.files)) / chunksize))
		if chunkcount > 1:
			progress = ProgressDialog(title="Images", message="Loading images", max=chunkcount, can_cancel=False, parent=self.context.uiparent)
		else:
			progress = gui.support.DummyProgressDialog()

		progress.open()
		for i, f in enumerate(self.files):
			if i % chunksize == 0:
				progress.update(i / chunksize)
			f.timestamp, f.exposure = self.get_timestamp(i, f.path)
			
		self.files = self.sort_files(self.files)
		progress.update(progress.max)
		progress.close()

	@traits.on_trait_change('time_start, time_exposure, time_delay')
	def manual_retime_files(self):
		if self.time_manual:
			self.retime_files()

	def traits_view(self):
		return traitsui.View(
			traitsui.Group(
				traitsui.Group(
					traitsui.Item('directory', editor=gui.support.DirectoryEditor()),
					traitsui.Item('pattern'),
					label='Files',
					show_border=True,
				),
				traitsui.Group(
					traitsui.Item('time_source', editor=traitsui.EnumEditor(values=gui.support.EnumMapping((('header', 'File header (EXIF/DM3)'), ('ctime', 'File created'), ('mtime', 'File last modified'), ('manual', 'Manual'))))),
					traitsui.Item('time_start_editor', label='Start', style='custom', enabled_when='time_manual', editor=traitsui.InstanceEditor(view='precision_view')),
					traitsui.Item('time_exposure', label='Exposure (ms)', enabled_when='time_manual', editor=gui.support.FloatEditor()),
					traitsui.Item('time_delay', label='Delay (ms)', enabled_when='time_manual', editor=gui.support.FloatEditor()),
					label='Time',
					show_border=True,
				),
				traitsui.Group(
					traitsui.Item('files', height=350, editor=ImageListPreviewEditor()),
					show_labels=False,
					label='Preview',
					show_border=True,
				),
				layout='normal',
			),
			handler=NonLiveComponentHandler(),
			buttons=traitsui.OKCancelButtons,
			width=500,
			kind='livemodal',
			resizable=True,
		)


class RGBImageGUI(ImageGUI, SingleFrameAnimation):
	id = 'rgbimage'
	label = 'Image'
	desc = 'DM3 microscopy images and ordinary bitmaps (PNG, JPEG, TIFF, BMP, ...)'

	configuration = traits.Instance(RGBImageConfiguration)
	select_files = traits.Button
	files = traits.DelegatesTo('configuration')

	selected_index = traits.Int(0)
	selected_index_lock = traits.Instance(object, args=())
	file_number_max = traits.Property(depends_on='files')
	clip = traits.Float(3)

	traits_saved = 'configuration.*', 'selected_index', 'clip'
	traits_not_saved = 'filename',

	plotfactory = subplots.Image
	datafactory = datasources.RGBImage

	animation_framenumber_trait = 'selected_index'
	animation_framenumber_low = 0
	animation_framenumber_high = 'file_number_max'

	probe_progress_chunksize = 25

	def _configuration_default(self):
		config = RGBImageConfiguration(id=self.id+'.configuration', parent=self)
		config.on_trait_change(self.load_files, 'active')
		return config

	@traits.cached_property
	def _get_file_number_max(self):
		return max(0, len(self.files) - 1)

	def _reload_fired(self):
		self.load_files(reload=True)

	def load_files(self, reload=False):
		if self.configuration.active:
			self.configuration.get_files(reload=reload)

	@traits.on_trait_change('files, files.checked')
	def files_changed(self, object, name, old, new):
		# CallbackLoopManager.decorator is not compatible with the extra parameters for trait notification, so check and avoid manually
		if self.context.callbacks.is_avoiding('selected_index_lock'):
			return
		with self.context.callbacks.avoid('selected_index_lock'):
			# ignore uncheck events, unless unchecking the last file
			if name == 'checked' and old == True and new == False:
				if sum(f.checked for f in self.files) == 0:
					object.checked = True
				return 
			try:
				self.selected_index = self.files.index(object)
			except ValueError:
				self.selected_index = 0
			self.file_changed()

	@gui.figure.CallbackLoopManager.decorator('selected_index_lock')
	def _selected_index_changed(self):
		self.files[self.selected_index].checked = True
		self.file_changed()

	@traits.on_trait_change('clip')
	def file_changed(self):
		f = self.files[self.selected_index]
		if f.exposure:
			tend = f.timestamp + f.exposure / 864e5
		else:
			tend = None
		data = self.datafactory.autodetect(f.path, f.timestamp, tend)
		if self.clip > 0:
			data = data.apply_filter(filters.ClipStdDev(self.clip))
		self.plot.set_data(data)
		self.rebuild()

	def _select_files_fired(self):
		RGBImageConfigurationEditor.edit_nonlive(self.configuration)

	def traits_view(self):
		return gui.support.PanelView(
			traitsui.Group(
				traitsui.Item('visible'),
				traitsui.Item('size'),
				traitsui.Item('select_files', show_label=False),
				traitsui.Item('reload', show_label=False, enabled_when='configuration.active'),
				traitsui.Item('selected_index', label='Number', editor=traitsui.RangeEditor(low=0, high_name='file_number_max', mode='spinner', enter_set=True, auto_set=False)),
				traitsui.Item('clip', label='Color clipping', tooltip='Clip DM3 greyscale at <number> standard deviations away from the average (0 to disable)', editor=gui.support.FloatEditor()),
				show_border=True,
				label='General',
			),
			traitsui.Group(
				traitsui.Item('files', label='File', editor=ImageListEditor()),
				show_labels=False,
				show_border=True,
				label='Files',
			),
		)


class DM3Stack(ImageGUI, SingleFrameAnimation):
	id = 'dm3stack'
	label = 'DM3 stack'
	desc = 'Stack of DM3 microscopy images with manual timing'

	animation_framenumber_trait = 'framenumber'
	animation_framenumber_low = 0
	animation_framenumber_high = 'framecount'

	datafactory = datasources.DM3Stack
	plotfactory = subplots.Image

	framemax = traits.Int(0)
	framenumber = traits.Int(0)

	exposure = traits.Float(1000)
	delay = traits.Float(0)
	tstart = gui.support.DateTimeSelector()
	tstart_mpldt = traits.DelegatesTo('tstart', 'mpldt')

	clip = traits.Float(3)
	
	traits_saved = 'framenumber', 'exposure', 'delay', 'tstart_mpldt', 'clip'

	@traits.on_trait_change('filename, reload')
	def load_file(self):
		data = self.data = self.datafactory(self.filename)
		self.framemax = self.data.framecount - 1
		if self.framenumber > self.framemax:
			self.framenumber = self.framemax
		else:
			self.settings_changed()

	@traits.on_trait_change('framenumber, exposure, delay, tstart_mpldt, clip')
	def settings_changed(self):
		if not self.data:
			return
		self.data.set_settings(self.framenumber, self.tstart_mpldt, self.exposure/864e5, self.delay/864e5)
		if self.clip > 0:
			data = self.data.apply_filter(filters.ClipStdDev(self.clip))
			self.plot.set_data(data)
		else:
			self.plot.set_data(self.data)
		self.rebuild()

	def traits_view(self):
		return gui.support.PanelView(
			traitsui.Group(
				traitsui.Item('visible'),
				traitsui.Item('filename', editor=gui.support.FileEditor(filter=['DM3 files', '*.dm3', 'All files', '*'], entries=0)),
				traitsui.Item('reload', show_label=False),
				traitsui.Item('size'),
				traitsui.Item('framenumber', editor=traitsui.RangeEditor(low=0, high_name='framemax', mode='spinner', enter_set=True, auto_set=False)),
				traitsui.Item('clip', label='Color clipping', tooltip='Clip DM3 greyscale at <number> standard deviations away from the average (0 to disable)', editor=gui.support.FloatEditor()),
				show_border=True,
				label='General',
			),
			traitsui.Group(
				traitsui.Item('tstart', label='Acquisition start', style='custom', editor=traitsui.InstanceEditor()),
				traitsui.Item('exposure', label='Exposure (ms)'),
				traitsui.Item('delay', label='Delay (ms)'),
				show_border=True,
				label='Manual timing',
			),
		)
