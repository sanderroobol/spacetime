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

from __future__ import division

# keep this import at top to ensure proper matplotlib backend selection
from .figure import MPLFigureEditor, DrawManager, CallbackLoopManager

from .. import plot, modules, version, prefs, util
from . import support, windows

from enthought.traits.api import *
from enthought.traits.ui.api import *
from enthought.pyface.api import ProgressDialog
import matplotlib.figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import wx
import json
import os
import itertools

import logging
logger = logging.getLogger(__name__)


class MainTab(modules.generic.panels.SerializableTab):
	version = Property()
	# the combination of an InstanceEditor with DelegatedTo traits and trait_set(trait_change_notify=False)
	# seems to be special: the GUI will be updated but no event handlers will be called
	xlimits = Instance(support.DateTimeLimits, args=())
	xauto = DelegatesTo('xlimits', 'auto')
	xmin_mpldt = DelegatesTo('xlimits', 'min_mpldt')
	xmax_mpldt = DelegatesTo('xlimits', 'max_mpldt')

	label = 'Main'
	status = Str('')

	traits_saved = 'version', 'xmin_mpldt', 'xmax_mpldt', 'xauto'

	def _get_version(self):
		return version.version

	def _set_version(self, version):
		pass

	def xlim_callback(self, ax):
		with self.context.callbacks.avoid(self.xlimits):
			self.xmin_mpldt, self.xmax_mpldt = ax.get_xlim()
		if not self.context.callbacks.is_avoiding(self.xlimits):
			self.xauto = False
		logger.info('%s.xlim_callback: (%s, %s) %s', self.__class__.__name__, self.xlimits.min, self.xlimits.max, 'auto' if self.xauto else 'manual')

	@on_trait_change('xmin_mpldt, xmax_mpldt, xauto')
	@CallbackLoopManager.decorator('xlimits')
	def xlim_changed(self):
		logger.info('%s.xlim_changed: (%s, %s) %s', self.__class__.__name__, self.xlimits.min, self.xlimits.max, 'auto' if self.xauto else 'manual')
		self.xmin_mpldt, self.xmax_mpldt = self.context.plot.set_shared_xlim(self.xmin_mpldt, self.xmax_mpldt, self.xauto)
		self.context.canvas.redraw()

	def reset_autoscale(self):
		self.xauto = True

	traits_view = View(Group(
		Group(
			Item('xlimits', style='custom'),
			show_labels=False,
			label='Time axis limits',
			show_border=True,
		),
		layout='normal',
	))


class MainWindowHandler(Handler):
	def do_new(self, info):
		if not self.close_project(info):
			return False
		mainwindow = info.ui.context['object']
		mainwindow.new_project()
		mainwindow.update_title()
		return True

	def close_project(self, info):
		mainwindow = info.ui.context['object']

		if mainwindow.project_modified:
			dlg = wx.MessageDialog(info.ui.control, 'Save current project?', style=wx.YES_NO | wx.CANCEL | wx.ICON_EXCLAMATION)
			ret = dlg.ShowModal()
			if ret == wx.ID_CANCEL:
				return False
			elif ret == wx.ID_YES:
				return self.do_save(info)
		return True

	def close(self, info, is_ok=None):
		mainwindow = info.ui.context['object']

		if not self.close_project(info):
			return False

		if mainwindow.figurewindowui:
			mainwindow.figurewindowui.control.Close()

		mainwindow.prefs.save_window('main', mainwindow.ui)
		mainwindow.prefs.close()

		return True
		
	def do_open(self, info, path=None):
		mainwindow = info.ui.context['object']
		if not self.close_project(info):
			return
		if path is None:
			dlg = wx.FileDialog(info.ui.control, style=wx.FD_OPEN, wildcard='Spacetime Project files (*.spacetime)|*.spacetime')
			dlg.Directory = mainwindow.prefs.get_path('project')
			if dlg.ShowModal() != wx.ID_OK:
				return
			path = dlg.Path
			mainwindow.prefs.set_path('project', dlg.Directory)
		mainwindow.new_project()
		try:
			mainwindow.open_project(path)
		except:
			support.Message.file_open_failed(path, parent=info.ui.control)
		mainwindow.prefs.add_recent('project', path)
		mainwindow.rebuild_recent_menu()
		mainwindow.update_title()
		mainwindow.context.canvas.rebuild()

	# you got to be f*cking kidding me...
	def do_open_recent_0(self, info):
		return self.do_open_recent(info, 0)
	def do_open_recent_1(self, info):
		return self.do_open_recent(info, 1)
	def do_open_recent_2(self, info):
		return self.do_open_recent(info, 2)
	def do_open_recent_3(self, info):
		return self.do_open_recent(info, 3)
	def do_open_recent_4(self, info):
		return self.do_open_recent(info, 4)
	def do_open_recent_5(self, info):
		return self.do_open_recent(info, 5)
	def do_open_recent_6(self, info):
		return self.do_open_recent(info, 6)
	def do_open_recent_7(self, info):
		return self.do_open_recent(info, 7)
	def do_open_recent_8(self, info):
		return self.do_open_recent(info, 8)
	def do_open_recent_9(self, info):
		return self.do_open_recent(info, 9)

	def do_open_recent(self, info, i):
		mainwindow = info.ui.context['object']
		return self.do_open(info, mainwindow.recent_paths[i])

	def do_save(self, info):
		mainwindow = info.ui.context['object']
		if mainwindow.project_path:
			if mainwindow.save_project(mainwindow.project_path):
				return True
			return False
		else:
			return self.do_save_as(info)

	def do_save_as(self, info):
		mainwindow = info.ui.context['object']
		dlg = wx.FileDialog(info.ui.control, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT, wildcard='Spacetime Project files (*.spacetime)|*.spacetime')
		dlg.Directory = mainwindow.prefs.get_path('project')
		if dlg.ShowModal() != wx.ID_OK:
			return False
		mainwindow.prefs.set_path('project', dlg.Directory)
		filename, path = dlg.Filename, dlg.Path
		if not path.endswith('.spacetime'):
			path += '.spacetime'
			filename += '.spacetime'
		try:
			if mainwindow.save_project(path):
				mainwindow.prefs.add_recent('project', path)
				mainwindow.rebuild_recent_menu()
				mainwindow.update_title()
				return True
		except:
			support.Message.file_open_failed(path, parent=info.ui.control)
		return False

	def do_add(self, info):
		windows.PanelSelector.run_static(info.ui.context['object'].context)

	def do_python(self, info):
		windows.PythonWindow.run_static(info.ui.context['object'].context)

	def do_about(self, info):
		windows.AboutWindow.run_static(info.ui.context['object'].context)

	def do_export(self, info):
		context = info.ui.context['object'].context
		mainwindow = context.app
		
		exportdialog = windows.ExportDialog(context=context)
		if not exportdialog.run().result:
			return

		dlg = wx.FileDialog(
			info.ui.control,
			"Export",
			context.prefs.get_path('export'),
			"image." + exportdialog.extension,
			exportdialog.wxfilter + "|All files (*.*)|*.*",
			wx.SAVE|wx.OVERWRITE_PROMPT
		)

		if dlg.ShowModal() == wx.ID_OK:
			context.prefs.set_path('export', dlg.GetDirectory())
			path = dlg.GetPath()
			try:
				newfig = matplotlib.figure.Figure(exportdialog.figsize, exportdialog.dpi)
				canvas = FigureCanvasAgg(newfig)
				context.plot.relocate(newfig)
				context.app.rebuild_figure()
				newfig.savefig(path, dpi=exportdialog.dpi, format=exportdialog.extension)
			except:
				support.Message.file_save_failed(path, parent=info.ui.control)
			finally:
				context.plot.relocate(context.app.figure)
				context.app.rebuild_figure()

	def do_movie(self, info):
		context = info.ui.context['object'].context
		
		moviedialog = windows.MovieDialog(context=context)
		try:
			if not moviedialog.run().result:
				return
		except RuntimeError as e:
			support.Message.show(message='Nothing to animate', desc=str(e))
			return

		dlg = wx.FileDialog(
			info.ui.control,
			"Save movie",
			context.prefs.get_path('movie'),
			"movie." + moviedialog.format,
			"*.{0}|*.{0}|All files (*.*)|*.*".format(moviedialog.format),
			wx.SAVE|wx.OVERWRITE_PROMPT
		)

		if dlg.ShowModal() != wx.ID_OK:
			return
		context.prefs.set_path('movie', dlg.GetDirectory())

		movie = None
		oldfig = context.plot.figure
		try:
			progress = ProgressDialog(title="Movie", message="Building movie", max=moviedialog.get_framecount()+2, can_cancel=True, parent=context.uiparent)
			progress.open()

			newfig = matplotlib.figure.Figure((moviedialog.frame_width / moviedialog.dpi, moviedialog.frame_height / moviedialog.dpi), moviedialog.dpi)
			canvas = FigureCanvasAgg(newfig)
			context.plot.relocate(newfig)
			movie = util.FFmpegEncode(
				dlg.GetPath(),
				moviedialog.format,
				moviedialog.codec,
				moviedialog.frame_rate,
				(moviedialog.frame_width, moviedialog.frame_height),
				moviedialog.kbpf * moviedialog.frame_rate * 1024,
				moviedialog.ffmpeg_options.split(),
			)
			thread, queue = movie.spawnstdoutthread()
			progress.update(1)

			# FIXME disable drawmanager? relocate? hold?
			iters = tuple(i() for i in moviedialog.get_animate_functions())
			for frameno, void in enumerate(itertools.izip_longest(*iters)):
				context.canvas.rebuild()
				newfig.canvas.draw()
				movie.writeframe(newfig.canvas.tostring_rgb())
				(cont, skip) = progress.update(frameno+2)
				if not cont or skip:
					movie.abort()
					try:
						os.unlink(dlg.GetPath())
					except:
						pass
					progress.close()
					break
			else:
				movie.eof() # closes stdin
				thread.join() # blocks until stdout has been read
				stdout = []
				while not queue.empty():
					stdout.append(queue.get_nowait())
				stdout = ''.join(stdout)
				movie.close()
				progress.update(progress.max)
				support.Message.show(parent=context.uiparent, title='Movie complete', message='Movie complete', desc='The movie successfully been generated.\nFor debugging purposes, the full FFmpeg output can be found below.', bt=stdout)
		except:
			if movie:
				movie.abort()
			thread.join()
			try:
				os.unlink(dlg.GetPath())
			except:
				pass	
			support.Message.exception(message='Movie export failed', desc='Something went wrong while exporting the movie. Detailed debugging information can be found below.')
		finally:
			context.plot.relocate(oldfig)
			context.canvas.rebuild()

	def do_fit(self, info):
		mainwindow = info.ui.context['object']
		with mainwindow.drawmgr.hold():
			for tab in mainwindow.tabs:
				tab.reset_autoscale()

	def do_zoom(self, info):
		mainwindow = info.ui.context['object']
		mainwindow.plot.figure.toolbar.zoom()
		mainwindow.zoom_checked = not mainwindow.zoom_checked
		mainwindow.pan_checked = False

	def do_pan(self, info):
		mainwindow = info.ui.context['object']
		mainwindow.plot.figure.toolbar.pan()
		mainwindow.pan_checked = not mainwindow.pan_checked
		mainwindow.zoom_checked = False

	def do_presentation_mode(self, info):
		mainwindow = info.ui.context['object']
		mainwindow.toggle_presentation_mode()

	def do_fullscreen(self, info):
		info.ui.context['object'].toggle_fullscreen()

	def do_graphmanager(self, info):
		windows.GraphManager.run_static(info.ui.context['object'].context)



class Frame(HasTraits):
	pass


class SplitFrame(Frame):
	app = Instance(HasTraits)
	figure = Instance(matplotlib.figure.Figure, args=())
	tabs = DelegatesTo('app')
	status = DelegatesTo('app')

	traits_view = View(
		HSplit(
			Item('figure', width=600, editor=MPLFigureEditor(status='status'), dock='vertical'),
			Item('tabs', style='custom', editor=ListEditor(use_notebook=True, page_name='.label')),
			show_labels=False,
		)
	)


class SimpleFrame(Frame):
	app = Instance(HasTraits)
	tabs = DelegatesTo('app')

	traits_view = View(
		Group(
			Item('tabs', style='custom', editor=ListEditor(use_notebook=True, page_name='.label')),
			show_labels=False,
		)
	)


class Context(HasTraits):
	app = Instance(HasTraits)
#	document = Instance(Any)
	plot = Instance(plot.Plot)
	canvas = Instance(DrawManager)
	callbacks = Instance(CallbackLoopManager, args=())
	prefs = Instance(prefs.Storage)
	uiparent = Any


class App(HasTraits):
	plot = Instance(plot.Plot)
	maintab = Instance(MainTab)
	status = DelegatesTo('maintab')
	drawmgr = Instance(DrawManager)
	moduleloader = Instance(modules.Loader, args=())
	frame = Instance(Frame)
	figurewindowui = None
	figure_fullscreen = Bool(False)
	prefs = Instance(prefs.Storage, args=())

	context = Instance(Context)

	pan_checked = Bool(False)
	zoom_checked = Bool(False)
	presentation_mode = Bool(False)

	project_path = Str()
	project_filename = Property(depends_on='project_path')
	_tabs_modified = Bool(False)
	project_modified = Property(depends_on='_tabs_modified, tabs._modified')

	tabs = List(Instance(modules.generic.panels.Tab))

	def clone_traits(self, *args, **kwargs):
		# FIXME: Somehow clone_traits() gets called to make (shallow) copies of
		# App instances. I don't know why this happens. Unfortunately, some
		# attributes do not get copied properly, in particular self.ui, but the
		# same applies to the context attribute of the Panels. To work around
		# the problem, just don't copy anymore. This doesn't seem to have any
		# negative side effects...
		return self

	def on_figure_resize(self, event):
		logger.info('on_figure_resize called')
		self.plot.setup_margins()
		self.context.canvas.redraw()

	def redraw_canvas(self):
		# make a closure on self so figure.canvas can be changed in the meantime
		wx.CallAfter(lambda: self.context.plot.figure.canvas.draw())

	def get_new_tab(self, klass):
		return klass(context=self.context)

	def add_tab(self, klass, serialized_data=None):
		tab = self.get_new_tab(klass)
		if serialized_data is not None:
			tab.from_serialized(serialized_data)
		self.tabs.append(tab)

	def _context_default(self):
		return Context(app=self, canvas=self.drawmgr, prefs=self.prefs)

	def _maintab_default(self):
		return MainTab(context=self.context)

	def _drawmgr_default(self):
		return DrawManager(self.rebuild_figure, self.redraw_canvas)

	def _tabs_changed(self):
		self._tabs_modified = True
		self.context.canvas.rebuild()

	def _tabs_items_changed(self, event):
		with self.context.canvas.hold():
			for removed in event.removed:
				if isinstance(removed, MainTab):
					self.tabs.insert(0, removed)
				else:
					self._tabs_modified = True
					self.context.canvas.rebuild()
			if event.added:
				self._tabs_modified = True
				self.context.canvas.rebuild()

	def _tabs_default(self):
		return [self.maintab]

	@cached_property
	def _get_project_filename(self):
		if not self.project_path:
			return ''
		return os.path.basename(self.project_path)

	@cached_property
	def _get_project_modified(self):
		return self._tabs_modified or True in set(tab._modified for tab in self.tabs)

	def clear_project_modified(self):
		self._tabs_modified = False
		for tab in self.tabs:
			tab._modified = False

	def new_project(self):
		self.tabs = self._tabs_default()
		for klass in self.moduleloader.list_classes():
			klass.number = 0
		self.project_path = ''
		self.clear_project_modified()

	def open_project(self, path):
		with open(path, 'rb') as fp:
			if fp.read(15) != 'Spacetime\nJSON\n':
				raise ValueError('not a valid Spacetime project file')
			data = json.load(fp)
		with self.context.canvas.hold_delayed():
			self.tabs[0].from_serialized(data.pop(0)[1])
			# FIXME: check version number and emit warning
			for id, props in data:
				try:
					self.add_tab(self.moduleloader.get_class_by_id(id), props)
				except KeyError:
					support.Message.show(title='Warning', message='Warning: incompatible project file', desc='Ignoring unknown graph id "{0}". Project might not be completely functional.'.format(id))
			self.project_path = path
			wx.CallAfter(self.clear_project_modified)

	def save_project(self, path):
		data = [('general', self.tabs[0].get_serialized())]
		for tab in self.tabs:
			if isinstance(tab, modules.generic.panels.SubplotPanel):
				data.append((self.moduleloader.get_id_by_instance(tab), tab.get_serialized()))
		with open(path, 'wb') as fp:
			fp.write('Spacetime\nJSON\n')
			json.dump(data, fp)
		self.project_path = path
		self.clear_project_modified()
		return True

	@on_trait_change('project_modified')
	def update_title(self):
		if self.project_filename:
			self.ui.title = '{0} - {1}{2}'.format(version.name, self.project_filename, '*' if self.project_modified else '')
		else:
			self.ui.title = version.name

		if self.figurewindowui:
			self.figurewindowui.title = self.ui.title

	def rebuild_figure(self):
		self.plot.clear()
		[self.plot.add_subplot(tab.plot) for tab in self.tabs if isinstance(tab, modules.generic.panels.SubplotPanel) and tab.visible]
		self.plot.setup()
		self.plot.draw()
		with self.context.callbacks.general_blockade():
			self.plot.autoscale()

	def _connect_canvas_resize_event(self):
		self.context.plot.figure.canvas.mpl_connect('resize_event', self.on_figure_resize), 

	def _plot_default(self):
		p = plot.Plot(self.frame.figure)
		p.setup()
		wx.CallAfter(p.set_shared_xlim_callback, self.maintab.xlim_callback)
		wx.CallAfter(self._connect_canvas_resize_event)
		return p

	def _frame_default(self):
		return SplitFrame(app=self)

	def _close_presentation_mode(self):
		self.presentation_mode = False
		self.figurewindowui = None
		self.frame = SplitFrame(app=self)
		self.plot.relocate(self.frame.figure)
		self.context.canvas.rebuild()
		wx.CallAfter(self._connect_canvas_resize_event)

	def _open_presentation_mode(self):
		self.presentation_mode = True
		self.frame = SimpleFrame(app=self)
		fw = windows.FigureWindow(context=self.context, app=self)
		self.figurewindowui = fw.edit_traits()
		self.plot.relocate(fw.figure)
		self.context.canvas.rebuild()
		wx.CallAfter(self._connect_canvas_resize_event)
		wx.CallAfter(self.context.plot.figure.canvas.Bind, wx.EVT_KEY_DOWN, self.fullscreen_keyevent)

	def toggle_presentation_mode(self):
		if self.presentation_mode:
			self.figurewindowui.control.Close()
			self.figure_fullscreen = False
		else:
			self._open_presentation_mode()
			self.update_title()

	def toggle_fullscreen(self):
		self.figure_fullscreen = not self.figure_fullscreen
		self.figurewindowui.control.ShowFullScreen(self.figure_fullscreen, wx.FULLSCREEN_NOBORDER | wx.FULLSCREEN_NOCAPTION)
			
	def fullscreen_keyevent(self, event):
		if event.KeyCode == wx.WXK_F11 or (self.figure_fullscreen and event.KeyCode == wx.WXK_ESCAPE):
			self.toggle_fullscreen()

	def init_recent_menu(self):
		frame = self.ui.control
		file_menu = frame.MenuBar.Menus[0][0]
		self.recent_menu = file_menu.MenuItems[2].SubMenu
		self.recent_menu_items = [i for i in self.recent_menu.MenuItems] # build a python list instead of a MenuItemList
		self.rebuild_recent_menu()

	def rebuild_recent_menu(self):
		recents = self.prefs.get_recent('project')
		self.recent_paths = [i for i in recents] # make a copy to maintain consistency even if the menu loses sync with the prefs
		for i, p in enumerate(self.recent_paths):
			item = self.recent_menu_items[i]
			item.SetItemLabel(os.path.basename(p))
			item.Enable(True)
		for i in range(len(self.recent_paths), 10):
			item = self.recent_menu_items[i]
			item.SetItemLabel('n/a')
			item.Enable(False)

	def rebuild_recent_menu_segfaulting(self):
		# this is a much more elegant implementation that removes the items that are not in use
		# however it segfaults when putting the items back into place (but simple test scripts work fine...)
		recents = self.prefs.get_recent('project')
		if recents:
			while len(recents) < self.recent_menu.MenuItemCount:
				self.recent_menu.RemoveItem(self.recent_menu.MenuItems[self.recent_menu.MenuItemCount - 1])
			while len(recents) > self.recent_menu.MenuItemCount:
				self.recent_menu.AppendItem(self.recent_menu_items[self.recent_menu.MenuItemCount])

			self.recent_paths = [i for i in recents] # make a copy to maintain consistency even if the menu loses sync with the prefs
			for i, p in enumerate(self.recent_paths):
				item = self.recent_menu_items[i]
				item.SetItemLabel(os.path.basename(p))
				if i == 0:
					item.Enable(True)
		else:
			while self.recent_menu.MenuItemCount > 1:
				self.recent_menu.RemoveItem(self.recent_menu.MenuItems[self.recent_menu.MenuItemCount - 1])
			self.recent_paths = []
			first = self.recent_menu_items[0]
			first.SetItemLabel('(none)')
			first.Enable(False)


	menubar =  MenuBar(
		Menu(
			Separator(),
			Action(name='&New', action='do_new', accelerator='Ctrl+N', image=support.GetIcon('new')),
			Action(name='&Open...', action='do_open', accelerator='Ctrl+O', image=support.GetIcon('open')),
			Menu(
				name='Open &recent',
				*[Action(name='recent {0}'.format(i), action='do_open_recent_{0}'.format(i)) for i in range(10)]
			),
			Separator(),
			Action(name='&Save', action='do_save', accelerator='Ctrl+S', image=support.GetIcon('save')),
			Action(name='Save &as...', action='do_save_as', accelerator='Shift+Ctrl+S', image=support.GetIcon('save')),
			Separator(),
			Action(name='&Quit', action='_on_close', accelerator='Ctrl+Q', image=support.GetIcon('close')),
			name='&File',
		),
		Menu(
			Action(name='&Add...', action='do_add', accelerator='Ctrl+A', image=support.GetIcon('add')),
			Action(name='&Manage...', action='do_graphmanager', image=support.GetIcon('manage')),
			name='&Graphs',
		),
		Menu(
			'zoom',
				Action(name='Zoom to &fit', action='do_fit', image=support.GetIcon('fit')),
				# checked items cannot have icons
				Action(name='&Zoom rectangle', action='do_zoom', checked_when='zoom_checked', style='toggle'),
				Action(name='&Pan', action='do_pan', checked_when='pan_checked', style='toggle'),
			'presentation mode',
				Action(name='Presentation &mode', action='do_presentation_mode', checked_when='presentation_mode', style='toggle'),
				Action(name='Full &screen', action='do_fullscreen', enabled_when='presentation_mode', style='toggle', checked_when='figure_fullscreen', accelerator='F11'),
			name='&View',
		),
		Menu(
			'export',
				Action(name='&Export image...', action='do_export', accelerator='Ctrl+E', image=support.GetIcon('export')),
				Action(name='&Export movie...', action='do_movie', accelerator='Ctrl+M', image=support.GetIcon('movie')),
			'python',
				Action(name='&Python console...', action='do_python', image=support.GetIcon('python')),
			name='&Tools',
		),
		Menu(
			Action(name='&About...', action='do_about', image=support.GetIcon('about')),
			name='&Help',
		)
	)

	main_toolbar = ToolBar(
		'main',
			Action(name='New', action='do_new', tooltip='New project', image=support.GetIcon('new')),
			Action(name='Open', action='do_open', tooltip='Open project', image=support.GetIcon('open')),
			Action(name='Save', action='do_save', tooltip='Save project', image=support.GetIcon('save')),
		'graphs',
			Action(name='Add', action='do_add', tooltip='Add graph', image=support.GetIcon('add')),
			Action(name='Manage', action='do_graphmanager', tooltip='Graph manager', image=support.GetIcon('manage')),
		'view',
			Action(name='Fit', action='do_fit', tooltip='Zoom to fit', image=support.GetIcon('fit')),
			Action(name='Zoom', action='do_zoom', tooltip='Zoom rectangle', image=support.GetIcon('zoom'), checked_when='zoom_checked', style='toggle'),
			Action(name='Pan', action='do_pan', tooltip='Pan', image=support.GetIcon('pan'), checked_when='pan_checked', style='toggle'),
		'export',
			Action(name='Export image', action='do_export', tooltip='Export image', image=support.GetIcon('export')),
			Action(name='Export movie', action='do_movie', tooltip='Export movie', image=support.GetIcon('movie')),
		'python', 
			Action(name='Python', action='do_python', tooltip='Python console', image=support.GetIcon('python')),
		'about',
			Action(name='About', action='do_about', tooltip='About', image=support.GetIcon('about')),
		show_tool_names=False
	)

	traits_view = View(
			Group(
				Item('frame', style='custom', editor=InstanceEditor()),
				show_labels=False,
			),
			resizable=True,
			height=700, width=1100,
			buttons=NoButtons,
			title=version.name,
			menubar=menubar,
			toolbar=main_toolbar,
			statusbar='status',
			handler=MainWindowHandler(),
			icon=support.GetIcon('spacetime-icon'),
		)

	def parseargs(self):
		from optparse import OptionParser
		parser = OptionParser(usage="usage: %prog [options] [project file]")
		parser.add_option("--presentation", dest="presentation", action='store_true', help="start in presentation (two window) mode")
		parser.add_option("--debug", dest="debug", action="store_true", help="print debugging statements")

		return parser.parse_args()

	def run(self):
		options, args = self.parseargs()

		if options.debug:
			loglevel = logging.DEBUG
		else:
			loglevel = logging.WARNING
		logging.basicConfig(level=loglevel)

		app = wx.PySimpleApp()

		if options.presentation:
			self._open_presentation_mode()

		self.ui = self.edit_traits()
		self.context.uiparent = self.ui.control
		self.context.plot = self.plot
		self.prefs.restore_window('main', self.ui)
		self.init_recent_menu()

		if args:
			# passing in 'self' for the info argument is a bit of a hack, but fortunately self.ui.context seems to be working fine
			self.ui.handler.do_open(self, args[0])
			# silently ignore multiple projects for Windows Explorer integration

		app.MainLoop()

if __name__ == '__main__':
	app = App()
	context = app.context
	del app
	context.app.run()
