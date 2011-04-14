from enthought.traits.api import *
from enthought.traits.ui.api import *

from ..generic.panels import DoubleTimeTrendPanel, PanelView
from ..lpmcamera.panels import CameraTrendPanel
from ..lpmgascabinet import subplots as lpmsubplots
from ... import uiutil

from . import subplots
from . import datasources


class CVPanel(CameraTrendPanel):
	tablabel = 'Cyclic voltammetry'
	plotfactory = subplots.CV
	voltage_channel = Int(0)
	current_channel = Int(0)
	channelcount = Int(0)

	traits_not_saved = 'selected_primary_channels', 'selected_secondary_channels'
	traits_saved = 'voltage_channel', 'current_channel'

	@on_trait_change('filename')
	def load_file(self):
		if self.filename:
			try:
				self.data = datasources.Camera(self.filename)
			except:
				uiutil.Message.file_open_failed(self.filename, parent=self.parent)
				self.filename = ''
				return
			self.channelcount = self.data.getchannelcount() - 1
			self.framecount = self.data.getframecount() - 1
			self.lastframe = min(self.framecount, 25)
			self.settings_changed()

	def _firstframe_changed(self):
		if self.firstframe > self.lastframe:
			self.lastframe = self.firstframe
			# settings_changed() will be triggered because lastframe changes
		else:
			self.settings_changed()

	@on_trait_change('averaging, lastframe, stepframe, voltage_channel, current_channel')
	def settings_changed(self):
		if not self.data:
			return
		# FIXME: implement a smarter first/last frame selection, don't redraw everything
		data = self.data.selectframes(self.firstframe, self.lastframe, self.stepframe)
		self.data.averaging = self.averaging
		self.plot.set_data(
			data.selectchannels(lambda chan: chan.id == str(self.voltage_channel)),
			data.selectchannels(lambda chan: chan.id == str(self.current_channel)),
		)
		self.redraw()

	traits_view = PanelView(
		Group(
			Item('visible'),
			Item('filename', editor=uiutil.FileEditor(filter=['Camera RAW files (*.raw)', '*.raw', 'All files', '*'], entries=0)),
			Item('firstframe', label='First frame', editor=RangeEditor(low=0, high_name='framecount', mode='spinner')),
			Item('lastframe', label='Last frame', editor=RangeEditor(low=0, high_name='framecount', mode='spinner')),
			Item('stepframe', label='Key frame mode'),
			Item('direction', editor=EnumEditor(values={1:'1:L2R', 2:'2:R2L'})), # FIXME: for trends, it should be possible to show both!
			Item('averaging', tooltip='Per-line averaging'),
			show_border=True,
			label='General',
		),
		Group(
			Item('voltage_channel', editor=RangeEditor(low=0, high_name='channelcount', mode='spinner')),
			Item('current_channel', editor=RangeEditor(low=0, high_name='channelcount', mode='spinner')),
			show_border=True,
			label='Channels',
		),
		Include('relativistic_group'),
	)


class TPDirkPanel(DoubleTimeTrendPanel):
	tablabel = 'TPDirk'
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
				uiutil.Message.file_open_failed(self.filename, parent=self.parent)
				self.filename = ''
				return
			self.plot.set_data(self.data)
			self.redraw()

	def traits_view(self):
		return PanelView(
			Group(
				Item('visible'),
				Item('filename', editor=uiutil.FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
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
	tablabel = 'Prototype gas cabinet'
	plotfactory = lpmsubplots.GasCabinet
	datafactory = datasources.OldGasCabinet
	filter = 'ASCII text files (*.txt)', '*.txt',


class ReactorEnvironmentPanel(DoubleTimeTrendPanel):
	tablabel = 'Reactor Environment logger'
	datafactory = datasources.ReactorEnvironment
	filter = 'ASCII text files (*.txt)', '*.txt',
