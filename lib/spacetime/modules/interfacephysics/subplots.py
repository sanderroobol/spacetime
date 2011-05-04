import numpy

from ..generic.subplots import Subplot, XAxisHandling, YAxisHandling, DoubleMultiTrend


class CV(XAxisHandling, YAxisHandling, Subplot):
	x = y = None
	markers = None, None
	marker_points = None, None

	def set_data(self, x, y):
		self.x = next(x.iterchannels())
		self.y = next(y.iterchannels())

	def draw(self):
		if not self.x:
			return
		self.axes.plot(self.x.value, self.y.value, 'b-')
		self.plot_marker()

	def clear(self, quick=False):
		if not quick:
			if self.axes:
				del self.axes.lines[:]
			self.axes.relim()
		super(CV, self).clear(quick)

	def clear_marker(self):
		left, right = self.marker_points
		if left:
			self.axes.lines.remove(left)
		if right:
			self.axes.lines.remove(right)
		self.markers = self.marker_points = None, None

	def set_marker(self, left, right=None):
		self.markers = left, right
		if self.x:
			self.plot_marker()
		return self.clear_marker

	def plot_marker(self):
		left, right = self.markers

		if left is None:
			return

		index_left = numpy.searchsorted(self.x.time, left, 'left')
		if index_left == self.x.time.size:
			index_left -= 1

		left_point = self.axes.plot([self.x.value[index_left]], [self.y.value[index_left]], 'go')[0]
		if right is None:
			self.marker_points = left_point, None
		else:
			index_right = numpy.searchsorted(self.x.time, right, 'right')
			if index_right == self.x.time.size:
				index_right -= 1
			right_point = self.axes.plot([self.x.value[index_right]], [self.y.value[index_right]], 'ro')[0]
			self.marker_points = left_point, right_point


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
