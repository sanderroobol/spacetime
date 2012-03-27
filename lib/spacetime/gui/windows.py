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

from enthought.traits.api import *
from enthought.traits.ui.api import *

import matplotlib.figure

from . import support
from .figure import MPLFigureEditor
from .. import modules, version


class GUIModuleTreeGUI(HasTraits):
	id = Str
	label = Str
	desc = Str

	traits_view = View(VGroup(
			Item('label', style='readonly', emphasized=True),
			Item('desc', style='readonly', resizable=True, editor=TextEditor(multi_line=True)),
			show_labels=False,
			scrollable=False,
		),
		width=100,
	)


class GUIModuleTreeModule(HasTraits):
	label = Str
	desc = Str
	guis = List(GUIModuleTreeGUI)

	traits_view = View(VGroup(
			Item('label', style='readonly', emphasized=True),
			Item('desc', style='readonly', resizable=True, editor=TextEditor(multi_line=True)),
			show_labels=False,
		),
		width=100,
	)


class GUIModuleTreeRoot(HasTraits):
	modules = List(Module)
	traits_view = View()


class GUIModuleSelectorHandler(Controller):
	def on_dclick(self, obj):
		self.info.ui.control.Close()


class GUIModuleSelector(support.UtilityWindow):
	moduleloader = Instance(modules.Loader)
	selected = List()
	root = Instance(GUIModuleTreeRoot)

	def _moduleloader_default(self):
		return self.context.app.moduleloader

	def _root_default(self):
		modules = []
		for name, guis in self.moduleloader.guis_by_module.iteritems():
			treeguis = [GUIModuleTreeGUI(id=gui.id, label=gui.label, desc=gui.desc) for gui in guis]
			treeguis.sort(key=lambda x:x.label)
			if treeguis:
				module = self.moduleloader.get_module_by_name(name)
				modules.append(GUIModuleTreeModule(label=module.label, desc=module.desc, guis=treeguis))
		modules.sort(key=lambda x: x.label)
		return GUIModuleTreeRoot(modules=modules)

	def iter_selected(self):
		for s in self.selected:
			if isinstance(s, GUIModuleTreeGUI):
				yield s.id

	@classmethod
	def run_static(cls, context, live=True):
		gms = cls(context=context)
		if gms.run().result:
			tabs = [context.app.get_new_tab(gms.moduleloader.get_class_by_id(id)) for id in gms.iter_selected()]
		else:
			tabs = []
		if live:
			context.app.tabs.extend(tabs)
		return tabs

	traits_view = View(
		Group(
			Item('root', editor=TreeEditor(editable=True, on_dclick='handler.on_dclick', selection_mode='extended', selected='selected', hide_root=True, nodes=[
				TreeNode(node_for=[GUIModuleTreeRoot], auto_open=True, children='modules', label='label'),
				TreeNode(node_for=[GUIModuleTreeModule], auto_open=True, children='guis', label='label'),
				TreeNode(node_for=[GUIModuleTreeGUI], label='label'),
			])),
			show_labels=False,
			padding=5,
		),
		title='Select subgraph type',
		height=400,
		width=600,
		buttons=OKCancelButtons,
		kind='livemodal',
		handler=GUIModuleSelectorHandler()
	)


class GraphManagerHandler(Handler):
	# this handler is required in order to set the GraphManager window as
	# parent when launching the GUIModuleSelector window
	add = Button
	# the other buttons can be dealt with in the GraphManager model

	def handler_add_changed(self, info):
		gm = info.ui.context['object']
		gm.tabs.extend(GUIModuleSelector.run_static(gm.context.fork(uiparent=info.ui.control), live=False))
		gm.selected = len(gm.tab_labels) - 1


class GraphManager(support.UtilityWindow):
	tabs = List(Instance(modules.generic.gui.Tab))
	tab_labels = Property(depends_on='tabs')
	selected = Int(-1)
	selected_any = Property(depends_on='selected')
	selected_not_first = Property(depends_on='selected')
	selected_not_last = Property(depends_on='selected, tab_labels')

	remove = Button
	move_up = Button
	move_down = Button

	@cached_property
	def _get_tab_labels(self):
		return [t.label for t in self.tabs[1:]]

	def _get_selected_any(self):
		return self.selected >= 0

	def _get_selected_not_first(self):
		return self.selected > 0

	def _get_selected_not_last(self):
		return 0 <= self.selected < len(self.tab_labels) - 1

	def _remove_fired(self):
		del self.tabs[self.selected + 1]

	def _move_up_fired(self):
		selected = self.selected + 1
		self.tabs[selected-1], self.tabs[selected] = self.tabs[selected], self.tabs[selected-1]
		self.selected = selected - 2

	def _move_down_fired(self):	
		selected = self.selected + 1
		self.tabs[selected], self.tabs[selected+1] = self.tabs[selected+1], self.tabs[selected]
		self.selected = selected

	@classmethod
	def run_static(cls, context):
		# get non-live behaviour by maintaining our own copy of mainwindow.tabs
		gm = cls(context=context)
		gm.tabs = [t for t in context.app.tabs]
		with context.canvas.hold():
			if gm.run().result:
				context.app.tabs = gm.tabs

	traits_view = View(
		HGroup(
			Item('tab_labels', editor=ListStrEditor(editable=False, selected_index='selected')),
			VGroup(
				Group(
					Item('handler.add'),
					Item('remove', enabled_when='selected_any'),
					show_labels=False,
				),
				Group(
					Item('move_up', enabled_when='selected_not_first'),
					Item('move_down', enabled_when='selected_not_last'),
					show_labels=False,
				),
			),
			show_labels=False,
		),
		height=400, width=400,
		resizable=True,
		title='Manage graphs',
		kind='livemodal',
		buttons=OKCancelButtons,
		handler=GraphManagerHandler(),
	)


class PythonWindow(support.PersistantGeometryWindow):
	prefs_id = 'python'
	shell = PythonValue({})
	traits_view = View(
		Item('shell', show_label=False, editor=ShellEditor(share=False)),
		title='Python console',
		height=600,
		width=500,
		resizable=True,
		handler=support.PersistantGeometryHandler(),
	)


class AboutWindow(support.UtilityWindow):
	title = Str("{0} {1}".format(version.name, version.version))
	desc = Str("""Copyright 2010-2012 Leiden University.
Written by Sander Roobol <roobol@physics.leidenuniv.nl>.

Spacetime is free software: you can redistribute it and/or modify it under the terms of the 
GNU General Public License as published by the Free Software Foundation, either version
3 of the License, or (at your option) any later version.

The Spacetime logo contains STM data by Kees Herbschleb, Catal. Today 154, 61 (2010).""")

	traits_view = View(
		HGroup(
			Group(
				Item('none', editor=ImageEditor(image=support.GetIcon('spacetime-logo'))),
				show_labels=False,
				padding=5,
			),
			Group(
				Item('title', emphasized=True, style='readonly'),
				Item('desc', style='readonly', editor=TextEditor(multi_line=True)),
				show_labels=False,
				padding=5,
			),
		),
		title='About {0}'.format(version.name),
		buttons=[OKButton],
		kind='modal',
	)


class FigureWindowHandler(support.PersistantGeometryHandler):
	def close(self, info, is_ok=None):
		super(FigureWindowHandler, self).close(info, is_ok)
		figurewindow = info.ui.context['object']
		figurewindow.app._close_presentation_mode()
		return True


class FigureWindow(support.PersistantGeometryWindow):
	prefs_id = 'figure'

	app = Instance(HasTraits)
	figure = Instance(matplotlib.figure.Figure, args=())
	status = DelegatesTo('app')

	traits_view = View(
		Group(
			Item('figure', editor=MPLFigureEditor(status='status')),
			show_labels=False,
		),
		resizable=True,
		height=600, width=800,
		buttons=NoButtons,
		title=version.name,
		statusbar='status',
		icon=support.GetIcon('spacetime-icon'),
		handler=FigureWindowHandler(),
		kind='live',
	)

class ExportDialog(support.UtilityWindow):
	filetype = Str('Portable Network Graphics (*.png)')
	extension = Property(depends_on='filetype')
	wxfilter = Property(depends_on='filetype') 

	filetypes = List(Str)
	extensions = List(Str)
	wxfilters = List(Str)

	dpi = Range(low=1, high=10000000, value=72)
	rasterize = Property(depends_on='filetype')

	canvas_width = Float(800)
	canvas_height = Float(600)
	canvas_unit = Enum('px', 'cm', 'inch')
	figsize = Property(depends_on='canvas_width, canvas_height, canvas_unit')

	def _get_rasterize(self):
		ft = self.filetype.lower()
		for i in ('pdf', 'vector', 'postscript', 'metafile'):
			if i in ft:
				return False
		return True

	def _get_extension(self):
		return self.extensions[self.filetypes.index(self.filetype)]

	def _get_wxfilter(self):
		return self.wxfilters[self.filetypes.index(self.filetype)]

	def _get_figsize(self):
		if self.canvas_unit == 'inch':
			return self.canvas_width, self.canvas_height
		elif self.canvas_unit == 'cm':
			return self.canvas_width / 2.54, self.canvas_height / 2.54
		else: # self.canvas_unit == 'px'
			return self.canvas_width / self.dpi, self.canvas_height / self.dpi

	def _canvas_unit_changed(self, old, new):
		if old == 'px' and new == 'inch':
				self.canvas_width  /= self.dpi
				self.canvas_height /= self.dpi
		elif old == 'px' and new == 'cm':
				self.canvas_width  /= self.dpi / 2.54
				self.canvas_height /= self.dpi / 2.54
		elif old == 'cm' and new == 'inch':
				self.canvas_width  /= 2.54
				self.canvas_height /= 2.54
		elif old == 'inch' and new == 'px':
				self.canvas_width  *= self.dpi
				self.canvas_height *= self.dpi
		elif old == 'cm' and new == 'px':
				self.canvas_width  *= self.dpi / 2.54
				self.canvas_height *= self.dpi / 2.54
		elif old == 'inch' and new == 'cm':
				self.canvas_width  *= 2.54
				self.canvas_height *= 2.54

	def run(self):
		mplcanvas = self.context.plot.figure.canvas
		filetypes, exts, filter_index = mplcanvas._get_imagesave_wildcards()
		self.filetypes = filetypes.split('|')[::2]
		self.extensions = exts
		self.wxfilters = ['|'.join(i) for i in zip(self.filetypes, filetypes.split('|')[1::2])]
		return super(ExportDialog, self).run()

	traits_view = View(
		Item('filetype', editor=EnumEditor(name='filetypes')),
		Item('dpi', enabled_when='rasterize'),
		Group(
			Item('canvas_width', label='Width'),
			Item('canvas_height', label='Height'),
			Item('canvas_unit', label='Unit'),
			label='Canvas size',
			show_border=True,
		),
		buttons=OKCancelButtons,
		title='Export',
		resizable=False,
		kind='livemodal',
	)

class MovieDialogMainTab(HasTraits):
	label = Str('General')
	format = Str('mp4')
	codec = Str('libx264')
	ffmpeg_options = Str('-x264opts crf=12 -preset medium -profile main -threads 0')

	frame_width = Int(800)
	frame_height = Int(600)
	dpi = Range(low=1, high=10000000, value=72)
	frame_rate = Int(2)

	animation_view = View(Group(
		Group(
			Item('frame_width', label='Width'),
			Item('frame_height', label='Height'),
			Item('dpi', enabled_when='rasterize'),
			label='Dimensions',
			show_border=True,
		),
		Group(
			Item('frame_rate'),
			Item('format'),
			Item('codec'),
			Item('ffmpeg_options', label='Extra options', tooltip='Extra options to be passed to the ffmpeg executable'),
			label='Movie options',
			show_border=True,
		),
	))


class MovieDialog(support.UtilityWindow):
	maintab = Instance(MovieDialogMainTab, args=())
	tabs = List(HasTraits)

	format = DelegatesTo('maintab')
	codec = DelegatesTo('maintab')
	ffmpeg_options = DelegatesTo('maintab')
	frame_width = DelegatesTo('maintab')
	frame_height = DelegatesTo('maintab')
	dpi = DelegatesTo('maintab')
	frame_rate = DelegatesTo('maintab')

	def get_animate_functions(self):
		return tuple(getattr(tab, 'animate') for tab in self.tabs[1:])

	def get_framecount(self):
		return max(getattr(tab, 'animation_framecount') for tab in self.tabs[1:])

	def run(self):
		self.tabs = [self.maintab]
		for tab in self.context.app.tabs:
			if hasattr(tab, 'animate'):
				self.tabs.append(tab)
		if len(self.tabs) == 1:
			raise RuntimeError('None of the graphs support animation.')
		return super(MovieDialog, self).run()

	traits_view = View(
		Group(
			Item('tabs', style='custom', editor=ListEditor(use_notebook=True, page_name='.label', view='animation_view')),
			show_labels=False,
		),
		title='Movie',
		resizable=False,
		width=400,
		kind='livemodal',
		buttons=OKCancelButtons,
	)
