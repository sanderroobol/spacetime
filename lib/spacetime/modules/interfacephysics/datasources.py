import datetime
import numpy

from ..generic.datasources import MultiTrend
from ..lpmgascabinet.datasources import LabviewMultiTrend
from ...util import Struct, mpldtfromdatetime


class ReactorEnvironment(LabviewMultiTrend):
	def __init__(self, *args, **kwargs):
		super(ReactorEnvironment, self).__init__(*args, **kwargs)
		fp = open(self.filename)
		columns = fp.readline().strip().split('\t')
		self.data = numpy.loadtxt(fp)
		fp.close()

		self.channels = []
		time = self.parselabviewdate(self.data[:,0])
		for i, v in enumerate(columns[1:]):
			self.channels.append(Struct(time=time, value=self.data[:,i+1], id=v))


class TPDirk(MultiTrend):
	def readiter(self):
		fp = open(self.filename)
		fp.readline() # ignore two header lines
		fp.readline()
		for line in fp:
			data = line.strip().split(';')
			if len(data) == 2: # last line ends with "date;time"
				continue
			no, dt, pressure, temperature = data
			yield numpy.array((
				mpldtfromdatetime(datetime.datetime.strptime(dt, '%y/%m/%d %H:%M:%S')),
				float(pressure),
				float(temperature)
			))

	def __init__(self, *args, **kwargs):
		super(TPDirk, self).__init__(*args, **kwargs)
		data = numpy.array(list(self.readiter()))
		self.channels = [
			Struct(id='pressure', time=data[:,0], value=data[:,1]),
			Struct(id='temperature', time=data[:,0], value=data[:,2]),
		]


class OldGasCabinet(MultiTrend):
	controllers = ['MFC CO', 'MFC NO', 'MFC H2', 'MFC O2', 'MFC Shunt', 'BPC1', 'BPC2', 'MFM Ar']
	parameters = ['valve output', 'measure', 'set point']
	data = None

	def __init__(self, *args, **kwargs):
		super(OldGasCabinet, self).__init__(*args, **kwargs)
		self.data = numpy.loadtxt(self.filename)
		# FIXME: this is an ugly hack to determine the date. the fileformat should be
        # modified such that date information is stored INSIDE the file
		import re
		y, m, d = re.search('(20[0-9]{2})([0-9]{2})([0-9]{2})', self.filename).groups()
 		self.offset = mpldtfromdatetime(datetime.datetime(int(y), int(m), int(d)))

		columns = self.data.shape[1]
		assert (columns - 2)  % 4 == 0
		self.channels = []
		for i in range((columns - 2) // 4):
			time = self.data[:,i*4]/86400 + self.offset
			for j, p in enumerate(self.parameters):
				self.channels.append(Struct(time=time, value=self.data[:,i*4+j+1], id='%s %s' % (self.controllers[i], p), parameter=p, controller=self.controllers[i]))
		# NOTE: the last two columns (Leak dectector) are ignored
