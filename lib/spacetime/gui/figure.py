# This file is part of Spacetime.
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

import matplotlib
matplotlib.use('WXAgg')
matplotlib.rc('mathtext', fontset='stixsans', default='regular')

import matplotlib.figure, matplotlib.transforms, matplotlib.backends.backend_wx, matplotlib.backends.backend_wxagg, matplotlib.backend_bases
from matplotlib.backend_bases import cursors
import wx

from traits.api import Str
from traitsui.wx.editor import Editor
from traitsui.basic_editor_factory import BasicEditorFactory

from .. import util

import logging
logger = logging.getLogger(__name__)


class ModifiedToolbar(matplotlib.backends.backend_wx.NavigationToolbar2Wx):
	def __init__(self, canvas, statuscallback):
		matplotlib.backend_bases.NavigationToolbar2.__init__(self, canvas) # skip NavigationToolbar2Wx to keep the toolbar from appearing on Windows
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

	def set_history_buttons(self): # required since matplotlib 1.2.0
		pass

	def zoom(self, *args):
		matplotlib.backend_bases.NavigationToolbar2.zoom(self, *args)
		
	def pan(self, *args):
		matplotlib.backend_bases.NavigationToolbar2.pan(self, *args)

	def drag_pan(self, event):
		# the drag callback in pan/zoom mode, enhanced to allow single-axis operation
		# TODO: turn this into a patch for matplotlib issue 1502
		for a, ind in self._xypress:
			if event.key is None or not event.key.isdigit() or event.key == str(ind):
				a.drag_pan(self._button_pressed, event.key, event.x, event.y)
		self.dynamic_update()


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


class DrawManager(object):
	_hold = 0
	level = 0

	def __init__(self, rebuild, redraw):
		self._rebuild = rebuild
		self._redraw = redraw
		self.subgraphs = []
		self._callback_loops = set()

	def hold(self):
		return util.ContextManager(self.hold_manual, lambda x,y,z: self.release_manual())

	def hold_delayed(self):
		return util.ContextManager(self.hold_manual, lambda x,y,z: wx.CallAfter(self.release_manual))

	def hold_manual(self):
		self._hold += 1

	def release_manual(self):
		if self._hold == 1:
			if self.level & 5 == 5:
				self._rebuild()
				del self.subgraphs[:]
				self._redraw()
			elif self.level & 3 == 3:
				for cb in self.subgraphs:
					cb()
				self._redraw()
			elif self.level & 1:
				self._redraw()
			self.level = 0
		self._hold -= 1

	def rebuild(self):
		if self._hold:
			self.level |= 5
		else:
			self._rebuild()
			self._redraw()
		
	def rebuild_subgraph(self, cb):
		if self._hold:
			self.level |= 3
			self.subgraphs.append(cb)
		else:
			cb()
			self._redraw()
	
	def redraw(self):
		if self._hold:
			self.level |= 1
		else:
			self._redraw()

	def relocate(self, rebuild=None, redraw=None):
		if rebuild is None:
			rebuild = self.rebuild
		if redraw is None:
			redraw = self.redraw
		return self.__class__(rebuild, redraw)


class CallbackLoopManager(object):
	_general_blockade = 0

	def __init__(self):
		self.objects = {}

	def general_blockade(self):
		return util.ContextManager(self._acquire_general_blockade, lambda x,y,z: self._release_general_blockade())

	def _acquire_general_blockade(self):
		self._general_blockade += 1

	def _release_general_blockade(self):
		self._general_blockade -= 1

	def is_avoiding(self, *objs):
		if self._general_blockade:
			logger.debug("is_avoiding: general blockade (%r)", objs)
			return True
		for obj in objs:
			if obj in self.objects:
				logger.debug("is_avoiding: deny (%r + %r)", self.objects, objs)
				return True
		logger.debug("is_avoiding: allow (%r + %r)", self.objects, objs)
		return False

	def avoid(self, *objs):
		return util.ContextManager(lambda: self._acquire(objs), lambda x,y,z: self._release(objs))

	def _acquire(self, objs):
		logger.debug("_acquire: %r", objs)
		for obj in objs:
			if obj in self.objects:
				self.objects[obj] += 1
			else:
				self.objects[obj] = 1
		
	def _release(self, objs):
		logger.debug("_release: %r", objs)
		for obj in objs:
			self.objects[obj] -= 1
			if not self.objects[obj]:
				del self.objects[obj]

	@staticmethod
	def decorator(*names):
		def _decorator(func):
			def _decorated(self, *args, **kwargs):
				callbacks = self.context.callbacks
				objs = tuple(getattr(self, i) for i in names)
				if not callbacks.is_avoiding(*objs):
					with callbacks.avoid(*objs):
						return func(self, *args, **kwargs)
			_decorated.original = func
			_decorated.__name__ = func.__name__
			return _decorated
		return _decorator
