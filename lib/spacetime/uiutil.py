import os.path, sys, traceback

from enthought.traits.api import *
from enthought.traits.ui.api import *

import enthought.traits.ui.basic_editor_factory
import enthought.traits.ui.wx.file_editor
import wx

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


class ImprovedSimpleFileEditorImplementation(enthought.traits.ui.wx.file_editor.SimpleEditor):
	# code borrowed from enthought.traits.ui.wx.file_editor.SimpleEditor
	# slightly modified to make the dialog remember the directory

	def _create_file_dialog ( self ):
		""" Creates the correct type of file dialog.
		"""
		if len( self.factory.filter ) > 0:
			wildcard = '|'.join( self.factory.filter[:] )
		else:
			wildcard = 'All Files (*.*)|*.*'

		if self.factory.dialog_style == 'save':
			style = wx.FD_SAVE
		elif self.factory.dialog_style == 'open':
			style = wx.FD_OPEN
		else:
			style = ex.FD_DEFAULT_STYLE

		dlg = wx.FileDialog( self.control,
		                     message  = 'Select a File',
		                     wildcard = wildcard,
		                     style=style)

		dlg.SetPath( self._get_value() ) # this was dlg.SetFilename()

		return dlg


class ImprovedSimpleFileEditor(enthought.traits.ui.basic_editor_factory.BasicEditorFactory, FileEditor):
	klass = ImprovedSimpleFileEditorImplementation


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
		Item('min', enabled_when='not_auto'),
		Item('max', enabled_when='not_auto'),
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
		Item('min', enabled_when='not_auto'),
		Item('max', enabled_when='not_auto'),
		Item('scale'),
		show_labels=False,
	))
