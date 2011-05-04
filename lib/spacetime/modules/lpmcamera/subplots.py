from ..generic.subplots import DoubleMultiTrend, XAxisHandling

from ... import util

class CameraTrend(XAxisHandling, DoubleMultiTrend):
	fft = False

	def xlim_rescale(self):
		if self.fft:
			super(CameraTrend, self).xlim_rescale()

	def get_axes_requirements(self):
		return [util.Struct(twinx=True, independent_x=self.fft)]

	def setup(self):
		super(CameraTrend, self).setup()
		if self.fft and self.xlim_callback:
			self.axes.callbacks.connect('xlim_changed', self.xlim_callback)

	def draw(self):
		super(CameraTrend, self).draw()
		if self.fft and self.xlog:
			self.axes.set_xscale('log')
			self.secondaryaxes.set_xscale('log')
