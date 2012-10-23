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

from ..generic.gui import TimeTrendGUI
from ... import gui

from . import datasources


class SRSScanGUI(TimeTrendGUI):
	id = 'srs_scan'
	label = 'SRS Scan'
	desc = 'Reads ASCII exported data from Stanford Research Systems Residual Gas Analyzers.'

	filter = 'ASCII text files (*.txt)', '*.txt',

	datafactory = datasources.SRSScan
