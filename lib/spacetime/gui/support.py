# This file is part of Spacetime.
#
# Copyright (C) 2010-2012 Leiden University.
# Written by Sander Roobol.
#
# Spacetime is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Spacetime is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os.path, sys, traceback
import datetime

import numpy

from .. import prefs, util

import enthought.traits.api as traits
import enthought.traits.ui.api as traitsui
from enthought.pyface.api import ImageResource

import enthought.traits.ui.basic_editor_factory
import enthought.traits.ui.wx.file_editor, enthought.traits.ui.wx.time_editor
import wx


ICON_PATH = [os.path.join(os.path.split(os.path.dirname(__file__))[0], 'icons')]
def GetIcon(id):
	return ImageResource(id, search_path=ICON_PATH)


class Message(traits.HasTraits):
	message = traits.Str
	desc = traits.Str
	bt = traits.Str
	title = traits.Str
	buttons = traits.List([traitsui.OKButton])

	def traits_view(self):
		items = [
			traitsui.Item('message', emphasized=True, style='readonly'),
			traitsui.Item('desc', style='readonly', editor=traitsui.TextEditor(multi_line=True)),
		]
		if self.bt:
			items.append(traitsui.Item('bt', style='custom', width=500, height=200))
		return traitsui.View(
			traitsui.Group(
				*items, 
				show_labels=False,
				padding=5
			),
			title=self.title,
			buttons=self.buttons,
			kind='modal',
		)

	@classmethod
	def show(klass, parent=None, **kwargs):
		return klass(**kwargs).edit_traits(parent=parent).result
	
	@classmethod
	def exception(klass, message, desc='', title='Exception occured', parent=None):
		return klass.show(message=message, desc=desc, title=title, bt=traceback.format_exc(sys.exc_info()[2]), parent=parent)

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
			dlg.Directory = self.context_object.context.prefs.get_path(self.context_object.id)

		return dlg

	@staticmethod
	def get_path_to_remember(dlg):
		return dlg.Directory

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
				self.context_object.context.prefs.set_path(self.context_object.id, self.get_path_to_remember(dlg))
				if self.factory.truncate_ext:
					file_name = os.path.splitext( file_name )[0]

				self.value = file_name
				self.update_editor()


class FileEditor(enthought.traits.ui.basic_editor_factory.BasicEditorFactory, traitsui.FileEditor):
	klass = FileEditorImplementation


class DirectoryEditorImplementation(FileEditorImplementation):
	# also borrowed from enthought.traits.ui.wx.directory_editor.SimpleEditor and improved

	def _create_file_dialog ( self ):
		""" Creates the correct type of file dialog.
		"""
		dlg = wx.DirDialog( self.control, message = 'Select a Directory' )
		path = self._file_name.GetValue()
		if path:
			dlg.Path = path
		else:
			dlg.Path = self.context_object.context.prefs.get_path(self.context_object.id)
		return dlg

	@staticmethod
	def get_path_to_remember(dlg):
		return dlg.Path


class DirectoryEditor(enthought.traits.ui.basic_editor_factory.BasicEditorFactory, traitsui.DirectoryEditor):
	klass = DirectoryEditorImplementation
	entries = 0	


class TimeEditorImplementation(enthought.traits.ui.wx.time_editor.SimpleEditor):
	def init(self, parent):
		# use 24 hour clock, update on enter and lost focus, not on any keystroke
		self.control = wx.lib.masked.TimeCtrl(parent, -1, style=wx.TE_PROCESS_TAB|wx.TE_PROCESS_ENTER, fmt24hr=True)
		wx.EVT_KILL_FOCUS(self.control, self.time_updated)
		wx.EVT_TEXT_ENTER(parent, self.control.GetId(), self.time_updated)


class TimeEditor(enthought.traits.ui.basic_editor_factory.BasicEditorFactory, traitsui.TimeEditor):
	klass = TimeEditorImplementation


def FloatEditor(**kwargs):
	return traitsui.TextEditor(auto_set=False, enter_set=True, evaluate=float, **kwargs)


class AxisLimits(traits.HasTraits):
	min = traits.Float(0)
	max = traits.Float(1)
	auto = traits.Bool(True)

	not_auto = traits.Property(depends_on='auto')
	auto_list = traits.Property(depends_on='auto')

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

	traits_view = traitsui.View(traitsui.HGroup(
		traitsui.Item('auto_list', style='custom', editor=traitsui.CheckListEditor(values=['Auto'])),
		traitsui.Item('min', enabled_when='not_auto', editor=FloatEditor()),
		traitsui.Item('max', enabled_when='not_auto', editor=FloatEditor()),
		show_labels=False,
	))


class LogAxisLimits(AxisLimits):
	scale = traits.Enum('linear', 'log')
	log = traits.Property(depends_on='scale')

	def _get_log(self):
		return self.scale == 'log'

	def _set_log(self, value):
		if value:
			self.scale = 'log'
		else:
			self.scale = 'linear'

	def __str__(self):
		return "({0:e}, {1:e}) {2} {3}".format(self.min, self.max, self.scale, 'auto' if self.auto else 'manual')

	traits_view = traitsui.View(traitsui.HGroup(
		traitsui.Item('auto_list', style='custom', editor=traitsui.CheckListEditor(values=['Auto'])),
		traitsui.Item('min', enabled_when='not_auto', editor=FloatEditor()),
		traitsui.Item('max', enabled_when='not_auto', editor=FloatEditor()),
		traitsui.Item('scale'),
		show_labels=False,
	))


class DateTimeSelector(traits.HasTraits):
	date = traits.Date(datetime.date.today())
	time = traits.Time(datetime.time())
	datetime = traits.Property(depends_on='date, time')
	mpldt = traits.Property(depends_on='datetime')
	usecs = traits.Property(traits.Int, depends_on='time')

	@traits.cached_property
	def _get_datetime(self):
		return util.localtz.localize(datetime.datetime.combine(self.date, self.time))

	def _set_datetime(self, dt):
		self.date = dt.date()
		self.time = dt.time()

	@traits.cached_property
	def _get_mpldt(self):
		return util.mpldtfromdatetime(self.datetime)

	def _set_mpldt(self, f):
		self.datetime = util.datetimefrommpldt(f, tz=util.localtz)

	@traits.cached_property
	def _get_usecs(self):
		return self.time.microsecond

	def _set_usecs(self, usecs):
		self.time = datetime.time(hour=self.time.hour, minute=self.time.minute, second=self.time.second, microsecond=usecs)

	def __str__(self):
		return self.datetime.strftime('%Y-%m-%d %H:%M:%S.%f')

	traits_view = traitsui.View(
		traitsui.HGroup(
			traitsui.Item('time', editor=traitsui.TimeEditor()),
			traitsui.Item('date'),
			show_labels=False,
	))

	precision_view = traitsui.View(
		traitsui.VGroup(
			traitsui.Item('date'),
			traitsui.Item('time', editor=traitsui.TimeEditor()),
			traitsui.Item('usecs', label='Microseconds', editor=traitsui.RangeEditor(low=0, high=999999))
	))


class DateTimeLimits(traits.HasTraits):
	min = traits.Instance(DateTimeSelector, args=())
	max = traits.Instance(DateTimeSelector, args=())	
	min_mpldt = traits.DelegatesTo('min', 'mpldt')
	max_mpldt = traits.DelegatesTo('max', 'mpldt')
	auto = traits.Bool(True)
	not_auto = traits.Property(depends_on='auto')

	def _get_not_auto(self):
		return not self.auto

	traits_view = traitsui.View(
		traitsui.Item('auto', label='Auto'),
		traitsui.Item('min', label='Min', style='custom', enabled_when='not_auto'),
		traitsui.Item('max', label='Max', style='custom', enabled_when='not_auto'),
	)


class UtilityWindow(traits.HasTraits):
	context = traits.Instance(traits.HasTraits)

	def run(self):
		return self.edit_traits(parent=self.context.uiparent)

	@classmethod
	def run_static(cls, context):
		return cls(context=context).run()


class PersistantGeometryWindow(UtilityWindow):
	prefs_id = None

	def edit_traits(self, *args, **kwargs):
		ui = super(PersistantGeometryWindow, self).edit_traits(*args, **kwargs)
		if self.prefs_id:
			self.context.prefs.restore_window(self.prefs_id, ui)
		return ui


class PersistantGeometryHandler(traitsui.Handler):
	def close(self, info, is_ok=None):
		window = info.ui.context['object']
		if window.prefs_id:
			window.context.prefs.save_window(window.prefs_id, info.ui)
		return True


def PanelView(*args, **kwargs):
	handler = kwargs.pop('handler', None)
	return traitsui.View(traitsui.Group(*args, layout='normal', scrollable=True, **kwargs), handler=handler)


def EnumMapping(items):
	pad = int(numpy.ceil(numpy.log10(len(items))))
	out = {}
	for n, item in enumerate(items):
		try:
			iter(item)
			if isinstance(item, basestring):
				raise TypeError
		except TypeError:
			key = value = item
		else:
			key, value = item
		out[key] = "{0:0{pad}}:{1}".format(n, value, pad=pad)
	return out


class DummyProgressDialog(object):
	def noop(self, *args, **kwargs):
		pass
	
	open = noop
	update = noop
	close = noop

	min = None
	max = None
