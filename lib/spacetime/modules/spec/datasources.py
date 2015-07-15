# This file is part of Spacetime.
#
# Copyright 2010-2014 Leiden University.
# Spec module written by Willem Onderwaater.
#
# Spacetime is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
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

import datetime
import numpy

try:
    from PyMca import specfilewrapper
except ImportError:
    from PyMca5.PyMca import specfilewrapper

from ... import util
from ..generic.datasources import MultiTrend, DataChannel

class Specfile(MultiTrend):
	lastdt = None
	ampm = None

	@staticmethod
	def is_zap(scan):
		return scan.command().startswith('zap')

	def parsetime(self, s):
		dt = util.localtz.localize(datetime.datetime.strptime(s, '%a %b %d %H:%M:%S %Y'))
		return util.mpldtfromdatetime(dt)

	def getspecmax(self):
		return max(self.scannumbers)

	def getspecmin(self):
		return min(self.scannumbers)

	def __init__(self, *args, **kwargs):
		super(Specfile, self).__init__(*args, **kwargs)
		self.spec = specfilewrapper.Specfile(self.filename)
		self.scannumbers = list(scan.number() for scan in self.spec)
		self.loaddata(self.getspecmin(),self.getspecmin())

	def speciter(self, start, stop):
		for index in range(self.scannumbers.index(start), self.scannumbers.index(stop) + 1):
			yield self.spec[index]

	def loaddata(self, start, stop):
		alllabels = numpy.unique(numpy.hstack(scan.alllabels() for scan in self.speciter(start, stop)))

		def get_data(scan):
			indices = list(list(alllabels).index(label) for label in scan.alllabels())
			try:
				scandata = numpy.zeros((len(alllabels), scan.lines() + 1)) # add an extra line of NaNs to separate scans in a plot
				scandata[...] = numpy.nan
				scandata[indices, :-1] = scan.data()
			except specfilewrapper.specfile.error:
				scandata = numpy.zeros((len(alllabels), 0))
			return scandata
		data = numpy.hstack(get_data(scan) for scan in self.speciter(start, stop))

		times = []
		for scan in self.speciter(start, stop):
			if self.is_zap(scan):
				try:
					acquisitiontime = int(scan.command().split(' ')[-2]) / (24. * 3600 * 1000)
					start = self.parsetime(scan.date())
					times.extend(list(numpy.arange(scan.lines()) * acquisitiontime + start))
				except specfilewrapper.specfile.error:
					pass
			else:
				try:
					start = self.parsetime(scan.date())
					scantime = scan.datacol('Epoch')
					times.extend(list((scantime - scantime[0]) / (24. * 3600) + start))
				except specfilewrapper.specfile.error:
					pass
			times.append(numpy.nan) # also extra NaN in time array

		time=numpy.array(times)
		self.channels = [DataChannel(time=time, value=data[i,:], id=m) for i, m in enumerate(alllabels)]

