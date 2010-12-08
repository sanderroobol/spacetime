from __future__ import division

from spacetime import datasources, subplots, filters, plot


if __name__ == '__main__':
	path = '/home/sander/promotie/Projects/20101001 CO oxidation/'

	gcdata = datasources.OldGasCabinet(path + 'copy of 20101001 gas cabinet data.txt')

	p = plot.Plot.autopylab(

		subplots.Image(datasources.ChainedImage(
				datasources.Camera(path + '101001_PdAl2O3_CO_O2_HighT.raw').selectchannel(0),
				datasources.Camera(path + '101001_PdAl2O3_CO_O2_HighT_2.raw').selectchannel(0),
		).apply_filter(filters.BGSubtractLineByLine, filters.ClipStdDev(4))),

		subplots.QMS(
				datasources.QMS(path + '20101001 190122 SEM Airdemo MID.asc').selectchannels(
					lambda d: d.mass in (28, 32, 44)
				)
		),

		subplots.GasCabinet(
				gcdata.selectchannels(
					lambda d: d.controller in ('MFC CO', 'MFC O2') and d.parameter in ('measure', 'set point')
				),
				gcdata.selectchannels(
					lambda d: d.controller == 'BPC1' and d.parameter in ('measure', 'set point')
				),
		)

	)
