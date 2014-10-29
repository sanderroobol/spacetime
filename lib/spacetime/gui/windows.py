# This file is part of Spacetime.
#
# Copyright 2010-2014 Leiden University.
# Written by Sander Roobol.
#
# Spacetime is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Spacetime is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import traits.api as traits
import traitsui.api as traitsui

import matplotlib.figure
import wx

from . import support
from .figure import MPLFigureEditor
from .. import modules, version
from ..modules import loader


class GUIModuleTreeGUI(traits.HasTraits):
	id = traits.Str
	label = traits.Str
	desc = traits.Str

	traits_view = traitsui.View(traitsui.VGroup(
			traitsui.Item('label', style='readonly', emphasized=True),
			traitsui.Item('desc', style='readonly', resizable=True, editor=traitsui.TextEditor(multi_line=True)),
			show_labels=False,
			scrollable=False,
		),
		width=100,
	)


class GUIModuleTreeModule(traits.HasTraits):
	label = traits.Str
	desc = traits.Str
	guis = traits.List(GUIModuleTreeGUI)

	traits_view = traitsui.View(traitsui.VGroup(
			traitsui.Item('label', style='readonly', emphasized=True),
			traitsui.Item('desc', style='readonly', resizable=True, editor=traitsui.TextEditor(multi_line=True)),
			show_labels=False,
		),
		width=100,
	)


class GUIModuleTreeRoot(traits.HasTraits):
	modules = traits.List(traits.Module)
	traits_view = traitsui.View()


class GUIModuleSelectorHandler(traitsui.Controller):
	def on_dclick(self, obj):
		# to distinguish a closing-the-window-by-a-doubleclick from
		# closing-the-window-by-closing-the-window:
		self.info.ui.context['object'].dclick = True
		# calling dispose() triggers a segfault on Linux and Windows...
		# CallAfter avoids it but still triggers an GTK assertion
		wx.CallAfter(self.info.ui.dispose)


class GUIModuleSelector(support.UtilityWindow):
	moduleloader = traits.Instance(loader.Loader)
	selected = traits.List()
	root = traits.Instance(GUIModuleTreeRoot)
	dclick = False

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
		if gms.run().result or gms.dclick:
			tabs = [context.app.get_new_tab(gms.moduleloader.get_class_by_id(id)) for id in gms.iter_selected()]
			if live:
				context.app.tabs.extend(tabs)
				context.app.tabs_selected = tabs[0]
			return tabs
		return []

	traits_view = traitsui.View(
		traitsui.Group(
			traitsui.Item('root', editor=traitsui.TreeEditor(editable=True, on_dclick='handler.on_dclick', selection_mode='extended', selected='selected', hide_root=True, nodes=[
				traitsui.TreeNode(node_for=[GUIModuleTreeRoot], auto_open=True, children='modules', label='label'),
				traitsui.TreeNode(node_for=[GUIModuleTreeModule], auto_open=True, children='guis', label='label'),
				traitsui.TreeNode(node_for=[GUIModuleTreeGUI], label='label'),
			])),
			show_labels=False,
			padding=5,
		),
		title='Select subgraph type',
		height=400,
		width=600,
		buttons=traitsui.OKCancelButtons,
		kind='livemodal',
		handler=GUIModuleSelectorHandler(),
		close_result=False,
	)


class GraphManagerHandler(traitsui.Handler):
	# this handler is required in order to set the GraphManager window as
	# parent when launching the GUIModuleSelector window
	add = traits.Button
	# the other buttons can be dealt with in the GraphManager model

	def handler_add_changed(self, info):
		gm = info.ui.context['object']
		gm.tabs.extend(GUIModuleSelector.run_static(gm.context.fork(uiparent=info.ui.control), live=False))
		gm.selected = len(gm.tab_labels) - 1


class GraphManager(support.UtilityWindow):
	tabs = traits.List(traits.Instance(modules.generic.gui.Tab))
	tab_labels = traits.Property(depends_on='tabs')
	selected = traits.Int(-1)
	selected_any = traits.Property(depends_on='selected')
	selected_not_first = traits.Property(depends_on='selected')
	selected_not_last = traits.Property(depends_on='selected, tab_labels')

	remove = traits.Button
	move_up = traits.Button
	move_down = traits.Button

	@traits.cached_property
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
				if gm.selected_any:
					context.app.tabs_selected = gm.tabs[gm.selected+1]

	traits_view = traitsui.View(
		traitsui.HGroup(
			traitsui.Item('tab_labels', editor=traitsui.ListStrEditor(editable=False, selected_index='selected')),
			traitsui.VGroup(
				traitsui.Group(
					traitsui.Item('handler.add'),
					traitsui.Item('remove', enabled_when='selected_any'),
					show_labels=False,
				),
				traitsui.Group(
					traitsui.Item('move_up', enabled_when='selected_not_first'),
					traitsui.Item('move_down', enabled_when='selected_not_last'),
					show_labels=False,
				),
			),
			show_labels=False,
		),
		height=400, width=400,
		resizable=True,
		title='Manage graphs',
		kind='livemodal',
		buttons=traitsui.OKCancelButtons,
		handler=GraphManagerHandler(),
		close_result=False,
	)


class PythonWindow(support.PersistantGeometryWindow):
	prefs_id = 'python'
	shell = traits.PythonValue({})
	traits_view = traitsui.View(
		traitsui.Item('shell', show_label=False, editor=traitsui.ShellEditor(share=False)),
		title='Python console',
		height=600,
		width=500,
		resizable=True,
		handler=support.PersistantGeometryHandler(),
	)


class AboutWindow(support.UtilityWindow):
	title = traits.Str("{0} {1}".format(version.name, version.version))
	desc = traits.Str("""Copyright 2010-2013 Leiden University.
Written by Sander Roobol <roobol@physics.leidenuniv.nl>.

Spacetime is free software: you can redistribute it and/or modify it under the terms of the 
GNU General Public License as published by the Free Software Foundation, either version
3 of the License, or (at your option) any later version.

The Spacetime logo contains STM data by Kees Herbschleb, Catal. Today 154, 61 (2010).""")
	image = traits.Any

	traits_view = traitsui.View(
		traitsui.HGroup(
			traitsui.Group(
				traitsui.Item('image', editor=traitsui.ImageEditor(image=support.GetIcon('spacetime-logo'))),
				show_labels=False,
				padding=5,
			),
			traitsui.Group(
				traitsui.Item('title', emphasized=True, style='readonly'),
				traitsui.Item('desc', style='readonly', editor=traitsui.TextEditor(multi_line=True)),
				show_labels=False,
				padding=5,
			),
		),
		title='About {0}'.format(version.name),
		buttons=[traitsui.OKButton],
		kind='livemodal',
	)


class FigureWindowHandler(support.PersistantGeometryHandler):
	def close(self, info, is_ok=None):
		super(FigureWindowHandler, self).close(info, is_ok)
		figurewindow = info.ui.context['object']
		figurewindow.app._close_presentation_mode()
		return True


class FigureWindow(support.PersistantGeometryWindow):
	prefs_id = 'figure'

	app = traits.Instance(traits.HasTraits)
	figure = traits.Instance(matplotlib.figure.Figure, args=())
	status = traits.DelegatesTo('app')

	traits_view = traitsui.View(
		traitsui.Group(
			traitsui.Item('figure', editor=MPLFigureEditor(status='status')),
			show_labels=False,
		),
		resizable=True,
		height=600, width=800,
		buttons=traitsui.NoButtons,
		title=version.name,
		statusbar='status',
		icon=support.GetIcon('spacetime-icon'),
		handler=FigureWindowHandler(),
		kind='live',
	)

class ExportDialog(support.UtilityWindow):
	filetype = traits.Str('Portable Network Graphics (*.png)')
	extension = traits.Property(depends_on='filetype')
	wxfilter = traits.Property(depends_on='filetype') 

	filetypes = traits.List(traits.Str)
	extensions = traits.List(traits.Str)
	wxfilters = traits.List(traits.Str)

	dpi = traits.Range(low=1, high=10000000, value=72)

	canvas_width = traits.Float(1024.)
	canvas_height = traits.Float(768.)
	canvas_unit = traits.Enum('px', 'cm', 'inch')
	figsize = traits.Property(depends_on='canvas_width, canvas_height, canvas_unit')

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

	traits_view = traitsui.View(
		traitsui.Item('filetype', editor=traitsui.EnumEditor(name='filetypes')),
		traitsui.Item('dpi'),
		traitsui.Group(
			traitsui.Item('canvas_width', label='Width'),
			traitsui.Item('canvas_height', label='Height'),
			traitsui.Item('canvas_unit', label='Unit'),
			label='Canvas size',
			show_border=True,
		),
		buttons=traitsui.OKCancelButtons,
		title='Export',
		resizable=False,
		kind='livemodal',
		close_result=False,
	)

class MovieDialogMainTab(traits.HasTraits):
	label = traits.Str('General')
	format = traits.Str('mp4')
	codec = traits.Str('libx264')
	ffmpeg_options = traits.Str('-x264opts crf=12 -preset medium -profile:v main -pix_fmt yuv420p -threads 0')

	frame_width = traits.Int(1024)
	frame_height = traits.Int(768)
	dpi = traits.Range(low=1, high=10000000, value=72)
	frame_rate = traits.Int(5)

	animation_view = traitsui.View(traitsui.Group(
		traitsui.Group(
			traitsui.Item('frame_width', label='Width'),
			traitsui.Item('frame_height', label='Height'),
			traitsui.Item('dpi'),
			label='Dimensions',
			show_border=True,
		),
		traitsui.Group(
			traitsui.Item('frame_rate'),
			traitsui.Item('format'),
			traitsui.Item('codec'),
			traitsui.Item('ffmpeg_options', label='Extra options', tooltip='Extra options to be passed to the ffmpeg executable'),
			label='Movie options',
			show_border=True,
		),
	))


class MovieDialog(support.UtilityWindow):
	maintab = traits.Instance(MovieDialogMainTab, args=())
	tabs = traits.List(traits.HasTraits)

	format = traits.DelegatesTo('maintab')
	codec = traits.DelegatesTo('maintab')
	ffmpeg_options = traits.DelegatesTo('maintab')
	frame_width = traits.DelegatesTo('maintab')
	frame_height = traits.DelegatesTo('maintab')
	dpi = traits.DelegatesTo('maintab')
	frame_rate = traits.DelegatesTo('maintab')

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

	traits_view = traitsui.View(
		traitsui.Group(
			traitsui.Item('tabs', style='custom', editor=traitsui.ListEditor(use_notebook=True, page_name='.label', view='animation_view')),
			show_labels=False,
		),
		title='Movie',
		resizable=False,
		width=400,
		kind='livemodal',
		buttons=traitsui.OKCancelButtons,
		close_result=False,
	)
