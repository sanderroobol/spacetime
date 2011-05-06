import matplotlib
matplotlib.use('WXAgg')

import matplotlib.figure, matplotlib.transforms, matplotlib.backends.backend_wx, matplotlib.backends.backend_wxagg, matplotlib.backend_bases
from matplotlib.backend_bases import cursors
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

	@staticmethod
	def event2coords(ax, event):
		try:
			xdata, ydata = ax.transData.inverted().transform_point((event.x, event.y))
		except ValueError:
			return '???', '???'
		else:
			return ax.format_xdata(xdata), ax.format_ydata(ydata)

	def build_coord_str(self, axes, event):
		all_strs = [self.event2coords(a, event) for a in axes]
		xs, ys = zip(*all_strs)
		 
		if len(set(xs)) == 1:
			xs = xs[0].strip()
		else:
			xs = '({0})'.format(', '.join(i.strip() for i in xs))

		if len(set(ys)) == 1:
			ys = ys[0].strip()
		else:
			ys = '({0})'.format(', '.join(i.strip() for i in ys))

		return 'x={0}, y={1}'.format(xs, ys)

	def mouse_move(self, event):
		# adapted from matplotlib.backend_bases.NavigationToolbar2.mouse_move

		if not event.inaxes or not self._active:
			if self._lastCursor != cursors.POINTER:
				self.set_cursor(cursors.POINTER)
				self._lastCursor = cursors.POINTER
		else:
			if self._active=='ZOOM':
				if self._lastCursor != cursors.SELECT_REGION:
					self.set_cursor(cursors.SELECT_REGION)
					self._lastCursor = cursors.SELECT_REGION
			elif (self._active=='PAN' and
				  self._lastCursor != cursors.MOVE):
				self.set_cursor(cursors.MOVE)

				self._lastCursor = cursors.MOVE

		if event.inaxes and event.inaxes.get_navigate():

			all_inaxes = [a for a in self.canvas.figure.get_axes() if a.in_axes(event)]
			try:
				s = self.build_coord_str(all_inaxes, event)
			except ValueError: pass
			except OverflowError: pass
			else:
				if len(self.mode):
					self.set_message('{0}, {1}'.format(self.mode, s))
				else:
					self.set_message(s)
		else: self.set_message(self.mode)

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
