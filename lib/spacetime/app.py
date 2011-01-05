# keep this import at top to ensure proper matplotlib backend selection
from .mplfigure import MPLFigureEditor

from . import plot, util, panels, version, uiutil

from enthought.traits.api import *
from enthought.traits.ui.api import *
from enthought.pyface.api import ImageResource
import matplotlib.figure, matplotlib.transforms
import wx
import datetime
import json
import os


class DateTimeSelector(HasTraits):
	date = Date(datetime.date.today())
	time = Time(datetime.time())
	datetime = Property(depends_on='date, time')
	mpldt = Property(depends_on='datetime')

	def _get_datetime(self):
		return datetime.datetime.combine(self.date, self.time)

	def _set_datetime(self, dt):
		self.date = dt.date()
		self.time = dt.time()

	def _get_mpldt(self):
		return util.mpldtfromdatetime(self.datetime)

	def _set_mpldt(self, f):
		self.datetime = util.datetimefrommpldt(f)

	traits_view = View(
		HGroup(
			Item('time', editor=TimeEditor(strftime='%H:%M:%D')),
			Item('date'),
			show_labels=False,
	))


class PanelMapper(object):
	# this is a list and  not a dictionary to preserve ordering
	MAPPING = (
		('camera',              panels.CameraFramePanel),
		('cameratrend',         panels.CameraTrendPanel),
		('quaderaqms',          panels.QMSPanel),
		('lpmgascabinet',       panels.GasCabinetPanel),
		('prototypegascabinet', panels.OldGasCabinetPanel),
		('reactorenvironment',  panels.ReactorEnvironmentPanel),
		('tpdirk',              panels.TPDirkPanel),
		('cameracv',            panels.CVPanel),
	)

	list_classes = tuple(klass for (id, klass) in MAPPING)
	list_tablabels = tuple(klass.tablabel for klass in list_classes)
	
	mapping_id_class = dict(MAPPING)
	mapping_classname_id = dict((klass.__name__, id) for (id, klass) in MAPPING)
	mapping_tablabel_class = dict((klass.tablabel, klass) for klass in list_classes)

	@classmethod
	def get_class_by_id(klass, id):
		return klass.mapping_id_class[id]

	@classmethod
	def get_id_by_instance(klass, obj):
		return klass.mapping_classname_id[obj.__class__.__name__]

	@classmethod
	def get_class_by_tablabel(klass, label):
		return klass.mapping_tablabel_class[label]


class PanelSelector(HasTraits):
	selected = List(Str)
	message = Str('Select subgraph type')
	types = List(PanelMapper.list_tablabels)

	traits_view = View(
		Group(
			Item('message', emphasized=True, style='readonly'),
			Item('types', editor=ListStrEditor(editable=False, multi_select=True, selected='selected')),
			show_labels=False,
			padding=5,
		),
		title='Select subgraph type',
		height=300,
		width=200,
		buttons=OKCancelButtons,
		kind='modal',
	)


class MainTab(panels.SerializableTab):
	xauto = Bool(True)
	not_xauto = Property(depends_on='xauto')
	xmin = Instance(DateTimeSelector, args=())
	xmax = Instance(DateTimeSelector, args=())
	xmin_mpldt = DelegatesTo('xmin', 'mpldt')
	xmax_mpldt = DelegatesTo('xmax', 'mpldt')
	tablabel = 'Main'
	status = Str('')

	traits_saved = 'xmin_mpldt', 'xmax_mpldt'

	mainwindow = Any

	def _get_not_xauto(self):
		return not self.xauto

	def xlim_callback(self, ax):
		self.xmin.mpldt, self.xmax.mpldt = ax.get_xlim()

	def _xmin_mpldt_changed(self):
		if self.mainwindow.plot.master_axes and self.mainwindow.plot.master_axes.get_xlim()[0] != self.xmin.mpldt:
			self.mainwindow.plot.master_axes.set_xlim(xmin=self.xmin.mpldt)
			self.mainwindow.drawmgr.update_canvas()

	def _xmax_mpldt_changed(self):
		if self.mainwindow.plot.master_axes and self.mainwindow.plot.master_axes.get_xlim()[1] != self.xmax.mpldt:
			self.mainwindow.plot.master_axes.set_xlim(xmax=self.xmax.mpldt)
			self.mainwindow.drawmgr.update_canvas()

	def get_serialized(self):
		d = super(MainTab, self).get_serialized()
		d['version'] = version.version
		return d

	traits_view = View(Group(
		Group(
			Item('xauto', label='Auto'),
			Item('xmin', label='Min', style='custom', enabled_when='not_xauto'),
			Item('xmax', label='Max', style='custom', enabled_when='not_xauto'),
			label='Time axis limits',
			show_border=True,
		),
		layout='normal',
	))


class PythonWindow(HasTraits):
	shell = PythonValue({})
	traits_view = View(
		Item('shell', show_label=False, editor=ShellEditor(share=False)),
		title='Python shell',
		height=600,
		width=500,
	)


class AboutWindow(HasTraits):
	title = Str('Spacetime ' + version.version)
	desc = Str('Copyright 2010-2011 Leiden University.\nWritten by Sander Roobol <roobol@physics.leidenuniv.nl>.\n\nRedistribution outside Leiden University is not permitted.')

	traits_view = View(
		Group(
			Item('title', emphasized=True, style='readonly'),
			Item('desc', style='readonly', editor=TextEditor(multi_line=True)),
			show_labels=False,
			padding=5,
		),
		title='About Spacetime',
		buttons=[OKButton],
		kind='modal',
	)


class MainWindowHandler(Handler):
	@staticmethod	
	def get_ui_title(filename = None):
		if filename is None:
			return 'Spacetime'
		else:
			return 'Spacetime - %s' % filename

	def set_ui_title(self, info, filename=None):
		info.ui.title = self.get_ui_title(filename)

	def do_new(self, info):
		if not self.close(info):
			return False
		mainwindow = info.ui.context['object']
		mainwindow.clear()
		self.set_ui_title(info)
		return True

	def close(self, info, is_ok=None):
		mainwindow = info.ui.context['object']
		if mainwindow.has_modifications():
			dlg = wx.MessageDialog(info.ui.control, 'Save current project?', style=wx.YES_NO | wx.CANCEL | wx.ICON_EXCLAMATION)
			ret = dlg.ShowModal()
			if ret == wx.ID_CANCEL:
				return False
			elif ret == wx.ID_YES:
				return self.do_save(info)
		return True
		
	def do_open(self, info):
		if not self.close(info):
			return
		dlg = wx.FileDialog(info.ui.control, style=wx.FD_OPEN, wildcard='Spacetime Project files (*.spacetime)|*.spacetime')
		if dlg.ShowModal() != wx.ID_OK:
			return
		mainwindow = info.ui.context['object']
		mainwindow.clear()
		try:
			mainwindow.open_project(dlg.Path)
		except:
			uiutil.Message.file_open_failed(dlg.Path)
		else:
			self.set_ui_title(info, dlg.Filename)
		mainwindow.drawmgr.redraw_figure()

	def do_save(self, info):
		dlg = wx.FileDialog(info.ui.control, style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT, wildcard='Spacetime Project files (*.spacetime)|*.spacetime')
		if dlg.ShowModal() != wx.ID_OK:
			return False
		mainwindow = info.ui.context['object']
		filename, path = dlg.Filename, dlg.Path
		if not path.endswith('.spacetime'):
			path += '.spacetime'
			filename += '.spacetime'
		try:
			if mainwindow.save_project(path):
				self.set_ui_title(info, filename)
				return True
		except:
			uiutil.Message.file_open_failed(path)
		return False

	def do_add(self, info):
		ps = PanelSelector()
		ps.edit_traits()
		mainwindow = info.ui.context['object']
		for s in ps.selected:
			mainwindow.add_tab(PanelMapper.get_class_by_tablabel(s))

	def do_python(self, info):
		PythonWindow().edit_traits()

	def do_about(self, info):
		AboutWindow().edit_traits()

	def do_export(self, info):
		# mostly borrowed from Matplotlib's NavigationToolbar2Wx.save()
		mainwindow = info.ui.context['object']
		canvas = mainwindow.figure.canvas
		# Fetch the required filename and file type.
		filetypes, exts, filter_index = canvas._get_imagesave_wildcards()
		default_file = "image." + canvas.get_default_filetype()
		dlg = wx.FileDialog(info.ui.control, "Save to file", "", default_file, filetypes, wx.SAVE|wx.OVERWRITE_PROMPT)
		dlg.SetFilterIndex(filter_index)
		if dlg.ShowModal() == wx.ID_OK:
			dirname  = dlg.GetDirectory()
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
				uiutil.Message.file_save_failed(path)


ICON_PATH = [os.path.join(os.path.dirname(__file__), 'icons')]
def GetIcon(id):
	return ImageResource(id, search_path=ICON_PATH)


class App(HasTraits):
	plot = Instance(plot.Plot)
	figure = Instance(matplotlib.figure.Figure)
	maintab = Instance(MainTab)
	status = DelegatesTo('maintab')
	drawmgr = Instance(uiutil.DrawManager)

	tabs = List(Instance(panels.Tab))

	def on_figure_resize(self, event):
		self.plot.setup_margins()
		self.drawmgr.update_canvas()

	def update_canvas(self):
		wx.CallAfter(self.figure.canvas.draw)

	def add_tab(self, klass, serialized_data=None):
		tab = klass(drawmgr=self.drawmgr, autoscale=self.plot.autoscale)
		if serialized_data is not None:
			tab.from_serialized(serialized_data)
		self.tabs.append(tab)

	def _maintab_default(self):
		return MainTab(mainwindow=self, drawmgr=self.drawmgr)

	def _drawmgr_default(self):
		return uiutil.DrawManager(self.redraw_figure, self.update_canvas)

	def _tabs_changed(self):
		self.drawmgr.redraw_figure()

	def _tabs_items_changed(self, event):
		for removed in event.removed:
			if isinstance(removed, MainTab):
				self.tabs.insert(0, removed)
		self.drawmgr.redraw_figure()

	def _tabs_default(self):
		return [self.maintab]

	def clear(self):
		self.tabs = self._tabs_default()
		for klass in PanelMapper.list_classes:
			klass.number = 0

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
					self.add_tab(PanelMapper.get_class_by_id(id), props)
				except KeyError:
					pass # silently ignore unknown class names for backward and forward compatibility

	def save_project(self, path):
		data = [('general', self.tabs[0].get_serialized())]
		for tab in self.tabs:
			if isinstance(tab, panels.SubplotPanel):
				data.append((PanelMapper.get_id_by_instance(tab), tab.get_serialized()))
		with open(path, 'wb') as fp:
			fp.write('Spacetime\nJSON\n')
			json.dump(data, fp)
		return True

	def has_modifications(self):
		return len(self.tabs) > 1

	def redraw_figure(self):
		self.plot.clear()
		[self.plot.add_subplot(tab.plot) for tab in self.tabs if isinstance(tab, panels.SubplotPanel) and tab.visible]
		self.plot.setup()
		self.plot.draw()
		self.plot.autoscale()

	def _plot_default(self):
		p = plot.Plot.newmatplotlibfigure()
		p.setup()

		# At this moment, the figure has not yet been initialized properly, so delay these calls.
		# This has to be a lambda statement to make a closure on the variables 'p' and 'self'
		wx.CallAfter(lambda: (
						p.figure.canvas.mpl_connect('resize_event', self.on_figure_resize), 
						p.set_xlim_callback(self.maintab.xlim_callback)
		))
		return p

	def _figure_default(self):
		return self.plot.figure

	traits_view = View(
			HSplit(
				Item('figure', editor=MPLFigureEditor(status='status'), dock='vertical'),
				Item('tabs', style='custom', width=200, editor=ListEditor(use_notebook=True, deletable=True, page_name='.tablabel')),
				show_labels=False,
			),
			resizable=True,
			height=700, width=1100,
			buttons=NoButtons,
			title=MainWindowHandler.get_ui_title(),
			toolbar=ToolBar(
				'main',
					Action(name='New', action='do_new', tooltip='New project', image=GetIcon('new')),
					Action(name='Open', action='do_open', tooltip='Open project', image=GetIcon('open')),
					Action(name='Save', action='do_save', tooltip='Save project', image=GetIcon('save')),
				'add',
					Action(name='Add', action='do_add', tooltip='Add graph', image=GetIcon('add')),
				'graph',
					Action(name='Fit', action='do_fit', tooltip='Zoom to fit', image=GetIcon('fit')),
					Action(name='Zoom', action='do_zoom', tooltip='Zoom rectangle', image=GetIcon('zoom')),
					Action(name='Pan', action='do_pan', tooltip='Pan', image=GetIcon('pan')),
				'export',
					Action(name='Export', action='do_export', tooltip='Export', image=GetIcon('export')),
				'python', 
					Action(name='Python', action='do_python', tooltip='Python shell', image=GetIcon('python')),
				'about',
					Action(name='About', action='do_about', tooltip='About', image=GetIcon('about')),
				show_tool_names=False
			),
			statusbar='status',
			handler=MainWindowHandler(),
		)

	def run(self):
		self.configure_traits()


if __name__ == '__main__':
	app = App()
	app.run()
