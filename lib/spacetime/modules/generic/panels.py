from enthought.traits.api import *
from enthought.traits.ui.api import *
import wx

import logging
logger = logging.getLogger(__name__)

from ... import prefs, gui

from . import subplots
from . import datasources


class Tab(HasTraits):
	pass


class TraitsSavedMeta(HasTraits.__metaclass__):
	def __new__(mcs, name, bases, dict):
		if 'traits_saved' not in dict:
			dict['traits_saved'] = ()
		for base in bases:
			if 'traits_saved' in base.__dict__:
				dict['traits_saved'] = tuple(i for i in base.__dict__['traits_saved'] if 'traits_not_saved' not in dict or i not in dict['traits_not_saved']) + dict['traits_saved']
		return HasTraits.__metaclass__.__new__(mcs, name, bases, dict)


class SerializableTab(Tab):
	__metaclass__ = TraitsSavedMeta
	drawmgr = Instance(gui.figure.DrawManager)

	def _delayed_from_serialized(self, src):
		with self.drawmgr.hold():
			# trait_set has to be called separately for each trait to respect the ordering of traits_saved
			for id in self.traits_saved:
				if id in src:
					try: 
						self.trait_set(**dict(((id, src[id]),)))
					except:
						gui.support.Message.exception(title='Warning', message='Warning: incompatible project file', desc='Could not restore property "{0}" for graph "{1}". This graph might not be completely functional.'.format(id, self.label))
				else:
					gui.support.Message.show(title='Warning', message='Warning: incompatible project file', desc='Ignoring unknown property "{0}" for graph "{1}". This graph might not be completely functional.'.format(id, self.label))
  

	def from_serialized(self, src):
		if hasattr(self, 'traits_saved'):
			wx.CallAfter(lambda: self._delayed_from_serialized(src))

	def get_serialized(self):
		if hasattr(self, 'traits_saved'):
			return dict((id, getattr(self, id)) for id in self.traits_saved)
		else:
			return dict()


class SubplotPanel(SerializableTab):
	# required attributes: id, label
	desc = '' # not required
	filename = File
	reload = Button
	simultaneity_offset = Float(0.)
	time_dilation_factor = Float(1.)

	plot = Instance(subplots.Subplot)
	visible = Bool(True)
	number = 0

	autoscale = Callable
	prefs = prefs.Storage
	parent = Any

	# Magic attribute with "class level" "extension inheritance". Does this make any sense?
	# It means that when you derive a class from this class, you only have to
	# specify the attributes that are "new" in the derived class, any
	# attributed listed in one of the parent classes will be added
	# automatically.
	# Anyway, this is possible thanks to the TraitsSavedMeta metaclass.
	traits_saved = 'visible', 'filename', 'simultaneity_offset', 'time_dilation_factor'
	# traits_not_saved = ... can be used to specify parameters that should not be copied in a derived classes

	relativistic_group = Group(
		Item('simultaneity_offset', label='Simultaneity offset (s)', editor=gui.support.FloatEditor()),
		Item('time_dilation_factor', editor=RangeEditor(low=.999, high=1.001)),
		show_border=True,
		label='Relativistic corrections',
	)

	def __init__(self, *args, **kwargs):
		super(SubplotPanel, self).__init__(*args, **kwargs)
		self.__class__.number += 1
		if self.__class__.number != 1:
			self.label = '{0} {1}'.format(self.label, self.__class__.number)

	def redraw_figure(self):
		self.drawmgr.redraw_figure()

	def redraw(self):
		self.drawmgr.redraw_subgraph(lambda: (
			self.plot.clear(),
			self.plot.draw(),
			self.autoscale(self.plot),
		))

	def update(self):
		self.drawmgr.update_canvas()

	def _visible_changed(self):
		self.redraw_figure()

	@on_trait_change('simultaneity_offset, time_dilation_factor')
	def relativistics_changed(self):
		self.plot.adjust_time(self.simultaneity_offset, self.time_dilation_factor)
		self.redraw()

	def reset_autoscale(self):
		pass


class TimeTrendPanel(SubplotPanel):
	plotfactory = subplots.MultiTrend
	legend = Enum('auto', 'off', 'upper right', 'upper left', 'lower left', 'lower right', 'center left', 'center right', 'lower center', 'upper center', 'center')
	ylimits = Instance(gui.support.LogAxisLimits, args=())
	yauto = DelegatesTo('ylimits', 'auto')
	ymin = DelegatesTo('ylimits', 'min')
	ymax = DelegatesTo('ylimits', 'max')
	ylog = DelegatesTo('ylimits', 'log')
	channels = List(Str)
	selected_primary_channels = List(Str)
	data = Instance(datasources.DataSource)

	traits_saved = 'legend', 'yauto', 'ymin', 'ymax', 'ylog', 'selected_primary_channels'

	def _plot_default(self):
		plot = self.plotfactory()
		plot.set_ylim_callback(self.ylim_callback)
		return plot

	def ylim_callback(self, ax):
		self.ymin, self.ymax = ax.get_ylim()
		logger.info('%s.ylim_callback: %s', self.__class__.__name__, self.ylimits)

	@on_trait_change('filename, reload')
	def load_file(self):
		if self.filename:
			try:
				self.data = self.datafactory(self.filename)
			except:
				gui.support.Message.file_open_failed(self.filename, parent=self.parent)
				self.filename = ''
				return
			self.channels = list(self.data.iterchannelnames())
			self.settings_changed()

	@on_trait_change('selected_primary_channels')
	def settings_changed(self):
		self.plot.set_data(self.data.selectchannels(lambda chan: chan.id in self.selected_primary_channels))
		self.redraw()

	@on_trait_change('ymin, ymax, yauto')
	def ylim_changed(self):
		logger.info('%s.ylim_changed: %s', self.__class__.__name__, self.ylimits)
		self.plot.set_ylim(self.ylimits.min, self.ylimits.max, self.ylimits.auto)
		self.update()

	def _ylog_changed(self):
		self.plot.set_ylog(self.ylog)
		self.update()

	def reset_autoscale(self):
		super(TimeTrendPanel, self).reset_autoscale()
		self.yauto = True

	def _legend_changed(self):
		if self.legend == 'off':
			legend = False
		elif self.legend == 'auto':
			legend = 'best'
		else:
			legend = self.legend
		self.plot.set_legend(legend)
		self.update()

	def get_general_view_group(self):
		return Group(
			Item('visible'),
			Item('filename', editor=gui.support.FileEditor(filter=list(self.filter) + ['All files', '*'], entries=0)),
			Item('reload', show_label=False),
			Item('legend'),
			show_border=True,
			label='General',
		)

	left_yaxis_group = Group(
		Item('channels', editor=ListStrEditor(editable=False, multi_select=True, selected='selected_primary_channels')),
		Item('ylimits', style='custom', label='Limits'),
		show_border=True,
		label='Left y-axis'
	)

	def traits_view(self):
		return gui.support.PanelView(
			self.get_general_view_group(),
			Include('left_yaxis_group'),
			Include('relativistic_group'),
		)


class DoubleTimeTrendPanel(TimeTrendPanel):
	plotfactory = subplots.DoubleMultiTrend
	selected_secondary_channels = List(Str)

	ylimits2 = Instance(gui.support.LogAxisLimits, args=())
	yauto2 = DelegatesTo('ylimits2', 'auto')
	ymin2 = DelegatesTo('ylimits2', 'min')
	ymax2 = DelegatesTo('ylimits2', 'max')
	ylog2 = DelegatesTo('ylimits2', 'log')

	traits_saved = 'selected_secondary_channels', 'yauto2', 'ymin2', 'ymax2', 'ylog2'

	def _plot_default(self):
		plot = self.plotfactory()
		plot.set_ylim_callback(self.ylim_callback)
		return plot

	def ylim_callback(self, ax):
		if ax is self.plot.axes:
			self.ymin, self.ymax = ax.get_ylim()
			logger.info('%s.ylim_callback primary: %s', self.__class__.__name__, self.ylimits)
		elif ax is self.plot.secondaryaxes:
			self.ymin2, self.ymax2 = ax.get_ylim()
			logger.info('%s.ylim_callback secondary: %s', self.__class__.__name__, self.ylimits2)

	@on_trait_change('ymin2, ymax2, yauto2')
	def ylim2_changed(self):
		logger.info('%s.ylim2_changed: %s', self.__class__.__name__, self.ylimits2)
		self.plot.set_ylim2(self.ylimits2.min, self.ylimits2.max, self.ylimits2.auto)
		self.update()

	def _ylog2_changed(self):
		self.plot.set_ylog2(self.ylog2)
		self.update()

	def reset_autoscale(self):
		super(DoubleTimeTrendPanel, self).reset_autoscale()
		self.yauto2 = True

	@on_trait_change('selected_primary_channels, selected_secondary_channels')
	def settings_changed(self):
		self.plot.set_data(
			self.data.selectchannels(lambda chan: chan.id in self.selected_primary_channels),
			self.data.selectchannels(lambda chan: chan.id in self.selected_secondary_channels),
		)
		self.redraw()

	right_yaxis_group = Group(
		Item('channels', editor=ListStrEditor(editable=False, multi_select=True, selected='selected_secondary_channels')),
		Item('ylimits2', style='custom', label='Limits'),
		show_border=True,
		label='Right y-axis'
	)

	def traits_view(self):
		return gui.support.PanelView(
			self.get_general_view_group(),
			Include('left_yaxis_group'),
			Include('right_yaxis_group'),
			Include('relativistic_group'),
		)


class XlimitsPanel(HasTraits):
	xlimits = Instance(gui.support.LogAxisLimits, args=())
	xauto = DelegatesTo('xlimits', 'auto')
	xmin = DelegatesTo('xlimits', 'min')
	xmax = DelegatesTo('xlimits', 'max')
	xlog = DelegatesTo('xlimits', 'log')

	traits_saved = 'xauto', 'xmin', 'xmax', 'xlog'

	@on_trait_change('xmin, xmax, xauto')
	def xlim_changed(self):
		logger.info('%s.xlim_changed: %s', self.__class__.__name__, self.xlimits)
		self.plot.set_xlim(self.xlimits.min, self.xlimits.max, self.xlimits.auto)
		self.update()

	def _xlog_changed(self):
		self.plot.set_xlog(self.xlog)
		self.update()

	def xlim_callback(self, ax):
		self.xmin, self.xmax = ax.get_xlim()
		logger.info('%s.xlim_callback: %s', self.__class__.__name__, self.xlimits)

	def reset_autoscale(self):
		self.xauto = True
