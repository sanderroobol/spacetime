import numpy

from ..generic.datasources import MultiTrend
from ...util import Struct

class LabviewMultiTrend(MultiTrend):
	data = None

	@staticmethod
	def parselabviewtimestamp(fl):
		# Labview uses the number of seconds since 1-1-1904 00:00:00 UTC.
		# mpldtfromdatetime(datetime.datetime(1904, 1, 1, 0, 0, 0, tzinfo=pytz.utc)) = 695056
		return fl / 86400. + 695056

	def set_header(self, line):
		self.channel_labels = line.strip().split('\t')

	def get_time_columns(self):
		return [i for (i,l) in enumerate(self.channel_labels) if l == 'Time']

	def get_channel_kwargs(self, label, i):
		return dict(id=label)

	def __init__(self, *args, **kwargs):
		super(LabviewMultiTrend, self).__init__(*args, **kwargs)
		fp = open(self.filename)
		self.set_header(fp.readline())

		self.data = numpy.loadtxt(fp)

		time_columns = self.get_time_columns()
		assert time_columns[0] == 0
		self.channels = []

		for i, label in enumerate(self.channel_labels):
			if time_columns and i == time_columns[0]:
				time = self.parselabviewtimestamp(self.data[:,time_columns.pop(0)])
			else:
				self.channels.append(Struct(time=time, value=self.data[:,i], **self.get_channel_kwargs(label, i)))


class GasCabinet(LabviewMultiTrend):
	controllers = ['NO', 'H2', 'O2', 'CO', 'Ar', 'Shunt', 'BPC1', 'BPC2']
	parameters = ['time', 'measure', 'set point', 'valve output']
	valves = ['MIX', 'MRS', 'INJ', 'OUT', 'Pump'] 

	def set_header(self, line):
		self.channel_labels = range(len(self.controllers) * len(self.parameters) + 1 + len(self.valves))

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

	def __init__(self, *args, **kwargs):
		super(GasCabinet, self).__init__(*args, **kwargs)
		assert self.data.shape[1] == len(self.controllers) * len(self.parameters) + 1 + len(self.valves)
