# Thi file is part of Spacetime.
#
# Copyright (C) 2010-2013 Leiden University.
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

# somehow avbin.dll doesn't play nice with some other libs and must be loaded first on Windows
import platform
if platform.system() == 'Windows':
	try:
		import ctypes
		ctypes.cdll.LoadLibrary('avbin')
	except:
		pass

# keep this import at top to ensure proper matplotlib backend selection
from .figure import MPLFigureEditor, DrawManager, CallbackLoopManager

from .. import plot, modules, version, prefs, util, pypymanager, cache
from . import support, windows

import enthought.traits.api as traits
import enthought.traits.ui.api as traitsui

from enthought.pyface.api import ProgressDialog
import matplotlib.figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
import wx
import json
import os
import itertools
import sys
import shutil
import traceback
import copy

import logging
logging.basicConfig()
logger = logging.getLogger(__name__)


class MainTab(modules.generic.gui.SerializableTab):
	version = traits.Property()
	# the combination of an InstanceEditor with DelegatedTo traits and trait_set(trait_change_notify=False)
	# seems to be special: the GUI will be updated but no event handlers will be called
	xlimits = traits.Instance(support.DateTimeLimits, args=())
	xauto = traits.DelegatesTo('xlimits', 'auto')
	xmin_mpldt = traits.DelegatesTo('xlimits', 'min_mpldt')
	xmax_mpldt = traits.DelegatesTo('xlimits', 'max_mpldt')

	x_rezero = traits.Bool(False)
	x_auto_origin = traits.Button()
	x_origin = traits.Instance(support.DateTimeSelector, args=())
	x_origin_mpldt = traits.DelegatesTo('x_origin', 'mpldt')
	x_unit = traits.Enum(86400., 1440., 24., 1.)

	label = 'Main'
	status = traits.Str('')

	traits_saved = 'version', 'xmin_mpldt', 'xmax_mpldt', 'xauto', 'x_rezero', 'x_origin_mpldt', 'x_unit'

	def _get_version(self):
		return version.version

	def _set_version(self, version):
		pass

	def xlim_callback(self, ax):
		with self.context.callbacks.avoid(self.xlimits):
			self.xmin_mpldt, self.xmax_mpldt = self.context.plot.get_ax_limits(ax)
		if not self.context.callbacks.is_avoiding(self.xlimits):
			self.xauto = False
		logger.debug('%s.xlim_callback: (%s, %s) %s', self.__class__.__name__, self.xlimits.min, self.xlimits.max, 'auto' if self.xauto else 'manual')

	@traits.on_trait_change('xmin_mpldt, xmax_mpldt, xauto')
	@CallbackLoopManager.decorator('xlimits')
	def xlim_changed(self):
		logger.debug('%s.xlim_changed: (%s, %s) %s', self.__class__.__name__, self.xlimits.min, self.xlimits.max, 'auto' if self.xauto else 'manual')
		self.xmin_mpldt, self.xmax_mpldt = self.context.plot.set_shared_xlim(self.xmin_mpldt, self.xmax_mpldt, self.xauto)
		self.context.canvas.redraw()

	def reset_autoscale(self):
		self.xauto = True

	@traits.on_trait_change('x_rezero, x_origin_mpldt, x_unit')
	def x_rezero_changed(self):
		if not self.context.callbacks.is_avoiding(self.xlimits):
			self.context.plot.set_rezero_opts(self.x_rezero, self.x_unit, self.x_origin.mpldt)
			self.context.canvas.rebuild()

	def _x_auto_origin_fired(self):
		self.x_origin.mpldt = self.xmin_mpldt

	traits_view = traitsui.View(traitsui.Group(
		traitsui.Group(
			traitsui.Item('xlimits', style='custom'),
			show_labels=False,
			label='Time axis limits',
			show_border=True,
		),
		traitsui.Group(
			traitsui.Item('x_rezero', label='Relative time'),
			traitsui.Item('x_origin', label='Origin', enabled_when='x_rezero', style='custom'),
			traitsui.Item('x_auto_origin', show_label=False, label='Auto origin', enabled_when='x_rezero'),
			traitsui.Item('x_unit', label='Unit', enabled_when='x_rezero', editor=traitsui.EnumEditor(values=support.EnumMapping(((86400., 'seconds'), (1440., 'minutes'), (24., 'hours'), (1., 'days')
)))),
			show_border=True,
			label='Rezero x-axis',
		),
		layout='normal',
	))


class MainWindowHandler(traitsui.Handler):
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
		windows.GUIModuleSelector.run_static(info.ui.context['object'].context)

	def do_python(self, info):
		windows.PythonWindow.run_static(info.ui.context['object'].context)

	def do_clear_image_cache(self, info):
		with cache.Cache('image_metadata') as c:
			c.clear()
		support.Message.show(title='Cache cleared', message='Image metadata cache has been cleared.')

	def do_about(self, info):
		windows.AboutWindow.run_static(info.ui.context['object'].context)

	def do_export_data(self, info):
		context = info.ui.context['object'].context

		dlg = wx.FileDialog(
			info.ui.control,
			"Export data",
			context.prefs.get_path('export_data'),
			"data",
			"|All files (*.*)|*.*",
			wx.SAVE
		)

		if dlg.ShowModal() != wx.ID_OK:
			return

		context.prefs.set_path('export_data', dlg.GetDirectory())
		dest = dlg.GetPath()

		try:
			os.mkdir(dest)
		except OSError:
			support.Message.exception(
				parent=context.uiparent, 
				message='Export failed', title='Export failed',
				desc='Cannot create directory {0}'.format(dest),
			)
			return

		for tab in context.app.tabs:
			if hasattr(tab, 'export'):
				tab.export(dest)
			
		
	def do_export_image(self, info):
		context = info.ui.context['object'].context
		
		exportdialog = context.app.export_image_dialog
		if not exportdialog.run().result:
			return

		dlg = wx.FileDialog(
			info.ui.control,
			"Export image",
			context.prefs.get_path('export_image'),
			"image." + exportdialog.extension,
			exportdialog.wxfilter + "|All files (*.*)|*.*",
			wx.SAVE|wx.OVERWRITE_PROMPT
		)

		if dlg.ShowModal() == wx.ID_OK:
			context.prefs.set_path('export_image', dlg.GetDirectory())
			path = dlg.GetPath()
			oldfig = context.plot.figure
			newfig = matplotlib.figure.Figure(exportdialog.figsize, exportdialog.dpi)
			canvas = FigureCanvasAgg(newfig)
			try:
				context.plot.relocate(newfig)
				context.app.rebuild_figure()
				newfig.savefig(path, dpi=exportdialog.dpi, format=exportdialog.extension)
			except:
				support.Message.file_save_failed(path, parent=info.ui.control)
			finally:
				context.plot.relocate(oldfig)
				context.app.rebuild_figure()

	def do_export_movie(self, info):
		context = info.ui.context['object'].context
		
		moviedialog = context.app.export_movie_dialog
		try:
			if not moviedialog.run().result:
				return
		except RuntimeError as e:
			support.Message.show(parent=context.uiparent, message='Nothing to animate', desc=str(e))
			return

		dlg = wx.FileDialog(
			info.ui.control,
			"Save movie",
			context.prefs.get_path('export_movie'),
			"movie." + moviedialog.format,
			"*.{0}|*.{0}|All files (*.*)|*.*".format(moviedialog.format),
			wx.SAVE|wx.OVERWRITE_PROMPT
		)

		if dlg.ShowModal() != wx.ID_OK:
			return
		context.prefs.set_path('export_movie', dlg.GetDirectory())

		# preparations, no harm is done if something goes wrong here
		movie = stdout_cb = stdout = None
		oldfig = context.plot.figure
		progress = ProgressDialog(title="Movie", message="Building movie", max=moviedialog.get_framecount()+2, can_cancel=True, parent=context.uiparent)
		newfig = matplotlib.figure.Figure((moviedialog.frame_width / moviedialog.dpi, moviedialog.frame_height / moviedialog.dpi), moviedialog.dpi)
		canvas = FigureCanvasAgg(newfig)

		finalpath = dlg.GetPath()
		temppath = finalpath + '.temp'

		class UserCanceled(Exception): pass
		class FFmpegFailed(Exception): pass

		# now the real thing starts. we have to clean up properly
		try:
			progress.open()
			context.plot.relocate(newfig)
			movie = util.FFmpegEncode(
				temppath,
				moviedialog.format,
				moviedialog.codec,
				moviedialog.frame_rate,
				(moviedialog.frame_width, moviedialog.frame_height),
				moviedialog.ffmpeg_options.split(),
			)
			stdout_cb = movie.spawnstdoutthread()
			progress.update(1)

			# FIXME disable drawmanager? relocate? hold?
			iters = tuple(i() for i in moviedialog.get_animate_functions())
			for frameno, void in enumerate(itertools.izip_longest(*iters)):
				context.canvas.rebuild()
				newfig.canvas.draw()
				movie.writeframe(newfig.canvas.tostring_rgb())
				(cont, skip) = progress.update(frameno+2)
				if not cont or skip:
					raise UserCanceled()
			
			ret = movie.close()	
			if ret != 0:
				raise FFmpegFailed('ffmpeg returned {0}'.format(ret))
			stdout = stdout_cb()
			stdout_cb = None
			shutil.move(temppath, finalpath)
			progress.update(progress.max)

		except UserCanceled:
			movie.abort()
			return
		except:
			if movie:
				movie.close()
			if stdout_cb:
				try:
					stdout = stdout_cb()
				except:
					pass
			stdout_cb = None

			support.Message.show(
				parent=context.uiparent, 
				message='Movie export failed', title='Exception occured',
				desc='Something went wrong while exporting the movie. Detailed debugging information can be found below.',
				bt="FFMPEG output:\n{0}\n\nBACKTRACE:\n{1}".format(stdout, traceback.format_exc())
			)
			return
		finally:
			if stdout_cb:
				stdout = stdout_cb()
			progress.close()
			try:
				os.remove(temppath)
			except:
				pass
			context.plot.relocate(oldfig)
			context.canvas.rebuild()

		support.Message.show(
			parent=context.uiparent,
			title='Movie complete', message='Movie complete',
			desc='The movie successfully been generated.\nFor debugging purposes, the full FFmpeg output can be found below.',
			bt=stdout
		)


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

	def do_reload(self, info):
		app = info.ui.context['object']
		with app.drawmgr.hold():
			for tab in app.tabs:
				tab.reload = True

	def do_copy(self, info):
		context = info.ui.context['object'].context
		context.plot.figure.canvas.Copy_to_Clipboard()


class Frame(traits.HasTraits):
	pass


class SplitFrame(Frame):
	app = traits.Instance(traits.HasTraits)
	figure = traits.Instance(matplotlib.figure.Figure, args=())
	tabs = traits.DelegatesTo('app')
	tabs_selected = traits.DelegatesTo('app')
	status = traits.DelegatesTo('app')

	traits_view = traitsui.View(
		traitsui.HSplit(
			traitsui.Item('figure', width=600, editor=MPLFigureEditor(status='status'), dock='vertical'),
			traitsui.Item('tabs', style='custom', editor=traitsui.ListEditor(use_notebook=True, selected='tabs_selected', page_name='.label')),
			show_labels=False,
		)
	)


class SimpleFrame(Frame):
	app = traits.Instance(traits.HasTraits)
	tabs = traits.DelegatesTo('app')
	tabs_selected = traits.DelegatesTo('app')

	traits_view = traitsui.View(
		traitsui.Group(
			traitsui.Item('tabs', style='custom', editor=traitsui.ListEditor(use_notebook=True, selected='tabs_selected', page_name='.label')),
			show_labels=False,
		)
	)


class Context(traits.HasTraits):
	app = traits.Instance(traits.HasTraits)
#	document = traits.Instance(Any)
	plot = traits.Instance(plot.Plot)
	canvas = traits.Instance(DrawManager)
	callbacks = traits.Instance(CallbackLoopManager, args=())
	prefs = traits.Instance(prefs.Storage)
	uiparent = traits.Any

	def fork(self, **kwargs):
		clone = copy.copy(self)
		clone.__dict__.update(kwargs)
		return clone


class App(traits.HasTraits):
	plot = traits.Instance(plot.Plot)
	maintab = traits.Instance(MainTab)
	status = traits.DelegatesTo('maintab')
	drawmgr = traits.Instance(DrawManager)
	moduleloader = traits.Instance(modules.loader.Loader)
	frame = traits.Instance(Frame)
	figurewindowui = None
	figure_fullscreen = traits.Bool(False)
	prefs = traits.Instance(prefs.Storage, args=())

	context = traits.Instance(Context)

	export_image_dialog = traits.Instance(traits.HasTraits)
	export_movie_dialog = traits.Instance(traits.HasTraits)

	pan_checked = traits.Bool(False)
	zoom_checked = traits.Bool(False)
	presentation_mode = traits.Bool(False)

	project_path = traits.Str()
	project_filename = traits.Property(depends_on='project_path')
	_tabs_modified = traits.Bool(False)
	project_modified = traits.Property(depends_on='_tabs_modified, tabs._modified')

	tabs = traits.List(traits.Instance(modules.generic.gui.Tab))
	tabs_selected = traits.Instance(modules.generic.gui.Tab)

	def on_figure_resize(self, event):
		logger.debug('on_figure_resize called')
		self.context.canvas.redraw()

	def redraw_canvas(self):
		# make a closure on self so figure.canvas can be changed in the meantime
		wx.CallAfter(lambda: self.context.plot.figure.canvas.draw())

	def get_new_tab(self, klass):
		return klass(context=self.context)

	def _context_default(self):
		return Context(app=self, canvas=self.drawmgr, prefs=self.prefs)

	def _maintab_default(self):
		return MainTab(context=self.context)

	def _drawmgr_default(self):
		return DrawManager(self.rebuild_figure, self.redraw_canvas)

	def _export_image_dialog_default(self):
		return windows.ExportDialog(context=self.context)

	def _export_movie_dialog_default(self):
		return windows.MovieDialog(context=self.context)

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

	@traits.cached_property
	def _get_project_filename(self):
		if not self.project_path:
			return ''
		return os.path.basename(self.project_path)

	@traits.cached_property
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

		progress = ProgressDialog(title="Open", message="Loading project", max=len(data)+1, can_cancel=False, parent=self.context.uiparent)
		progress.open()
		with self.context.canvas.hold_delayed():
			self.tabs[0].from_serialized(data.pop(0)[1])
			tabs = [self.tabs[0]]
			progress.update(1)
			# FIXME: check version number and emit warning
			for p, (id, props) in enumerate(data):
				try:
					tab = self.get_new_tab(self.moduleloader.get_class_by_id(id))
					tab.from_serialized(props)
					tabs.append(tab)
				except KeyError:
					support.Message.show(title='Warning', message='Warning: incompatible project file', desc='Ignoring unknown graph id "{0}". Project might not be completely functional.'.format(id))
				progress.update(2+p)
			self.tabs = tabs
			self.project_path = path
			wx.CallAfter(self.clear_project_modified)
			wx.CallAfter(lambda: (progress.update(progress.max), progress.close()))

	def save_project(self, path):
		data = [('general', self.tabs[0].get_serialized())]
		for tab in self.tabs:
			if isinstance(tab, modules.generic.gui.SubplotGUI):
				data.append((self.moduleloader.get_id_by_instance(tab), tab.get_serialized()))
		with open(path, 'wb') as fp:
			fp.write('Spacetime\nJSON\n')
			json.dump(data, fp)
		self.project_path = path
		self.clear_project_modified()
		return True

	@traits.on_trait_change('project_modified')
	def update_title(self):
		if self.project_filename:
			self.ui.title = '{0} - {1}{2}'.format(version.name, self.project_filename, '*' if self.project_modified else '')
		else:
			self.ui.title = version.name

		if self.figurewindowui:
			self.figurewindowui.title = self.ui.title

	def rebuild_figure(self):
		self.plot.clear()
		[self.plot.add_subplot(tab.plot) for tab in self.tabs if isinstance(tab, modules.generic.gui.SubplotGUI) and tab.visible]
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
		self.recent_paths = [i for i in recents if os.path.exists(i)]
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

	def is_known_exception(self, type, value, tb):
		return False
	
	def is_known_traits_exception(self, object, trait_name, old_value, new_value):
		if sys.platform == 'win32' and util.instance_fqcn(object) == 'traitsui.wx.table_model.TableModel' and trait_name == 'click':
			return True
		return False

	def excepthook(self, type, value, tb):
		text = ''.join(traceback.format_exception(type, value, tb))
		if self.is_known_exception(type, value, tb):
			logger.warning('Ignoring known exception:\n' + text)
		else:
			logger.error(text)
			# DISABLE FOR 0.15
			#support.Message.exception(parent=self.context.uiparent, bt=text)

	def trait_exception_handler(self, object, trait_name, old_value, new_value):
		text = 'Exception occurred in traits notification handler for object: {0!r}, trait: {1}, old value: {2!r}, new value: {3!r}\n{4}'.format(object, trait_name, old_value, new_value, traceback.format_exc())
		if self.is_known_traits_exception(object, trait_name, old_value, new_value):
			logger.warning('Ignoring known traits exception:\n' + text)			
		else:
			logger.error(text)
			# DISABLE FOR 0.15
			#support.Message.exception(parent=self.context.uiparent, bt=text)


	menubar =  traitsui.MenuBar(
		traitsui.Menu(
			traitsui.Separator(),
			traitsui.Action(name='&New', action='do_new', accelerator='Ctrl+N', image=support.GetIcon('new')),
			traitsui.Action(name='&Open...', action='do_open', accelerator='Ctrl+O', image=support.GetIcon('open')),
			traitsui.Menu(
				name='Open &recent',
				*[traitsui.Action(name='recent {0}'.format(i), action='do_open_recent_{0}'.format(i)) for i in range(10)]
			),
			traitsui.Separator(),
			traitsui.Action(name='&Save', action='do_save', accelerator='Ctrl+S', image=support.GetIcon('save')),
			traitsui.Action(name='Save &as...', action='do_save_as', accelerator='Shift+Ctrl+S', image=support.GetIcon('save')),
			traitsui.Separator(),
			traitsui.Action(name='&Quit', action='_on_close', accelerator='Ctrl+Q', image=support.GetIcon('close')),
			name='&File',
		),
		traitsui.Menu(
			traitsui.Action(name='&Add...', action='do_add', accelerator='Ctrl+A', image=support.GetIcon('add')),
			traitsui.Action(name='&Manage...', action='do_graphmanager', image=support.GetIcon('manage')),
			traitsui.Action(name='&Reload all', action='do_reload', accelerator='Ctrl+R', image=support.GetIcon('reload')),
			name='&Graphs',
		),
		traitsui.Menu(
			'zoom',
				traitsui.Action(name='Zoom to &fit', action='do_fit', image=support.GetIcon('fit')),
				# checked items cannot have icons
				traitsui.Action(name='&Zoom rectangle', action='do_zoom', checked_when='zoom_checked', style='toggle'),
				traitsui.Action(name='&Pan', action='do_pan', checked_when='pan_checked', style='toggle'),
			'presentation mode',
				traitsui.Action(name='Presentation &mode', action='do_presentation_mode', checked_when='presentation_mode', style='toggle'),
				traitsui.Action(name='Full &screen', action='do_fullscreen', enabled_when='presentation_mode', style='toggle', checked_when='figure_fullscreen', accelerator='F11'),
			name='&View',
		),
		traitsui.Menu(
			'export',
				traitsui.Action(name='Export &data...', action='do_export_data', accelerator='Ctrl+D', image=support.GetIcon('export')),
				traitsui.Action(name='Export &image...', action='do_export_image', accelerator='Ctrl+E', image=support.GetIcon('image')),
				traitsui.Action(name='&Copy to clipboard', action='do_copy', accelerator='Ctrl+C', tooltip='Copy to clipboard', image=support.GetIcon('copy')),
				traitsui.Action(name='Export &movie...', action='do_export_movie', accelerator='Ctrl+M', image=support.GetIcon('movie')),
			'advanced',
				traitsui.Action(name='&Python console...', action='do_python', image=support.GetIcon('python')),
				traitsui.Action(name='Clear image metadata cache', action='do_clear_image_cache'),
			name='&Tools',
		),
		traitsui.Menu(
			traitsui.Action(name='&About...', action='do_about', image=support.GetIcon('about')),
			name='&Help',
		)
	)

	main_toolbar = traitsui.ToolBar(
		'main',
			traitsui.Action(name='New', action='do_new', tooltip='New project', image=support.GetIcon('new')),
			traitsui.Action(name='Open', action='do_open', tooltip='Open project', image=support.GetIcon('open')),
			traitsui.Action(name='Save', action='do_save', tooltip='Save project', image=support.GetIcon('save')),
		'graphs',
			traitsui.Action(name='Add', action='do_add', tooltip='Add graph', image=support.GetIcon('add')),
			traitsui.Action(name='Manage', action='do_graphmanager', tooltip='Graph manager', image=support.GetIcon('manage')),
			traitsui.Action(name='Reload', action='do_reload', tooltip='Reload all', image=support.GetIcon('reload')),
		'view',
			traitsui.Action(name='Fit', action='do_fit', tooltip='Zoom to fit', image=support.GetIcon('fit')),
			traitsui.Action(name='Zoom', action='do_zoom', tooltip='Zoom rectangle', image=support.GetIcon('zoom'), checked_when='zoom_checked', style='toggle'),
			traitsui.Action(name='Pan', action='do_pan', tooltip='Pan', image=support.GetIcon('pan'), checked_when='pan_checked', style='toggle'),
		'export',
			traitsui.Action(name='Export data', action='do_export_data', tooltip='Export data', image=support.GetIcon('export')),
			traitsui.Action(name='Export image', action='do_export_image', tooltip='Export image', image=support.GetIcon('image')),
			traitsui.Action(name='&Copy to clipboard', action='do_copy', accelerator='Ctrl+C', tooltip='Copy to clipboard', image=support.GetIcon('copy')),

			traitsui.Action(name='Export movie', action='do_export_movie', tooltip='Export movie', image=support.GetIcon('movie')),
		'python', 
			traitsui.Action(name='Python', action='do_python', tooltip='Python console', image=support.GetIcon('python')),
		'about',
			traitsui.Action(name='About', action='do_about', tooltip='About', image=support.GetIcon('about')),
		show_tool_names=False
	)

	traits_view = traitsui.View(
			traitsui.Group(
				traitsui.Item('frame', style='custom', editor=traitsui.InstanceEditor()),
				show_labels=False,
			),
			resizable=True,
			height=700, width=1100,
			buttons=traitsui.NoButtons,
			title=version.name,
			menubar=menubar,
			toolbar=main_toolbar,
			statusbar='status',
			handler=MainWindowHandler(),
			icon=support.GetIcon('spacetime-icon'),
			kind='live',
		)

	def parseargs(self):
		from optparse import OptionParser
		parser = OptionParser(usage="usage: %prog [options] [project file]")
		parser.add_option("--debug", dest="debug", action="store_true", help="print debugging statements")
		parser.add_option("--pypy", dest="pypy", action="store_true", help="use pypy acceleration (experimental)")

		return parser.parse_args()

	def run(self):
		options, args = self.parseargs()

		logger = logging.getLogger()
		if options.debug:
			logger.setLevel(logging.DEBUG)
		else:
			logger.setLevel(logging.WARNING)

		sys.excepthook = self.excepthook
		traits.push_exception_handler(self.trait_exception_handler, main=True, locked=True)

		if options.pypy:
			pypymanager.set_executable('pypy')
			pypymanager.launch_delegate()

		try:
			app = wx.PySimpleApp()

			self.moduleloader = modules.loader.Loader()
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
		finally:
			pypymanager.shutdown_delegate()

if __name__ == '__main__':
	app = App()
	context = app.context
	del app
	context.app.run()
