import matplotlib
matplotlib.use('WXAgg')

import matplotlib.figure, matplotlib.transforms, matplotlib.backends.backend_wx, matplotlib.backends.backend_wxagg, matplotlib.backend_bases
import wx

from enthought.traits.api import Str
from enthought.traits.ui.wx.editor import Editor
from enthought.traits.ui.basic_editor_factory import BasicEditorFactory


class ModifiedToolbar(matplotlib.backends.backend_wx.NavigationToolbar2Wx):
	def __init__(self, canvas, statuscallback):
		matplotlib.backend_bases.NavigationToolbar2.__init__(self, canvas)
		self.canvas = canvas
		self._idle = True
		self.statbar = None
		self.statuscallback = statuscallback

	def set_message(self, s):
		self.statuscallback(s)

	def _init_toolbar(self):
		self._NTB2_BACK    = None
		self._NTB2_FORWARD = None
		self._NTB2_PAN     = None
		self._NTB2_ZOOM    = None

	def ToggleTool(self, *args, **kwargs):
		pass

	def EnableTool(self, *args, **kwargs):
		pass


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
		self.value.toolbar = ModifiedToolbar(mpl_control, self.set_status)
		return mpl_control

	def set_status(self, s):
		self.status = s


class MPLFigureEditor(BasicEditorFactory):
	klass = _MPLFigureEditor

	status = Str
