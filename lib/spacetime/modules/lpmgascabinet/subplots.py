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

	def draw_legend(self):
		if self.legend:
			handles1, labels1 = self.axes.get_legend_handles_labels()
			handles2, labels2 = self.secondaryaxes.get_legend_handles_labels()

			handles = []
			labels = []
			previd = None
			for (h, l) in zip(handles1 + handles2, labels1 + labels2):
				id = l.split()[0]
				if id != previd:
					handles.append(h)
					labels.append(id)
					previd = id

			self.axes.legend_ = None
			if len(handles):
				self.secondaryaxes.legend(handles, labels, loc=self.legend, prop=self.legendprops)
