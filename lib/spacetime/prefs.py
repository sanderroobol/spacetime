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

import os
import shutil
try:
	import cPickle as pickle
except ImportError:
	import pickle

from . import util

import logging
logger = logging.getLogger(__name__)

class Storage(object):
	def __init__(self):
		self.filename = util.get_persistant_path('preferences')
		self.tempname = '{0}.tmp'.format(self.filename)

		self.data = util.Struct()

		try:
			with open(self.filename, 'rb') as fp:
				self.data = pickle.load(fp)
		except:
			logger.warning("could not load preferences from '%s'", self.filename)

	def close(self):
		fp = open(self.tempname, 'wb')
		try:
			pickle.dump(self.data, fp, 2)
			fp.close()
			fp = None
			shutil.move(self.tempname, self.filename)
		finally:
			if fp:
				fp.close()
			try:
				os.remove(self.tempname)
			except:
				pass

	def restore_window(self, id, ui):
		info = self.data.windows[id]
		if info.size:
			if info.size == 'max':
				ui.control.Maximize(True)
			else:
				ui.control.SetSize(info.size)
		if info.position:
			ui.control.SetPosition(info.position)

	def save_window(self, id, ui):
		info = self.data.windows[id]
		if ui.control.IsMaximized() or ui.control.IsFullScreen():
			info.size = 'max'
		else:
			info.size = ui.control.GetSizeTuple()
		info.position = ui.control.GetPositionTuple()

	def add_recent(self, id, value, max=10):
		if not self.data.recent[id]:
			self.data.recent[id] = []
		recent = self.data.recent[id]
		try:
			old = recent.index(value)
		except ValueError:
			pass
		else:
			del recent[old]
		recent.insert(0, value)
		del recent[max:]

	def get_recent(self, id):
		if self.data.recent[id]:
			return self.data.recent[id]
		else:
			return []

	def set_path(self, id, value):
		self.data.paths[id] = value

	def get_path(self, id):
		value = self.data.paths[id]
		if value:
			return value
		return '.'
