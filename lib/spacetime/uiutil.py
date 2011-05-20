import os.path, sys, traceback

from . import prefs

from enthought.traits.api import *
from enthought.traits.ui.api import *

import enthought.traits.ui.basic_editor_factory
import enthought.traits.ui.wx.file_editor, enthought.traits.ui.wx.time_editor
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
	def file_open_failed(klass, filename, parent=None):
		return klass.exception(message='Failed to open file', desc='{0}\nmight not be accessible or it is not in the correct format.'.format(filename), parent=parent)

	@classmethod
	def file_save_failed(klass, filename, parent=None):
		return klass.exception(message='Failed to save file', desc=filename, parent=parent)


class FileEditorImplementation(enthought.traits.ui.wx.file_editor.SimpleEditor):
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

		# modifications start here
		path = self._get_value()
		if path:
			dlg.Path = path
		else:
			dlg.Directory = self.context_object.prefs.get_path(self.context_object.id)

		return dlg

	def show_file_dialog ( self, event ):
		""" Displays the pop-up file dialog.
		"""
		if self.history is not None:
			self.popup = self._create_file_popup()
		else:
			dlg       = self._create_file_dialog()
			rc        = (dlg.ShowModal() == wx.ID_OK)
			file_name = os.path.abspath( dlg.GetPath() )
			dlg.Destroy()
			if rc:
				self.context_object.prefs.set_path(self.context_object.id, dlg.Directory)
				if self.factory.truncate_ext:
					file_name = os.path.splitext( file_name )[0]

				self.value = file_name
				self.update_editor()


class FileEditor(enthought.traits.ui.basic_editor_factory.BasicEditorFactory, FileEditor):
	klass = FileEditorImplementation


class TimeEditorImplementation(enthought.traits.ui.wx.time_editor.SimpleEditor):
	def init(self, parent):
		# use 24 hour clock, update on enter and lost focus, not on any keystroke
		self.control = wx.lib.masked.TimeCtrl(parent, -1, style=wx.TE_PROCESS_TAB|wx.TE_PROCESS_ENTER, fmt24hr=True)
		wx.EVT_KILL_FOCUS(self.control, self.time_updated)
		wx.EVT_TEXT_ENTER(parent, self.control.GetId(), self.time_updated)


class TimeEditor(enthought.traits.ui.basic_editor_factory.BasicEditorFactory, TimeEditor):
	klass = TimeEditorImplementation


def FloatEditor(**kwargs):
	return TextEditor(auto_set=False, enter_set=True, evaluate=float, **kwargs)


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

	def __str__(self):
		return "({0:e}, {1:e}) {2}".format(self.min, self.max, 'auto' if self.auto else 'manual')

	traits_view = View(HGroup(
		Item('auto_list', style='custom', editor=CheckListEditor(values=['Auto'])),
		Item('min', enabled_when='not_auto', editor=FloatEditor()),
		Item('max', enabled_when='not_auto', editor=FloatEditor()),
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

	def __str__(self):
		return "({0:e}, {1:e}) {2} {3}".format(self.min, self.max, self.scale, 'auto' if self.auto else 'manual')

	traits_view = View(HGroup(
		Item('auto_list', style='custom', editor=CheckListEditor(values=['Auto'])),
		Item('min', enabled_when='not_auto', editor=FloatEditor()),
		Item('max', enabled_when='not_auto', editor=FloatEditor()),
		Item('scale'),
		show_labels=False,
	))


class ContextManager(object):
	def __init__(self, context, enter, exit):
		self.context = context
		self.enter = enter
		self.exit = exit

	def __enter__(self):
		self.enter()

	def __exit__(self, exc_type, exc_value, traceback):
		self.exit(exc_type, exc_value, traceback)


class DrawManager(object):
	_hold = 0
	level = 0

	def __init__(self, redraw_figure, update_canvas):
		self._redraw_figure = redraw_figure
		self._update_canvas = update_canvas
		self.subgraphs = []

	def hold(self):
		return ContextManager(self, self.hold_manual, lambda x,y,z: self.release_manual())

	def hold_delayed(self):
		return ContextManager(self, self.hold_manual, lambda x,y,z: wx.CallAfter(self.release_manual))

	def hold_manual(self):
		self._hold += 1

	def release_manual(self):
		if self._hold == 1:
			if self.level & 5 == 5:
				self._redraw_figure()
				del self.subgraphs[:]
				self._update_canvas()
			elif self.level & 3 == 3:
				for cb in self.subgraphs:
					cb()
				self._update_canvas()
			elif self.level & 1:
				self._update_canvas()
			self.level = 0
		self._hold -= 1

	def redraw_figure(self):
		if self._hold:
			self.level |= 5
		else:
			self._redraw_figure()
			self._update_canvas()
		
	def redraw_subgraph(self, cb):
		if self._hold:
			self.level |= 3
			self.subgraphs.append(cb)
		else:
			cb()
			self._update_canvas()
	
	def update_canvas(self):
		if self._hold:
			self.level |= 1
		else:
			self._update_canvas()


class PersistantGeometry(HasTraits):
	prefs = Instance(prefs.Storage)
	prefs_id = None

	def edit_traits(self, *args, **kwargs):
		ui = super(PersistantGeometry, self).edit_traits(*args, **kwargs)
		if self.prefs_id:
			self.prefs.restore_window(self.prefs_id, ui)
		return ui


class PersistantGeometryHandler(Handler):
	def close(self, info, is_ok=None):
		window = info.ui.context['object']
		if window.prefs_id:
			window.prefs.save_window(window.prefs_id, info.ui)
		return True
