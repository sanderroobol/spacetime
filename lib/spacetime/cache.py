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

import sqlite3
try:
	import cPickle as pickle
except ImportError:
	import pickle

import logging
logger = logging.getLogger(__name__)

from . import util


# sqlite requires the buffer type for blobs, but pickle doesn't grok that
def obj2blob(obj):
	return buffer(pickle.dumps(obj, pickle.HIGHEST_PROTOCOL))

def blob2obj(blob):
	return pickle.loads(str(blob))


class Cache(object):
	def __init__(self, table):
		self.table = table
		self.conn = sqlite3.connect(util.get_persistant_path('cache'))
		self.cur = self.conn.cursor()
		self.cur.execute('CREATE TABLE IF NOT EXISTS {0} (key BLOB PRIMARY KEY, value BLOB)'.format(self.table))
		self.pending = []

	def close(self):
		self.commit_pending()
		self.conn.close()

	def commit_pending(self):
		self.cur.executemany('INSERT INTO {0} (key, value) VALUES (?, ?)'.format(self.table), self.pending)
		self.conn.commit()

	def lookup(self, key):
		self.cur.execute('SELECT * FROM {0} WHERE key = ?'.format(self.table), (key,))
		data = self.cur.fetchone()
		if data:
			key, value = data
			return blob2obj(value)

	def put(self, key, value):
		self.pending.append((key, obj2blob(value)))

	def clear(self):
		self.cur.execute('DELETE FROM {0}'.format(self.table))

	def __enter__(self):
		return self

	def __exit__(self, type, value, traceback):
		self.close()
