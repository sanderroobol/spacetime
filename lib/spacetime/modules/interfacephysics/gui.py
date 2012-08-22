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

from ..generic.gui import DoubleTimeTrendGUI
from ..generic.datasources import CSVFactory
from ..lpmcamera.gui import CameraTrendGUI
from ..lpmcamera.datasources import Camera as CameraDataSource
from ..lpmgascabinet import subplots as lpmsubplots
from ...gui import support

from . import subplots
from . import datasources


class TPDirkGUI(DoubleTimeTrendGUI):
	id = 'tpdirk'
	label = 'TPDirk'
	desc = 'Simple temperature/pressure readout for Dirk and the VT STM.'

	plotfactory = subplots.TPDirk
	datafactory = datasources.TPDirk
	filter = 'Dirk\'s ASCII files (*.txt)', '*.txt'

	def __init__(self, *args, **kwargs):
		super(TPDirkGUI, self).__init__(*args, **kwargs)
		self.ylog = True

	@traits.on_trait_change('filename, reload')
	def load_file(self):
		if self.filename:
			try:
				self.data = self.datafactory(self.filename)
			except:
				support.Message.file_open_failed(self.filename, parent=self.context.uiparent)
				self.filename = ''
				return
			self.plot.set_data(self.data)
			self.rebuild()

	def traits_view(self):
		return support.PanelView(
			traitsui.Group(
				traitsui.Item('visible'),
				traitsui.Item('filename', editor=support.FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
				traitsui.Item('reload', show_label=False),
				traitsui.Item('legend'),
				show_border=True,
				label='General',
			),
			traitsui.Group(
				traitsui.Item('ylimits', style='custom', label='Left limits'),
				traitsui.Item('ylimits2', style='custom', label='Right limits'),
				show_border=True,
				label='Y axes'
			),
			traitsui.Include('relativistic_group'),
		)


class OldGasCabinetGUI(DoubleTimeTrendGUI):
	id = 'prototypegascabinet'
	label = 'Prototype gas cabinet'
	desc = 'Reads the data of the ReactorSTM gas cabinet.'

	plotfactory = lpmsubplots.GasCabinet
	datafactory = datasources.OldGasCabinet
	filter = 'ASCII text files (*.txt)', '*.txt',


class ReactorEnvironmentGUI(DoubleTimeTrendGUI):
	id = 'reactorenvironment'
	label = 'Reactor Environment logger'
	desc = 'Reads the log of the pressure, temperature and heater control for the ReactorAFM.'

	datafactory = CSVFactory(time_type='labview', time_column='auto')
	filter = 'ASCII text files (*.txt)', '*.txt',

	def filter_channels(self, channels):
		return (chan for chan in channels if chan.id != 'Time')

class PLLMonitor(ReactorEnvironmentGUI):
	id = 'pllmonitor'
	label = 'PLL monitor'
	desc = 'Monitors resonance frequency and noise of the quartz tuning fork of the ReactorAFM.'
