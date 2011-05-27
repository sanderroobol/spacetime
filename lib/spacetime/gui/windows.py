from enthought.traits.api import *
from enthought.traits.ui.api import *

import matplotlib.figure

from . import support
from .figure import MPLFigureEditor
from .. import modules, version


class PanelTreePanel(HasTraits):
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


class PanelTreeModule(HasTraits):
	label = Str
	desc = Str
	panels = List(PanelTreePanel)

	traits_view = View(VGroup(
			Item('label', style='readonly', emphasized=True),
			Item('desc', style='readonly', resizable=True, editor=TextEditor(multi_line=True)),
			show_labels=False,
		),
		width=100,
	)


class PanelTreeRoot(HasTraits):
	modules = List(PanelTreeModule)
	traits_view = View()


class PanelSelector(HasTraits):
	panelmgr = Instance(modules.PanelManager)
	selected = List()
	root = Instance(PanelTreeRoot)

	def _root_default(self):
		modules = []
		for name, panels in self.panelmgr.panels_by_module.iteritems():
			treepanels = [PanelTreePanel(id=panel.id, label=panel.label, desc=panel.desc) for panel in panels]
			if treepanels:
				module = self.panelmgr.get_module_by_name(name)
				modules.append(PanelTreeModule(label=module.label, desc=module.desc, panels=treepanels))
		return PanelTreeRoot(modules=modules)

	def iter_selected(self):
		for s in self.selected:
			if isinstance(s, PanelTreePanel):
				yield s.id

	@staticmethod
	def run(mainwindow, live=True):
		ps = PanelSelector(panelmgr=mainwindow.panelmgr)
		ps.edit_traits(parent=mainwindow.ui.control, scrollable=False)
		tabs = [mainwindow.get_new_tab(mainwindow.panelmgr.get_class_by_id(id)) for id in ps.iter_selected()]
		if live:
			mainwindow.tabs.extend(tabs)
		return tabs

	traits_view = View(
		Group(
			Item('root', editor=TreeEditor(editable=True, selection_mode='extended', selected='selected', hide_root=True, nodes=[
				TreeNode(node_for=[PanelTreeRoot], auto_open=True, children='modules', label='label'),
				TreeNode(node_for=[PanelTreeModule], auto_open=True, children='panels', label='label'),
				TreeNode(node_for=[PanelTreePanel], label='label'),
			])),
			show_labels=False,
			padding=5,
		),
		title='Select subgraph type',
		height=400,
		width=600,
		buttons=OKCancelButtons,
		kind='modal',
	)


class GraphManager(HasTraits):
	mainwindow = Instance(HasTraits)
	tabs = List(Instance(modules.generic.panels.Tab))
	tab_labels = Property(depends_on='tabs')
	selected = Int(-1)
	selected_any = Property(depends_on='selected')
	selected_not_first = Property(depends_on='selected')
	selected_not_last = Property(depends_on='selected, tab_labels')
	add = Event
	remove = Event
	move_up = Event
	move_down = Event

	def _get_tab_labels(self):
		return [t.label for t in self.tabs[1:]]

	def _get_selected_any(self):
		return self.selected >= 0

	def _get_selected_not_first(self):
		return self.selected > 0

	def _get_selected_not_last(self):
		return 0 <= self.selected < len(self.tab_labels) - 1

	def _add_fired(self):
		self.tabs.extend(PanelSelector.run(self.mainwindow, live=False))
		self.selected = len(self.tab_labels) - 1

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

	@staticmethod
	def run(mainwindow, parent=None):
		# get non-live behaviour by maintaining our own copy of mainwindow.tabs
		gm = GraphManager(mainwindow=mainwindow)
		gm.tabs = [t for t in mainwindow.tabs]
		with mainwindow.drawmgr.hold():
			if gm.edit_traits(parent=parent).result:
				mainwindow.tabs = gm.tabs

	traits_view = View(
		HGroup(
			Item('tab_labels', editor=ListStrEditor(editable=False, selected_index='selected')),
			VGroup(
				Group(
					Item('add', editor=ButtonEditor()),
					Item('remove', editor=ButtonEditor(), enabled_when='selected_any'),
					show_labels=False,
				),
				Group(
					Item('move_up', editor=ButtonEditor(), enabled_when='selected_not_first'),
					Item('move_down', editor=ButtonEditor(), enabled_when='selected_not_last'),
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
	)


class PythonWindow(support.PersistantGeometry):
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


class AboutWindow(HasTraits):
	title = Str("{0} {1}".format(version.name, version.version))
	desc = Str('Copyright 2010-2011 Leiden University.\nWritten by Sander Roobol <roobol@physics.leidenuniv.nl>.\n\nRedistribution outside Leiden University is not permitted.')

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
		figurewindow.mainwindow._close_presentation_mode()
		return True


class FigureWindow(support.PersistantGeometry):
	prefs_id = 'figure'

	mainwindow = Any
	figure = DelegatesTo('mainwindow')
	status = DelegatesTo('mainwindow')

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
	)
