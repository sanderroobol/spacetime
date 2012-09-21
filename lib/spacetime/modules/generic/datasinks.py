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

import os
import numpy


class DataSink(object):
	def save(self, plot, destdir, prefix):
		raise NotImplementedError


class MultiTrendTextSink(DataSink):
	def save(self, plot, destdir, prefix):
		channelnamecounts = {}
		
		for d in plot.data.iterchannels():
			if d.id in channelnamecounts:
				channelnamecounts[d.id] += 1
				label = '{0} {1}'.format(d.id, channelnamecounts[d.id])
			else:
				channelnamecounts[d.id] = 1
				label = d.id
			path = os.path.join(destdir, '{0} - {1}.txt'.format(prefix, label))
			numpy.savetxt(path, numpy.vstack((plot.get_xdata(d), plot.get_ydata(d))).transpose())
