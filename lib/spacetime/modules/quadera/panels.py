from enthought.traits.api import *
from enthought.traits.ui.api import *

from ..generic.panels import TimeTrendPanel
from ... import gui

from . import subplots, datasources


class QuaderaPanel(TimeTrendPanel):
	normalize_channel = Str('none')
	normalize_channel_options = Property(depends_on='channels')
	normalize_factor = Float(1.)

	plotfactory = subplots.QMS
	filter = 'Quadera ASCII files (*.asc)', '*.asc'

	traits_saved = 'normalize_channel', 'normalize_factor'

	def __init__(self, *args, **kwargs):
		super(QuaderaPanel, self).__init__(*args, **kwargs)
		self.ylog = True

	@cached_property
	def _get_normalize_channel_options(self):
		return gui.support.EnumMapping([('none', 'Disable')] + self.channels)

	@on_trait_change('normalize_channel, normalize_factor')
	def normalization_changed(self):
		if self.normalize_channel == 'none':
			self.plot.set_normalization(self.normalize_factor)
		else:
			self.plot.set_normalization(self.normalize_factor, self.data.selectchannels(lambda chan: chan.id == self.normalize_channel))
		self.redraw()

	def traits_view(self):
		return gui.support.PanelView(
			self.get_general_view_group(),
			Group(
				Item('normalize_channel', label='Channel', editor=EnumEditor(name='normalize_channel_options')),
				Item('normalize_factor', label='Factor', editor=gui.support.FloatEditor()),
				show_border=True,
				label='Normalization',
			),
			Include('left_yaxis_group'),
			Include('relativistic_group'),
		)


class QuaderaMIDPanel(QuaderaPanel):
	id = 'quadera_mid'
	label = 'Quadera MID'
	desc = 'Reads ASCII exported Quadera MID projects from a Pfeiffer PrismaPlus quadrupole mass spectrometer.'

	datafactory = datasources.QuaderaMID


class QuaderaScanPanel(QuaderaPanel):
	id = 'quadera_scan'
	label = 'Quadera Scan'
	desc = 'Reads ASCII exported Quadera Scan projects from a Pfeiffer PrismaPlus quadrupole mass spectrometer.'

	datafactory = datasources.QuaderaScan


