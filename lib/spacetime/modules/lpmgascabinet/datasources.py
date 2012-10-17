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

class GasCabinet(CSV):
	time_columns = 'auto'
	time_type = 'labview'

	controllers = ['NO', 'H2', 'O2', 'CO', 'Ar', 'Shunt', 'Reactor', 'Pulse']
	controller_parameters = ['time', 'measure', 'setpoint', 'valve position']

	controller_aliases = {
		'BPC1': 'Reactor',
		'BPC2': 'Pulse',
	}
	controller_parameter_aliases = {
		'set point': 'setpoint',
		'valve output': 'valve position',
	}

	valves = ['MIX', 'MRS', 'INJ', 'OUT', 'Pump']
	valve_aliases = {}
	valve_parameters = ['position']
	valve_parameter_aliases = {
		'valve': 'position'
	}

	def parse_column_names(self, line):
		labels = line.split('\t')
		self.channel_kwargs = []
		self.channel_labels = []
		for l in labels:
			info = self.channel_mapping[l.lower()]
			self.channel_kwargs.append(info)
			self.channel_labels.append(info['id'])

	def get_channel_kwargs(self, label, i):
		return self.channel_kwargs[i]

	def make_channel_mapping(self):
		# construct mapping with all possible names that we might encounter
		self.channel_mapping = {}

		controllers = dict((c, c) for c in self.controllers)
		controllers.update(self.controller_aliases)
		controller_parameters = dict((p, p) for p in self.controller_parameters)
		controller_parameters.update(self.controller_parameter_aliases)
		for (ca, c), (pa, p) in itertools.product(controllers.iteritems(), controller_parameters.iteritems()):
			self.channel_mapping['{0} {1}'.format(ca, pa).lower()] = dict(
				id = '{0} {1}'.format(c, p),
				type = 'controller',
				controller = c,
				parameter = p,
			)

		valves = dict((v, v) for v in self.valves)
		valves.update(self.valve_aliases)
		valve_parameters = dict((p, p) for p in self.valve_parameters)
		valve_parameters.update(self.valve_parameter_aliases)
		for (va, v), (pa, p) in itertools.product(valves.iteritems(), valve_parameters.iteritems()):
			self.channel_mapping['{0} {1}'.format(va, pa).lower()] = dict(
				id = '{0} {1}'.format(v, p),
				type = 'valve',
				valve = v,
			)

		self.channel_mapping['time'] = dict(id='time')
		self.channel_mapping['valves time'] = dict(id='Valves time')

	def read_header(self, fp):
		self.make_channel_mapping()

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
			self.parse_column_names('\t'.join(columns))
			self.get_time_columns = lambda: [len(self.controller_parameters) * i for i in range(len(self.controllers))] + [len(self.controllers) * len(self.controller_parameters)] 
		else:
			self.parse_column_names(line1.strip())
