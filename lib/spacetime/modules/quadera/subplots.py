from ..generic.subplots import MultiTrend

class QMS(MultiTrend):
	normalization_factor = normalization_channel = 1

	def setup(self):
		super(QMS, self).setup()
		self.axes.set_ylabel('Ion current (A)')

	def set_normalization(self, factor, channel=None):
		self.normalization_factor = factor
		if channel:
			self.normalization_channel = next(channel.iterchannels()).value
		else:
			self.normalization_channel = 1

	def get_ydata(self, chandata):
		return chandata.value * self.normalization_factor / self.normalization_channel
