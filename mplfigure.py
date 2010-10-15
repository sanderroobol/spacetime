import matplotlib
matplotlib.use('WXAgg')

import matplotlib.figure, matplotlib.transforms, matplotlib.backends.backend_wx, matplotlib.backends.backend_wxagg
import wx

from enthought.traits.ui.wx.editor import Editor
from enthought.traits.ui.basic_editor_factory import BasicEditorFactory


class _MPLFigureEditor(Editor):
	scrollable  = True

	def init(self, parent):
		self.control = self._create_canvas(parent)
		self.set_tooltip()

	def update_editor(self):
		pass

	def _create_canvas(self, parent):
		""" Create the MPL canvas. """
		# The panel lets us add additional controls.
		panel = wx.Panel(parent, -1, style=wx.CLIP_CHILDREN)
		sizer = wx.BoxSizer(wx.VERTICAL)
		panel.SetSizer(sizer)
		# matplotlib commands to create a canvas
		mpl_control = matplotlib.backends.backend_wxagg.FigureCanvasWxAgg(panel, -1, self.value)
		sizer.Add(mpl_control, 1, wx.LEFT | wx.TOP | wx.GROW)
		toolbar = matplotlib.backends.backend_wx.NavigationToolbar2Wx(mpl_control)
		sizer.Add(toolbar, 0, wx.EXPAND)
		self.value.canvas.SetMinSize((10,10))
		return panel


class MPLFigureEditor(BasicEditorFactory):
	klass = _MPLFigureEditor
