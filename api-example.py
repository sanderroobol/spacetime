from __future__ import division

import datasources
import subplots
import filters
import plot


if __name__ == '__main__':
	gcdata = datasources.GasCabinet('../../20101001 CO oxidation/copy of 20101001 gas cabinet data.txt')

	p = plot.Plot.autopylab(

		subplots.Image(datasources.ChainedImage(
				#datasources.Camera('../20101001 CO oxidation/101001_PdNPAl2O3_35nm_Vacuum_tip100930.raw').selectchannel(0),
				#datasources.Camera('../20101001 CO oxidation/101001_PdNPAL2O3_H2_P_05bar_HighT.raw').selectchannel(0),
				datasources.Camera('../../20101001 CO oxidation/101001_PdAl2O3_CO_O2_HighT.raw').selectchannel(0),
				datasources.Camera('../../20101001 CO oxidation/101001_PdAl2O3_CO_O2_HighT_2.raw').selectchannel(0),
		).apply_filter(filters.BGSubtractLineByLine, filters.ClipStdDev(4))),

		subplots.QMS(
				datasources.QMS('../../20101001 CO oxidation/20101001 190122 SEM Airdemo MID.asc').selectchannels(
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
