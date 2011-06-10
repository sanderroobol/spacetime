from enthought.traits.api import *
from enthought.traits.ui.api import *

from ..generic.panels import DoubleTimeTrendPanel
from ..generic.datasources import CSV
from ..lpmcamera.panels import CameraTrendPanel
from ..lpmcamera.datasources import Camera as CameraDataSource
from ..lpmgascabinet import subplots as lpmsubplots
from ...gui import support

from . import subplots
from . import datasources


class TPDirkPanel(DoubleTimeTrendPanel):
	id = 'tpdirk'
	label = 'TPDirk'
	desc = 'Simple temperature/pressure readout for Dirk and the VT STM.'

	plotfactory = subplots.TPDirk
	datafactory = datasources.TPDirk
	filter = 'Dirk\'s ASCII files (*.txt)', '*.txt'

	def __init__(self, *args, **kwargs):
		super(TPDirkPanel, self).__init__(*args, **kwargs)
		self.ylog = True

	@on_trait_change('filename, reload')
	def load_file(self):
		if self.filename:
			try:
				self.data = self.datafactory(self.filename)
			except:
				support.Message.file_open_failed(self.filename, parent=self.parent)
				self.filename = ''
				return
			self.plot.set_data(self.data)
			self.redraw()

	def traits_view(self):
		return support.PanelView(
			Group(
				Item('visible'),
				Item('filename', editor=support.FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
				Item('reload', show_label=False),
				Item('legend'),
				show_border=True,
				label='General',
			),
			Group(
				Item('ylimits', style='custom', label='Left limits'),
				Item('ylimits2', style='custom', label='Right limits'),
				show_border=True,
				label='Y axes'
			),
			Include('relativistic_group'),
		)


class OldGasCabinetPanel(DoubleTimeTrendPanel):
	id = 'prototypegascabinet'
	label = 'Prototype gas cabinet'
	desc = 'Reads the data of the ReactorSTM gas cabinet.'

	plotfactory = lpmsubplots.GasCabinet
	datafactory = datasources.OldGasCabinet
	filter = 'ASCII text files (*.txt)', '*.txt',


class ReactorEnvironmentPanel(DoubleTimeTrendPanel):
	id = 'reactorenvironment'
	label = 'Reactor Environment logger'
	desc = 'Reads the log of the pressure, temperature and heater control for the ReactorAFM.'

	datafactory = CSV.factory(time_type='labview', time_column='auto')
	filter = 'ASCII text files (*.txt)', '*.txt',
