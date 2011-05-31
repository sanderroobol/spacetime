# keep this import at top to ensure proper matplotlib backend selection
from .figure import MPLFigureEditor, DrawManager

from .. import plot, modules, version, prefs
from . import support, windows

from enthought.traits.api import *
from enthought.traits.ui.api import *
import matplotlib.figure
import wx
import json
import os

import logging
logger = logging.getLogger(__name__)


class MainTab(modules.generic.panels.SerializableTab):
	# the combination of an InstanceEditor with DelegatedTo traits and trait_set(trait_change_notify=False)
	# seems to be special: the GUI will be updated but no event handlers will be called
	xlimits = Instance(support.DateTimeLimits, args=())
	xauto = DelegatesTo('xlimits', 'auto')
	xmin_mpldt = DelegatesTo('xlimits', 'min_mpldt')
	xmax_mpldt = DelegatesTo('xlimits', 'max_mpldt')
	label = 'Main'
	status = Str('')

	traits_saved = 'xmin_mpldt', 'xmax_mpldt', 'xauto'

	mainwindow = Any

	def xlim_callback(self, ax):
		xmin, xmax = ax.get_xlim()
		self.trait_set(trait_change_notify=False, xmin_mpldt=xmin, xmax_mpldt=xmax, xauto=False)
		logger.info('%s.xlim_callback: (%s, %s) %s', self.__class__.__name__, self.xlimits.min, self.xlimits.max, 'auto' if self.xauto else 'manual')

	@on_trait_change('xmin_mpldt, xmax_mpldt, xauto')
	def xlim_changed(self):
		logger.info('%s.xlim_changed: (%s, %s) %s', self.__class__.__name__, self.xlimits.min, self.xlimits.max, 'auto' if self.xauto else 'manual')
		xmin, xmax = self.mainwindow.plot.set_shared_xlim(self.xmin_mpldt, self.xmax_mpldt, self.xauto)
		self.trait_set(trait_change_notify=False, xmin_mpldt=xmin, xmax_mpldt=xmax)
		self.mainwindow.update_canvas()

	def reset_autoscale(self):
		self.xauto = True

	def get_serialized(self):
		d = super(MainTab, self).get_serialized()
		d['version'] = version.version
		return d

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

		if mainwindow.has_modifications():
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
			gui.support.Message.file_open_failed(path, parent=info.ui.control)
		mainwindow.prefs.add_recent('project', path)
		mainwindow.rebuild_recent_menu()
		mainwindow.update_title()
		mainwindow.drawmgr.redraw_figure()

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
			gui.support.Message.file_open_failed(path, parent=info.ui.control)
		return False

	def do_add(self, info):
		windows.PanelSelector.run(mainwindow=info.ui.context['object'])

	def do_python(self, info):
		mainwindow = info.ui.context['object']
		windows.PythonWindow(prefs=mainwindow.prefs).edit_traits(parent=info.ui.control)

	def do_about(self, info):
		windows.AboutWindow().edit_traits(parent=info.ui.control)

	def do_export(self, info):
		# mostly borrowed from Matplotlib's NavigationToolbar2Wx.save()
		mainwindow = info.ui.context['object']
		canvas = mainwindow.figure.canvas
		# Fetch the required filename and file type.
		filetypes, exts, filter_index = canvas._get_imagesave_wildcards()
		default_file = "image." + canvas.get_default_filetype()
		dlg = wx.FileDialog(info.ui.control, "Save to file", "", default_file, filetypes, wx.SAVE|wx.OVERWRITE_PROMPT)
		dlg.SetFilterIndex(filter_index)
		dlg.Directory = mainwindow.prefs.get_path('export')
		if dlg.ShowModal() == wx.ID_OK:
			dirname  = dlg.GetDirectory()
			mainwindow.prefs.set_path('export', dirname)
			filename = dlg.GetFilename()
			format = exts[dlg.GetFilterIndex()]
			basename, ext = os.path.splitext(filename)
			if ext.startswith('.'):
				ext = ext[1:]
			if ext in ('svg', 'pdf', 'ps', 'eps', 'png') and format != ext:
				#looks like they forgot to set the image type drop down, going with the extension.
				#warnings.warn('extension %s did not match the selected image type %s; going with %s'%(
				format = ext
			path = os.path.join(dirname, filename)
			try:
				canvas.print_figure(path, format=format)
			except:
				gui.support.Message.file_save_failed(path, parent=info.ui.control)

	def do_fit(self, info):
		mainwindow = info.ui.context['object']
		with mainwindow.drawmgr.hold():
			for tab in mainwindow.tabs:
				tab.reset_autoscale()

	def do_zoom(self, info):
		mainwindow = info.ui.context['object']
		mainwindow.figure.toolbar.zoom()
		mainwindow.zoom_checked = not mainwindow.zoom_checked
		mainwindow.pan_checked = False

	def do_pan(self, info):
		mainwindow = info.ui.context['object']
		mainwindow.figure.toolbar.pan()
		mainwindow.pan_checked = not mainwindow.pan_checked
		mainwindow.zoom_checked = False

	def do_presentation_mode(self, info):
		mainwindow = info.ui.context['object']
		mainwindow.toggle_presentation_mode()

	def do_fullscreen(self, info):
		info.ui.context['object'].toggle_fullscreen()

	def do_graphmanager(self, info):
		windows.GraphManager.run(mainwindow=info.ui.context['object'], parent=info.ui.control)



class MainWindow(HasTraits):
	pass


class SplitMainWindow(MainWindow):
	app = Instance(HasTraits)
	figure = DelegatesTo('app')
	tabs = DelegatesTo('app')
	status = DelegatesTo('app')

	traits_view = View(
		HSplit(
			Item('figure', width=600, editor=MPLFigureEditor(status='status'), dock='vertical'),
			Item('tabs', style='custom', editor=ListEditor(use_notebook=True, page_name='.label')),
			show_labels=False,
		)
	)


class SimpleMainWindow(MainWindow):
	app = Instance(HasTraits)
	tabs = DelegatesTo('app')

	traits_view = View(
		Group(
			Item('tabs', style='custom', editor=ListEditor(use_notebook=True, page_name='.label')),
			show_labels=False,
		)
	)


class App(HasTraits):
	plot = Instance(plot.Plot)
	figure = Instance(matplotlib.figure.Figure)
	maintab = Instance(MainTab)
	status = DelegatesTo('maintab')
	drawmgr = Instance(DrawManager)
	panelmgr = Instance(modules.PanelManager, args=())
	mainwindow = Instance(MainWindow)
	figurewindowui = None
	figure_fullscreen = Bool(False)
	prefs = Instance(prefs.Storage, args=())

	pan_checked = Bool(False)
	zoom_checked = Bool(False)
	presentation_mode = Bool(False)

	project_path = Str()
	project_filename = Property(depends_on='project_path')

	tabs = List(Instance(modules.generic.panels.Tab))

	def on_figure_resize(self, event):
		logger.info('on_figure_resize called')
		self.plot.setup_margins()
		self.drawmgr.update_canvas()

	def update_canvas(self):
		# make a closure on self so figure.canvas can be changed in the meantime
		wx.CallAfter(lambda: self.figure.canvas.draw())

	def get_new_tab(self, klass):
		return klass(drawmgr=self.drawmgr, autoscale=self.plot.autoscale, prefs=self.prefs, parent=self.ui.control)

	def add_tab(self, klass, serialized_data=None):
		tab = self.get_new_tab(klass)
		if serialized_data is not None:
			tab.from_serialized(serialized_data)
		self.tabs.append(tab)

	def _maintab_default(self):
		return MainTab(mainwindow=self, drawmgr=self.drawmgr)

	def _drawmgr_default(self):
		return DrawManager(self.redraw_figure, self.update_canvas)

	def _tabs_changed(self):
		self.drawmgr.redraw_figure()

	def _tabs_items_changed(self, event):
		for removed in event.removed:
			if isinstance(removed, MainTab):
				self.tabs.insert(0, removed)
		self.drawmgr.redraw_figure()

	def _tabs_default(self):
		return [self.maintab]

	def _get_project_filename(self):
		if not self.project_path:
			return ''
		return os.path.basename(self.project_path)

	def new_project(self):
		self.tabs = self._tabs_default()
		for klass in self.panelmgr.list_classes():
			klass.number = 0
		self.project_path = ''

	def open_project(self, path):
		with open(path, 'rb') as fp:
			if fp.read(15) != 'Spacetime\nJSON\n':
				raise ValueError('not a valid Spacetime project file')
			data = json.load(fp)
		with self.drawmgr.hold_delayed():
			self.tabs[0].from_serialized(data.pop(0)[1])
			# FIXME: check version number and emit warning
			for id, props in data:
				try:
					self.add_tab(self.panelmgr.get_class_by_id(id), props)
				except KeyError:
					support.Message.show(title='Warning', message='Warning: incompatible project file', desc='Ignoring unknown graph id "{0}". Project might not be completely functional.'.format(id))
			self.project_path = path

	def save_project(self, path):
		data = [('general', self.tabs[0].get_serialized())]
		for tab in self.tabs:
			if isinstance(tab, modules.generic.panels.SubplotPanel):
				data.append((self.panelmgr.get_id_by_instance(tab), tab.get_serialized()))
		with open(path, 'wb') as fp:
			fp.write('Spacetime\nJSON\n')
			json.dump(data, fp)
		self.project_path = path
		return True

	def update_title(self):
		if self.project_filename:
			self.ui.title = '{0} - {1}'.format(version.name, self.project_filename)
		else:
			self.ui.title = version.name

		if self.figurewindowui:
			self.figurewindowui.title = self.ui.title

	def has_modifications(self):
		return len(self.tabs) > 1

	def redraw_figure(self):
		self.plot.clear()
		[self.plot.add_subplot(tab.plot) for tab in self.tabs if isinstance(tab, modules.generic.panels.SubplotPanel) and tab.visible]
		self.plot.setup()
		self.plot.draw()
		self.plot.autoscale()

	def _connect_canvas_resize_event(self):
		self.figure.canvas.mpl_connect('resize_event', self.on_figure_resize), 

	def _plot_default(self):
		p = plot.Plot.newmatplotlibfigure()
		p.setup()
		p.set_xlim_callback(self.maintab.xlim_callback)
		wx.CallAfter(self._connect_canvas_resize_event)
		return p

	def _figure_default(self):
		return self.plot.figure

	def _mainwindow_default(self):
		return SplitMainWindow(app=self)

	def _close_presentation_mode(self):
		self.presentation_mode = False
		self.figurewindowui = None
		with self.drawmgr.hold():
			self.mainwindow = SplitMainWindow(app=self)
			self.on_figure_resize(None)
		wx.CallAfter(self._connect_canvas_resize_event)

	def _open_presentation_mode(self):
		self.presentation_mode = True
		with self.drawmgr.hold():
			self.mainwindow = SimpleMainWindow(app=self)
			self.figurewindowui = windows.FigureWindow(mainwindow=self, prefs=self.prefs).edit_traits()
		wx.CallAfter(self._connect_canvas_resize_event)
		wx.CallAfter(lambda: self.figure.canvas.Bind(wx.EVT_KEY_DOWN, self.fullscreen_keyevent))

	def toggle_presentation_mode(self):
		if self.presentation_mode:
			self.figurewindowui.control.Close()
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
				Action(name='&Export...', action='do_export', accelerator='Ctrl+E', image=support.GetIcon('export')),
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
			Action(name='Export', action='do_export', tooltip='Export', image=support.GetIcon('export')),
		'python', 
			Action(name='Python', action='do_python', tooltip='Python console', image=support.GetIcon('python')),
		'about',
			Action(name='About', action='do_about', tooltip='About', image=support.GetIcon('about')),
		show_tool_names=False
	)

	traits_view = View(
			Group(
				Item('mainwindow', style='custom', editor=InstanceEditor()),
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
		parser = OptionParser()
		parser.add_option("--presentation", dest="presentation", action='store_true', help="start in presentation (two window) mode")
		parser.add_option("--debug", dest="debug", action="store_true", help="print debugging statements")

		(options, args) = parser.parse_args()
		if len(args):
			parser.error('invalid argument(s): {0!r}'.format(args))

		return options, args

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
		self.prefs.restore_window('main', self.ui)
		self.init_recent_menu()

		app.MainLoop()

if __name__ == '__main__':
	app = App()
	app.run()
