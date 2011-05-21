import numpy

from ..generic.subplots import DoubleMultiTrend, XAxisHandling

from ... import util

class CameraTrend(XAxisHandling, DoubleMultiTrend):
	xdata = None
	fft = False

	marker_points = None, None

	def set_data(self, y1, y2, x=None):
		super(CameraTrend, self).set_data(y1, y2)
		if x is None:
			self.xdata = None
		else:
			self.xdata = next(x.iterchannels())

	def xlim_rescale(self):
		if self.xdata or self.fft:
			super(CameraTrend, self).xlim_rescale()
		else:
			raise util.SharedXError

	def get_axes_requirements(self):
		return [util.Struct(twinx=True, independent_x=bool(self.xdata) or self.fft)]

	def setup(self):
		super(CameraTrend, self).setup()
		if (self.xdata or self.fft)and self.xlim_callback:
			self.axes.callbacks.connect('xlim_changed', self.xlim_callback)

	def get_xdata(self, chandata):
		if self.xdata:
			return self.xdata.value
		else:
			return super(CameraTrend, self).get_xdata(chandata)

	# this needs some more work to get properly working again, disable for now if it's not a simple multitrend
	def set_marker(self, left, right=None):
		if not self.fft and not self.xdata:
			return super(CameraTrend, self).set_marker(left, right)

"""
	def clear(self, quick=False):
		if not quick:
			self.clear_marker()
			#self.axes.relim()
		super(CameraTrend, self).clear(quick)

	def clear_marker(self):
		left, right = self.marker_points
		if left:
			self.axes.lines.remove(left)
		if right:
			self.axes.lines.remove(right)
		self.marker_points = None, None

	def set_marker(self, left, right=None):

		if self.fft:
			return
		elif not self.xdata:
			return super(CameraTrend, self).set_marker(left, right)

		self.clear_marker()

		if left is None:
			return

		index_left = numpy.searchsorted(self.x.time, left, 'left')
		if index_left == self.x.time.size:
			index_left -= 1

		left_point = self.axes.plot([self.xdata.value[index_left]], [self.data.value[index_left]], 'go')[0]
		if right is None:
			self.marker_points = left_point, None
		else:
			index_right = numpy.searchsorted(self.x.time, right, 'right')
			if index_right == self.x.time.size:
				index_right -= 1
			right_point = self.axes.plot([self.xdata.value[index_right]], [self.data.value[index_right]], 'ro')[0]
			self.marker_points = left_point, right_point

		return self.clear_marker
"""
