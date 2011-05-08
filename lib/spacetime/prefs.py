import os
import shutil
import platform
try:
	import cPickle as pickle
except ImportError:
	import pickle

from . import util

import logging
logger = logging.getLogger(__name__)

def _win32_get_appdata():
	# inspired by Ryan Ginstrom's winpaths module
	
	import ctypes
	from ctypes import wintypes, windll

	CSIDL_APPDATA = 26

	SHGetFolderPathW = windll.shell32.SHGetFolderPathW
	SHGetFolderPathW.argtypes = (
		wintypes.HWND,
		ctypes.c_int,
		wintypes.HANDLE,
		wintypes.DWORD,
 		wintypes.LPCWSTR
	)

	path = wintypes.create_unicode_buffer(wintypes.MAX_PATH)
	result = SHGetFolderPathW(0, CSIDL_APPDATA, 0, 0, path)
	if result == 0:
		return path.value
	else:
		raise Exception('SHGetFolderPathW failed')

def get_prefs_path():
	if platform.system() == 'Windows':
		try:
			appdir = _win32_get_appdata()
			stdir = os.path.join(appdir, 'Spacetime')
			if not os.path.exists(stdir):
				os.mkdir(stdir)
		except:
			pass
		else:
			return os.path.join(stdir, 'preferences')
	return os.path.join(os.path.expanduser('~'), '.spacetime.prefs')


class Storage(object):
	def __init__(self):
		self.filename = get_prefs_path()
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
			ui.control.SetSize(info.size)
		if info.position:
			ui.control.SetPosition(info.position)

	def save_window(self, id, ui):
		info = self.data.windows[id]
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
