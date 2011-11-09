from ..generic.subplots import MultiTrend, Time2D

class Normalization(object):
	normalization_factor = normalization_channel = 1

	def set_normalization(self, factor, channel=None):
		self.normalization_factor = factor
		if channel:
			self.normalization_channel = next(channel.iterchannels()).value
		else:
			self.normalization_channel = 1


class QTrend(Normalization, MultiTrend):
	def setup(self):
		super(QTrend, self).setup()
		self.axes.set_ylabel('Ion current (A)')

	def get_ydata(self, chandata):
		return chandata.value * self.normalization_factor / self.normalization_channel


class Q2D(Normalization, Time2D):
	def setup(self):
		super(Q2D, self).setup()
		self.axes.set_ylabel('Mass (a.m.u.)')

	def get_imdata(self, imdata):
		return imdata.data# * self.normalization_factor / self.normalization_channel
