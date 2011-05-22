import itertools
import numpy

from ..generic.subplots import DoubleMultiTrend, XAxisHandling

from ... import util

class CameraTrend(XAxisHandling, DoubleMultiTrend):
	xdata = None
	fft = False

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
		if (self.xdata or self.fft) and self.xlim_callback:
			self.axes.callbacks.connect('xlim_changed', self.xlim_callback)

	def get_xdata(self, chandata):
		if self.xdata:
			return self.xdata.value
		else:
			return super(CameraTrend, self).get_xdata(chandata)

	def draw(self):
		super(CameraTrend, self).draw()
		if self.xdata:
			self.parent.markers.redraw()

	def draw_marker(self, marker):
		if self.fft:
			return
		elif not self.xdata:
			return super(CameraTrend, self).draw_marker(marker)

		points = []

		index_left = numpy.searchsorted(self.xdata.time, marker.left, 'left')
		if index_left == self.xdata.time.size:
			index_left -= 1
		for ydata in itertools.chain(self.data.iterchannels(), self.secondarydata.iterchannels()):
			points.append(self.axes.plot([self.xdata.value[index_left]], [ydata.value[index_left]], 'go', zorder=1e9)[0])

		if marker.interval():
			index_right = numpy.searchsorted(self.xdata.time, marker.right, 'right')
			if index_right == self.xdata.time.size:
				index_right -= 1
			for ydata in itertools.chain(self.data.iterchannels(), self.secondarydata.iterchannels()):
				points.append(self.axes.plot([self.xdata.value[index_right]], [ydata.value[index_right]], 'ro', zorder=1e9)[0])

		marker.add_callback(lambda:	[self.axes.lines.remove(point) for point in points if point in self.axes.lines])
