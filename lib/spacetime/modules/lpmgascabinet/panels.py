from enthought.traits.api import *

from ..generic.panels import DoubleTimeTrendPanel

from . import subplots, datasources

class GasCabinetPanel(DoubleTimeTrendPanel):
	id = 'lpmgascabinet'
	label = 'LPM Gas Cabinet'
	desc = 'Reads logs from LPM Gas Cabinet control software.'

	plotfactory = subplots.GasCabinet
	datafactory = datasources.GasCabinet
	filter = 'ASCII text files (*.txt)', '*.txt',

	@cached_property
	def _get_primary_channels(self):
		if self.data:
			time_columns = set(self.data.get_time_columns())
			return [label for (i, label) in enumerate(self.channels) if i not in time_columns]
		else:
			return []
