import matplotlib
matplotlib.use('WXAgg')

import matplotlib.figure, matplotlib.transforms, matplotlib.backends.backend_wx, matplotlib.backends.backend_wxagg
import wx

from enthought.traits.api import Str
from enthought.traits.ui.wx.editor import Editor
from enthought.traits.ui.basic_editor_factory import BasicEditorFactory


class ModifiedToolbar(matplotlib.backends.backend_wx.NavigationToolbar2Wx):
	def __init__(self, statuscallback, *args, **kwargs):
		super(ModifiedToolbar, self).__init__(*args, **kwargs)
		self.statuscallback = statuscallback

	def set_message(self, s):
		self.statuscallback(s)


class _MPLFigureEditor(Editor):
	scrollable  = True
	status = Str

	def init(self, parent):
		self.control = self._create_canvas(parent)
		self.set_tooltip()
		self.sync_value(self.factory.status, 'status', 'to')

	def update_editor(self):
		pass

	def _create_canvas(self, parent):
		mpl_control = matplotlib.backends.backend_wxagg.FigureCanvasWxAgg(parent, -1, self.value)
		self.value.toolbar = ModifiedToolbar(self.set_status, mpl_control)
		return mpl_control

	def set_status(self, s):
		self.status = s


class MPLFigureEditor(BasicEditorFactory):
	klass = _MPLFigureEditor

	status = Str
