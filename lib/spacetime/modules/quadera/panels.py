from ..generic.panels import TimeTrendPanel

from . import subplots, datasources


class QMSPanel(TimeTrendPanel):
	id = 'quaderaqms'
	label = 'QMS'
	desc = 'Reads ASCII exported Quadera files containing data from a Pfeiffer PrismaPlus quadrupole mass spectrometer.'

	datafactory = datasources.QMS
	plotfactory = subplots.QMS
	filter = 'Quadera ASCII files (*.asc)', '*.asc'

	def __init__(self, *args, **kwargs):
		super(QMSPanel, self).__init__(*args, **kwargs)
		self.ylog = True
