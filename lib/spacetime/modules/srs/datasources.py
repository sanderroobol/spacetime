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

import numpy

from ... import util
from ..generic.datasources import MultiTrend, DataChannel


class SRSScan(MultiTrend):
	def __init__(self, *args, **kwargs):
		super(SRSScan, self).__init__(*args, **kwargs)
		with open(self.filename) as fp:
			# parse header looking for start time
			line = ''
			while not line.startswith('Start time, '):
				line = fp.readline().strip()
			starttime = util.mpldtstrptime(line[12:], '%b %d, %Y  %I:%M:%S %p')

			# read rest of header until blank line indicating start of channel table
			while line:
				line = fp.readline().strip()

			# read channel info, stop on blank line
			self.channel_labels = []
			while True:
				line = fp.readline().strip()
				if not line:
					break
				line = line.split()
				mass = line[1]
				name = ' '.join(line[2:-3]) # name might contain spaces...
				self.channel_labels.append('{0} ({1})'.format(name, mass))

			fp.readline() # another blank line
			fp.readline() # column headers
			fp.readline() # blank

			self.data = numpy.loadtxt(fp, delimiter=',', usecols=range(len(self.channel_labels)+1))

		time = self.data[:, 0] / 86400 + starttime
		self.channels = []
		for i, v in enumerate(self.channel_labels):
			self.channels.append(DataChannel(time=time, value=self.data[:, i+1], id=v))
