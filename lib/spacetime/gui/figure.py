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

import matplotlib
matplotlib.use('WXAgg')

import matplotlib.figure, matplotlib.transforms, matplotlib.backends.backend_wx, matplotlib.backends.backend_wxagg, matplotlib.backend_bases
from matplotlib.backend_bases import cursors
import wx

from enthought.traits.api import Str
from enthought.traits.ui.wx.editor import Editor
from enthought.traits.ui.basic_editor_factory import BasicEditorFactory

from .. import util

import logging
logger = logging.getLogger(__name__)


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

	# decorator function
	@staticmethod
	def avoid_callback_loop(*names):
		def decorator(func):
			def decorated(self, *args, **kwargs):
				callback_loops = self.context.canvas._callback_loops
				objs = set(getattr(self, i) for i in names)
				if objs & callback_loops:
					logger.info("avoid_callback_loop: deny (%r + %r)", callback_loops, objs)
					return
				logger.info("avoid_callback_loop: enter (%r + %r)", callback_loops, objs)
				callback_loops |= objs
				try:
					return func(self, *args, **kwargs)
				finally:
					callback_loops -= objs
					logger.info("avoid_callback_loop: end (%r)", callback_loops)
			decorated.__name__ = func.__name__
			return decorated
		return decorator
