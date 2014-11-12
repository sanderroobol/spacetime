# This file is part of Spacetime.
#
# Copyright 2010-2014 Leiden University.
# Spec module written by Willem Onderwaater.
#
# Spacetime is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Spacetime is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import traits.api as traits
import traitsui.api as traitsui

from ..generic.gui import TimeTrendGUI
from ... import gui

from . import subplots, datasources

class Specfile(TimeTrendGUI):
	id = 'specfile'
	label = 'specfile'
	desc = 'Reads spec files from sychrotron lightsources'
	filter = 'Spec files (*.spec)', '*.spec'
	datafactory = datasources.Specfile
	plotfactory = subplots.Normalization

	normalize_channel = traits.Str('none')
	normalize_channel_options = traits.Property(depends_on='channel_names')
	normalize_factor = traits.Float(1.)

	traits_saved = 'normalize_channel', 'normalize_factor'

	firstscan = traits.Int(0)
	lastscan = traits.Int(1)
	scanmin = traits.Int(0)
	scanmax = traits.Int(1)

	def __init__(self, *args, **kwargs):
		super(Specfile, self).__init__(*args, **kwargs)
		self.ylog = True

	@traits.on_trait_change('firstscan')
	def first_changed(self):
		if self.firstscan > self.lastscan:
			self.lastscan = self.firstscan
		self.data.loaddata(self.firstscan, self.lastscan)
		self.update_channel_names()
		self.settings_changed()

	@traits.on_trait_change('lastscan')
	def last_changed(self):
		if self.firstscan > self.lastscan:
			self.firstscan = self.lastscan
		self.data.loaddata(self.firstscan, self.lastscan)
		self.update_channel_names()
		self.settings_changed()

	@traits.on_trait_change('filename')
	def _filename_changed(self):
		self.data = datasources.Specfile(self.filename)
		self.scanmin = self.data.getspecmin()
		self.scanmax = self.data.getspecmax()
		self.settings_changed()

	@traits.cached_property
	def _get_normalize_channel_options(self):
		return gui.support.EnumMapping([('none', 'Disable')] + self.channel_names)

	@traits.on_trait_change('normalize_channel, normalize_factor')
	def normalization_changed(self):
		if self.normalize_channel == 'none':
			self.plot.set_normalization(self.normalize_factor)
		else:
			self.plot.set_normalization(self.normalize_factor, self.data.selectchannels(lambda chan: chan.id == self.normalize_channel))
		self.rebuild()

	normalization_group = traitsui.Group(
		traitsui.Item('normalize_channel', label='Channel', editor=traitsui.EnumEditor(name='normalize_channel_options')),
		traitsui.Item('normalize_factor', label='Factor', editor=gui.support.FloatEditor()),
		show_border=True,
		label='Normalization',
	)

	scan_group = traitsui.Group(
		traitsui.Item('firstscan', label='first scan', editor=gui.support.RangeEditor(low_name='scanmin', high_name='scanmax', mode='spinner')),
		traitsui.Item('lastscan', label='last scan', editor=gui.support.RangeEditor(low_name='scanmin', high_name='scanmax', mode='spinner')),
		show_border=True,
		label='Scan range',
	)

	def traits_view(self):
		return gui.support.PanelView(
			self.get_general_view_group(),
			traitsui.Include('normalization_group'),
			traitsui.Include('scan_group'),
			traitsui.Include('yaxis_group'),
			traitsui.Include('relativistic_group'),
		)
