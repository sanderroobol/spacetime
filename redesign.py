from __future__ import division

import pylab, matplotlib

from datasources import *
from subplots import *
from filters import *


class MainFigure(object):
	def __init__(self):
		self.plots = []

	def add_plot(self, plot):
		self.plots.append(plot)

	def build(self):
		self.figsetup()
		top = None
		for i, p in enumerate(self.plots):
			if top:
				axes = self.figure.add_subplot(len(self.plots), 1, i+1, sharex=top)
			else:
				top = axes = self.figure.add_subplot(len(self.plots), 1, i+1)
			try:
				if p.secondarydata: # FIXME: this is not really nice
					p.secondaryaxes = axes.twinx()
					p.secondaryaxes.xaxis_date()
			except AttributeError:
				pass
			if i + 1 != len(self.plots):
				self.hide_xticklabels(axes)
			p.build(axes)
			axes.xaxis_date()
		self.reformat_xaxis()

	def reformat_xaxis(self):
		self.figure.axes[-1].xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H:%M:%S'))

	@staticmethod
	def hide_xticklabels(ax):
		for label in ax.get_xticklabels():
			label.set_visible(False)

	def figinit(self, size=(14,8)):
		self.figure = matplotlib.figure.Figure(figsize=size)

	def figsetup(self, size=(14,8), legend=0):
		self.figinit(size)

		width, height = size
		def wabs2rel(x): return x / width
		def habs2rel(x): return x / height

		lrborder = .75
		tbborder = .45
		hspace = .2
		wspace = .2
		
		self.figure.subplots_adjust(
				left=wabs2rel(lrborder),
				right=1-wabs2rel(lrborder + legend),
				top=1-habs2rel(tbborder),
				bottom=habs2rel(tbborder),
				hspace=habs2rel(hspace),
				wspace=wabs2rel(wspace),
		)


class MainFigurePylab(MainFigure):
	def figinit(self, size=(14,8)):
		self.figure = matplotlib.pyplot.figure(figsize=size)



if __name__ == '__main__':
	f = MainFigurePylab()

	f.add_plot(ImagePlot(ChainedImageData(
			#CameraData('../20101001 CO oxidation/101001_PdNPAl2O3_35nm_Vacuum_tip100930.raw').selectchannel(0),
			#CameraData('../20101001 CO oxidation/101001_PdNPAL2O3_H2_P_05bar_HighT.raw').selectchannel(0),
			CameraData('../../20101001 CO oxidation/101001_PdAl2O3_CO_O2_HighT.raw').selectchannel(0),
			CameraData('../../20101001 CO oxidation/101001_PdAl2O3_CO_O2_HighT_2.raw').selectchannel(0),
	).apply_filter(BGSubtractLineByLine, ClipStdDev(4))))

	f.add_plot(QMSPlot(
			QMSData('../../20101001 CO oxidation/20101001 190122 SEM Airdemo MID.asc').selectchannels(
				lambda d: d.mass in (28, 32, 44)
			)
	))

	gcdata = GasCabinetData('../../20101001 CO oxidation/copy of 20101001 gas cabinet data.txt')
	f.add_plot(MultiTrendPlot(
			gcdata.selectchannels(
				lambda d: d.controller in ('MFC CO', 'MFC O2') and d.parameter in ('measure', 'set point')
			),
			gcdata.selectchannels(
				lambda d: d.controller == 'BPC1' and d.parameter in ('measure', 'set point')
			),
			formatter=GasCabinetFormatter()
	))

	f.build()
	pylab.show()
