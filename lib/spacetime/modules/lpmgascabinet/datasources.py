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
			return dict(id='{0} {1}'.format(c, p), parameter=p, controller=c)
		else:
			v = self.valves[i - len(self.controllers)*len(self.parameters) - 1]
			return dict(id='{0} valve'.format(v), valve=v)

	def verify_data(self, data):
		assert data.shape[1] == len(self.controllers) * len(self.parameters) + 1 + len(self.valves)
