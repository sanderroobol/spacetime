# This file is part of Spacetime.
#
# Copyright 2010-2014 Leiden University.
# Written by Sander Roobol.
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

from ..generic.gui import DoubleTimeTrendGUI

from . import subplots, datasources

class GasCabinetGUI(DoubleTimeTrendGUI):
	id = 'lpmgascabinet'
	label = 'LPM Gas Cabinet'
	desc = 'Reads logs from LPM Gas Cabinet control software.'

	plotfactory = subplots.GasCabinet
	datafactory = datasources.GasCabinet
	filter = 'ASCII text files (*.txt)', '*.txt',
