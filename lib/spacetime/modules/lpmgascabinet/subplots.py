from ..generic.subplots import DoubleMultiTrend, MultiTrendFormatter

class GasCabinetFormatter(MultiTrendFormatter):
	prevcontroller = None

	def reset(self):
		self.prevcontroller = None
		super(GasCabinetFormatter, self).reset()

	def __call__(self, data):
		if data.parameter == 'set point':
			linestyle = '--' # dashed
		elif data.parameter == 'valve output':
			linestyle = ':'
		else:
			linestyle = '-' # solid
	
		if self.prevcontroller != data.controller:
			self.increase_counter()
			self.prevcontroller = data.controller

		return self.colors[self.counter] + linestyle


class GasCabinet(DoubleMultiTrend):
	def __init__(self, data=None, secondarydata=None, formatter=None):
		if formatter is None:
			formatter = GasCabinetFormatter()
		super(GasCabinet, self).__init__(data, secondarydata, formatter)

	def draw(self):
		super(GasCabinet, self).draw()
		self.axes.set_ylabel('')
		self.secondaryaxes.set_ylabel('')

		if self.data and list(self.data.iterchannelnames()):
			if all(chan.startswith('MF') for chan in self.data.iterchannelnames()):
				self.axes.set_ylabel('Mass flow (mbar l/min)')
			elif all(chan.startswith('BPC') for chan in self.data.iterchannelnames()):
				self.axes.set_ylabel('Pressure (bar)')

		if self.secondarydata and list(self.secondarydata.iterchannelnames()):
			if all(chan.startswith('MF') for chan in self.secondarydata.iterchannelnames()):
				self.secondaryaxes.set_ylabel('Mass flow (mbar l/min)')
			elif all(chan.startswith('BPC') for chan in self.secondarydata.iterchannelnames()):
				self.secondaryaxes.set_ylabel('Pressure (bar)')

	def get_legend_items(self):
		handles, labels = super(GasCabinet, self).get_legend_items()
		newhandles = []
		newlabels = []
		previd = None
		for (h, l) in zip(handles, labels):
			id = l.split()[0]
			if id != previd:
				newhandles.append(h)
				newlabels.append(id)
				previd = id
		return newhandles, newlabels
