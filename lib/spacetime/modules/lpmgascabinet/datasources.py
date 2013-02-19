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

from ..generic.datasources import CustomCSV

class GasCabinet(CustomCSV):
	time_columns = 'auto'
	time_type = 'labview'

	controllers = ['NO', 'H2', 'O2', 'CO', 'Ar', 'Shunt', 'Reactor', 'Pulse'] # DO NOT TOUCH, used to generate header for certain malformed files
	controller_parameters = ['time', 'measure', 'setpoint', 'valve position'] # DO NOT TOUCH, idem

	controller_parameter_aliases = {
		'set point': 'setpoint',
		'valve output': 'valve position',
	}

	valves = ['MIX', 'MRS', 'INJ', 'OUT', 'Pump'] # DO NOT TOUCH, idem
	valve_parameters = ['time', 'position']
	valve_parameter_aliases = {
		'valve': 'position'
	}

	def parse_column_label(self, lbl):
		ll = lbl.lower()

		for pa, p in itertools.chain(((p, p) for p in self.controller_parameters), self.controller_parameter_aliases.iteritems()):
			if ll.endswith(' {0}'.format(pa)):
				return dict(id=lbl, type='controller', controller=lbl[:-len(pa)-1], parameter=p)

		for pa, p in itertools.chain(((p, p) for p in self.valve_parameters), self.valve_parameter_aliases.iteritems()):
			if ll.endswith(' {0}'.format(pa)):
				return dict(id=lbl, type='valve', valve=lbl[:-len(pa)-1], parameter=p)

		if ll.endswith(' time') or lbl == 'time':
			return dict(id=lbl, parameter='time')

		return dict(id=lbl, parameter=None)

	def get_channel_kwargs(self, label, i):
		return self.channel_kwargs[i]

	def get_time_columns(self):
		return [i for (i, d) in enumerate(self.channel_kwargs) if d['parameter'].lower() == 'time']

	def read_header(self, fp):
		line1 = fp.readline()
		line2 = fp.readline()
		fp.seek(len(line1)) # line2 contains real data, we want to read this again later on
		
		headercount = len(line1.split('\t'))
		datacount = len(line2.split('\t'))
		if headercount == 29 and (datacount == 37 or datacount == 38):
			# support the buggy header from some versions of the LabVIEW gas cabinet control software
			columns = ['{0} {1}'.format(c, p) for (c, p) in itertools.product(self.controllers, self.controller_parameters)] + \
				['Valves time'] + ['{0} valve'.format(v) for v in self.valves]
			if datacount == 37:
				columns.pop()
			self.channel_labels = columns
		else:
			self.channel_labels = line1.strip().split('\t')
		self.channel_kwargs = [self.parse_column_label(lbl) for lbl in self.channel_labels]
