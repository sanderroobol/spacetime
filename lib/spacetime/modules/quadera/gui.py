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

from ..generic.gui import TimeTrendGUI, Time2DGUI
from ... import gui

from . import subplots, datasources


class NormalizationGUI(HasTraits):
	normalize_channel = Str('none')
	normalize_channel_options = Property(depends_on='channels')
	normalize_factor = Float(1.)

	filter = 'Quadera ASCII files (*.asc)', '*.asc'

	traits_saved = 'normalize_channel', 'normalize_factor'

	def __init__(self, *args, **kwargs):
		super(NormalizationGUI, self).__init__(*args, **kwargs)
		self.ylog = True

	@cached_property
	def _get_normalize_channel_options(self):
		return gui.support.EnumMapping([('none', 'Disable')] + self.channels)

	@on_trait_change('normalize_channel, normalize_factor')
	def normalization_changed(self):
		if self.normalize_channel == 'none':
			self.plot.set_normalization(self.normalize_factor)
		else:
			self.plot.set_normalization(self.normalize_factor, self.data.selectchannels(lambda chan: chan.id == self.normalize_channel))
		self.rebuild()


class QuaderaMIDGUI(NormalizationGUI, TimeTrendGUI):
	id = 'quadera_mid'
	label = 'Quadera MID'
	desc = 'Reads ASCII exported Quadera MID projects from a Pfeiffer PrismaPlus quadrupole mass spectrometer.'

	plotfactory = subplots.QTrend
	datafactory = datasources.QuaderaMID

	def traits_view(self):
		return gui.support.PanelView(
			self.get_general_view_group(),
			Group(
				Item('normalize_channel', label='Channel', editor=EnumEditor(name='normalize_channel_options')),
				Item('normalize_factor', label='Factor', editor=gui.support.FloatEditor()),
				show_border=True,
				label='Normalization',
			),
			Include('left_yaxis_group'),
			Include('relativistic_group'),
		)


class QuaderaScanGUI(QuaderaMIDGUI):
	id = 'quadera_scan'
	label = 'Quadera Scan'
	desc = 'Reads ASCII exported Quadera Scan projects from a Pfeiffer PrismaPlus quadrupole mass spectrometer.'

	plotfactory = subplots.QTrend
	datafactory = datasources.QuaderaScan


class Quadera2DScanGUI(NormalizationGUI, Time2DGUI):
	id = 'quadera_scan2d'
	label = 'Quadera Scan 2D (experimental)'
	desc = 'Reads ASCII exported Quadera Scan projects from a Pfeiffer PrismaPlus quadrupole mass spectrometer, makes pretty 2D plots.'

	plotfactory = subplots.Q2D
	datafactory = datasources.QuaderaScan
