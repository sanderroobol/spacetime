from enthought.traits.api import *
from enthought.traits.ui.api import *

from ..generic.panels import TimeTrendPanel
from ... import gui

from . import subplots, datasources


class QMSPanel(TimeTrendPanel):
	id = 'quaderaqms'
	label = 'QMS'
	desc = 'Reads ASCII exported Quadera files containing data from a Pfeiffer PrismaPlus quadrupole mass spectrometer.'

	normalize_channel = Property(depends_on='channels')
	normalize_channel_selected = List(['Disable'])
	normalize_factor = Float(1.)

	datafactory = datasources.QMS
	plotfactory = subplots.QMS
	filter = 'Quadera ASCII files (*.asc)', '*.asc'

	traits_saved = 'normalize_channel_selected', 'normalize_factor'

	def __init__(self, *args, **kwargs):
		super(QMSPanel, self).__init__(*args, **kwargs)
		self.ylog = True

	def _get_normalize_channel(self):
		return ['Disable'] + self.channels

	@on_trait_change('normalize_channel_selected, normalize_factor')
	def normalization_changed(self):
		if self.normalize_channel_selected == ['Disable']:
			self.plot.set_normalization(self.normalize_factor)
		else:
			self.plot.set_normalization(self.normalize_factor, self.data.selectchannels(lambda chan: chan.id in self.normalize_channel_selected))
		self.redraw()

	def traits_view(self):
		return gui.support.PanelView(
			self.get_general_view_group(),
			Group(
				Item('normalize_channel_selected', label='Channel', editor=CheckListEditor(name='normalize_channel')),
				Item('normalize_factor', label='Factor', editor=gui.support.FloatEditor()),
				show_border=True,
				label='Normalization',
			),
			Include('left_yaxis_group'),
			Include('relativistic_group'),
		)
