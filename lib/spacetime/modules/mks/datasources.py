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

import numpy
import datetime

from ... import util
from ..generic.datasources import MultiTrend, DataChannel


class PeakJump(MultiTrend):
	lastdt = None
	ampm = None

	def parsetime(self, s):
		s = s.strip('"')
		dt = util.localtz.localize(datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S'))
		# FIXME: this fileformat uses a 12-hour clock but without AM/PM...
		# Try to guess AM/PM when we pass noon/midnight
		# Tricky situations to deal with:
		# day N 11:59 (AM) -> day N 12:00 (PM)
		# day N 11:59 (PM) -> day N+1 12:00 (AM)
		# day N 12:59 (AM) -> day N 1:00 (AM) (correct 12:59 to 0:59)
		# day N 12:59 (PM) -> day N 1:00 (PM) (correct 1:00 to 13:00)
		return util.mpldtfromdatetime(dt)

	def __init__(self, *args, **kwargs):
		super(PeakJump, self).__init__(*args, **kwargs)
		with open(self.filename) as fp:
			while 1:
				line = fp.readline()
				if line == '':
					return
				if line.strip() == '"[Scan Data (Pressures in mBar)]"':
					fp.readline()
					break
			header = fp.readline().split(',')
			self.masses = [h.strip('"') for h in header[2:-1]]
			data = []
			times = []
			while 1:
				line = fp.readline()
				if line == '':
					break
				ld = line.split(',')
				times.append(self.parsetime(ld[0]))
				data.append([float(i) for i in ld[2:-1]])

		self.data = numpy.array(data)
		self.time = numpy.array(times)

		self.channels = [DataChannel(time=self.time, value=self.data[:, i], id=m) for i, m in enumerate(self.masses)]
