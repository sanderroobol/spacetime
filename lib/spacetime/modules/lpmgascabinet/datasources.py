import numpy

from ..generic.datasources import MultiTrend
from ...util import Struct

class LabviewMultiTrend(MultiTrend):
	@staticmethod
	def parselabviewdate(fl):
		# Labview uses the number of seconds since 1-1-1904 00:00:00 UTC.
		# mpldtfromdatetime(datetime.datetime(1904, 1, 1, 0, 0, 0, tzinfo=pytz.utc)) = 695056
		# FIXME: the + 1./24 is a hack to convert to local time
		return fl / 86400. + 695056 + 1./24


class GasCabinet(LabviewMultiTrend):
	controllers = ['NO', 'H2', 'O2', 'CO', 'Ar', 'Shunt', 'BPC1', 'BPC2']
	parameters = ['time', 'measure', 'set point', 'valve output']
	valves = ['MIX', 'MRS', 'INJ', 'OUT', 'Pump'] 
	data = None

	def __init__(self, *args, **kwargs):
		super(GasCabinet, self).__init__(*args, **kwargs)
		self.data = numpy.loadtxt(self.filename, skiprows=1) # skip header line

		assert self.data.shape[1] == 38
		self.channels = []
		for i, c in enumerate(self.controllers):
			time = self.parselabviewdate(self.data[:,i*4])
			for j, p in enumerate(self.parameters[1:]):
				self.channels.append(Struct(time=time, value=self.data[:,i*4+j+1], id='%s %s' % (c, p), parameter=p, controller=c))

		colstart = len(self.controllers) * len(self.parameters)
		time = self.parselabviewdate(self.data[:,colstart])
		for i, v in enumerate(self.valves):
			self.channels.append(Struct(time=time, value=self.data[:,colstart+i+1], id='%s valve' % v, valve=v))
