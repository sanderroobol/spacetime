# This file is part of Spacetime.
#
# Copyright (C) 2010-2013 Leiden University.
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

import traits.api as traits
import traitsui.api as traitsui

from ..generic.gui import SubplotGUI, TimeTrendGUI, Time2DGUI, SerializableBase
from ... import gui

from . import subplots, datasources


class NormalizationBase(SerializableBase):
	normalize_channel = traits.Str('none')
	normalize_channel_options = traits.Property(depends_on='channel_names')
	normalize_factor = traits.Float(1.)

	traits_saved = 'normalize_channel', 'normalize_factor'

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


class NormalizationTrendGUI(NormalizationBase, TimeTrendGUI):
	plotfactory = subplots.MSTrend

	def __init__(self, *args, **kwargs):
		super(NormalizationTrendGUI, self).__init__(*args, **kwargs)
		self.ylog = True

	def traits_view(self):
		return gui.support.PanelView(
			self.get_general_view_group(),
			traitsui.Include('normalization_group'),
			traitsui.Include('yaxis_group'),
			traitsui.Include('relativistic_group'),
		)


class Normalization2DGUI(NormalizationBase, Time2DGUI):
	plotfactory = subplots.MS2D

	def traits_view(self):
		return gui.support.PanelView(
			self.get_general_view_group(),
			traitsui.Include('normalization_group'),
			traitsui.Include('false_color_group'),
			traitsui.Include('limits_group'),
			traitsui.Include('relativistic_group'),
		)


class QuaderaMIDGUI(NormalizationTrendGUI):
	id = 'quadera_mid'
	label = 'Quadera MID'
	desc = 'Reads ASCII exported Quadera MID projects from a Pfeiffer PrismaPlus quadrupole mass spectrometer.'
	filter = 'Quadera ASCII files (*.asc)', '*.asc'
	datafactory = datasources.QuaderaMID


class QuaderaScanGUI(NormalizationTrendGUI):
	id = 'quadera_scan'
	label = 'Quadera Scan'
	desc = 'Reads ASCII exported Quadera Scan projects from a Pfeiffer PrismaPlus quadrupole mass spectrometer.'
	filter = 'Quadera ASCII files (*.asc)', '*.asc'
	datafactory = datasources.QuaderaScan


class Quadera2DScanGUI(Normalization2DGUI):
	id = 'quadera_scan2d'
	label = 'Quadera Scan 2D (experimental)'
	desc = 'Reads ASCII exported Quadera Scan projects from a Pfeiffer PrismaPlus quadrupole mass spectrometer, makes pretty 2D plots.'
	filter = 'Quadera ASCII files (*.asc)', '*.asc'
	datafactory = datasources.QuaderaScan


class MKSPeakJump(NormalizationTrendGUI):
	id = 'mks_peakjump'
	label = 'MKS Peak Jump'
	desc = 'Reads ASCII files from MKS RGA.'
	filter = 'Text files (*.txt)', '*.txt'
	datafactory = datasources.MKSPeakJump


class SRSScanGUI(NormalizationTrendGUI):
	id = 'srs_scan'
	label = 'SRS Scan'
	desc = 'Reads ASCII exported data from Stanford Research Systems Residual Gas Analyzers.'
	filter = 'ASCII text files (*.txt)', '*.txt',
	datafactory = datasources.SRSScan

class SRSDirectory(object):
	def get_general_view_group(self):
		return traitsui.Group(
			traitsui.Item('visible'),
			traitsui.Item('filename', label='Directory', editor=gui.support.DirectoryEditor()),
			traitsui.Item('reload', show_label=False),
			traitsui.Item('legend'),
			traitsui.Item('size'),
			show_border=True,
			label='General',
		)

class SRSAnalogGUI(SRSDirectory, NormalizationTrendGUI):
	id = 'srs_analog'
	label = 'SRS analog'
	desc = 'Reads a folder of ASCII files from SRS analog scans.'
	datafactory = datasources.SRSAnalog

class SRS2DAnalogGUI(SRSDirectory, Normalization2DGUI):
	id = 'srs_analog2d'
	label = 'SRS analog 2D (experimental)'
	desc = 'Reads a folder of ASCII files from SRS analog scans, makes pretty 2D plots.'
	datafactory = datasources.SRSAnalog
