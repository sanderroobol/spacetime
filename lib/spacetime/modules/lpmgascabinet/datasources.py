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

import itertools
import numpy

from ..generic.datasources import CSV
from ...util import Struct

class GasCabinet(CSV):
	time_columns = 'auto'
	time_type = 'labview'

	controllers = ['NO', 'H2', 'O2', 'CO', 'Ar', 'Shunt', 'BPC1', 'BPC2']
	parameters = ['time', 'measure', 'set point', 'valve output']
	valves = ['MIX', 'MRS', 'INJ', 'OUT', 'Pump'] 

	def set_header(self, line):
		self.channel_labels = ['{0} {1}'.format(c, p) for (c, p) in itertools.product(self.controllers, self.parameters)] + \
			['Valves time'] + ['{0} valve'.format(v) for v in self.valves]

	def get_time_columns(self):
		return [len(self.parameters) * i for i in range(len(self.controllers))] + [len(self.controllers) * len(self.parameters)] 

	def get_channel_kwargs(self, label, i):
		if i < len(self.controllers)*len(self.parameters):
			c = self.controllers[i // len(self.parameters)]
			p = self.parameters[i % len(self.parameters)]
			return dict(id='{0} {1}'.format(c, p), type='controller', parameter=p, controller=c)
		else:
			v = self.valves[i - len(self.controllers)*len(self.parameters) - 1]
			return dict(id='{0} valve'.format(v), type='valve', valve=v)

	def verify_data(self, data):
		assert data.shape[1] == len(self.controllers) * len(self.parameters) + 1 + len(self.valves)
