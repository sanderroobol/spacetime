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

from __future__ import division

from ... import util
from ..generic.datasources import MultiTrend
from . import pypy


class QuaderaScan(MultiTrend):
	def __init__(self, *args, **kwargs):
		super(QuaderaScan, self).__init__(*args, **kwargs)
		self.masses, self.time_data, self.ion_data, self.channels = pypy.loadscan(self.filename)

	def iterimages(self):
		d = util.Struct()
		d.data = self.ion_data.transpose()
		d.tstart = self.time_data[0]
		d.tend = self.time_data[-1]
		d.ybottom = self.masses[0]
		d.ytop = self.masses[-1]
		yield d


class QuaderaMID(MultiTrend):
	channels = None
	masses = None

	def __init__(self, *args, **kwargs):
		super(QuaderaMID, self).__init__(*args, **kwargs)
		self.header, self.masses, self.channels = pypy.loadmid(self.filename)
