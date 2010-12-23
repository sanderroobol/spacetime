import sys, traceback

from enthought.traits.api import *
from enthought.traits.ui.api import *

class Message(HasTraits):
	message = Str
	desc = Str
	bt = Str
	bt_visible = Property(depends_on='bt')
	title = Str
	buttons = List

	def _get_bt_visible(self):
		return bool(self.bt)

	def traits_view(self):
		return View(
			Group(
				Item('message', emphasized=True, style='readonly'),
				Item('desc', style='readonly', editor=TextEditor(multi_line=True)),
				Item('bt', style='custom', width=500, height=200, visible_when='bt_visible'),
				show_labels=False,
				padding=5,
			),
			title=self.title,
			buttons=self.buttons,
			kind='modal',
		)

	@classmethod
	def exception(klass, message, desc='', title='Exception occured', parent=None):
		return klass(message=message, title=title, desc=desc, bt=traceback.format_exc(sys.exc_info()[2]), buttons=['OK']).edit_traits(parent=parent).result

	@classmethod
	def file_open_failed(klass, filename):
		return klass.exception(message='Failed to open file', desc='%s\nmight not be accessible or it is not in the correct format.' % filename)

	@classmethod
	def file_save_failed(klass, filename):
		return klass.exception(message='Failed to save file', desc=filename)


def FormattedFloatEditor():
	# FIXME: implement!!!
	return RangeEditor(mode='text')


class AxisLimits(HasTraits):
	min = Float(0)
	max = Float(1)
	auto = Bool(True)

	not_auto = Property(depends_on='auto')
	auto_list = Property(depends_on='auto')

	def _get_not_auto(self):
		return not self.auto

	def _get_auto_list(self):
		if self.auto:
			return ['Auto']
		else:
			return []

	def _set_auto_list(self, value):
		self.auto = bool(value)


	traits_view = View(HGroup(
		Item('auto_list', style='custom', editor=CheckListEditor(values=['Auto'])),
		Item('min', enabled_when='not_auto', editor=FormattedFloatEditor()),
		Item('max', enabled_when='not_auto', editor=FormattedFloatEditor()),
		show_labels=False,
	))


class LogAxisLimits(AxisLimits):
	scale = Enum('linear', 'log')
	log = Property(depends_on='scale')

	def _get_log(self):
		return self.scale == 'log'

	def _set_log(self, value):
		if value:
			self.scale = 'log'
		else:
			self.scale = 'linear'

	traits_view = View(HGroup(
		Item('auto_list', style='custom', editor=CheckListEditor(values=['Auto'])),
		Item('min', enabled_when='not_auto', editor=FormattedFloatEditor()),
		Item('max', enabled_when='not_auto', editor=FormattedFloatEditor()),
		Item('scale'),
		show_labels=False,
	))
