from ..generic.panels import DoubleTimeTrendPanel

from . import subplots, datasources

class GasCabinetPanel(DoubleTimeTrendPanel):
	id = 'lpmgascabinet'
	label = 'LPM gas cabinet'

	plotfactory = subplots.GasCabinet
	datafactory = datasources.GasCabinet
	filter = 'ASCII text files (*.txt)', '*.txt',
