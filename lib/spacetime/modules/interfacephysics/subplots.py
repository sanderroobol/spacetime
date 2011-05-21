from ..generic.subplots import DoubleMultiTrend

class TPDirk(DoubleMultiTrend):
	def __init__(self, data=None, formatter=None):
		self.set_data(data)
		super(TPDirk, self).__init__(self.data, self.secondarydata, formatter)
	
	def set_data(self, data):
		self.realdata = data
		if data:
			self.data = data.selectchannels(lambda x: x.id == 'pressure')
			self.secondarydata = data.selectchannels(lambda x: x.id == 'temperature')
		else:
			self.data = None
			self.secondarydata = None

	def setup(self):
		super(TPDirk, self).setup()
		self.axes.set_ylabel('Pressure (mbar)')
		self.axes.set_yscale('log')
		self.secondaryaxes.set_ylabel('Temperature (K)')
