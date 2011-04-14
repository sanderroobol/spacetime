from ..generic.subplots import MultiTrend

class QMS(MultiTrend):
	def setup(self):
		super(QMS, self).setup()
		self.axes.set_ylabel('Ion current (A)')
