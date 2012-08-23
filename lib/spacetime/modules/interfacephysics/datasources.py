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

import datetime
import numpy
import re

from ..generic.datasources import MultiTrend
from ...util import Struct, mpldtfromdatetime, mpldtstrptime, localtz


class TPDirk(MultiTrend):
	def readiter(self):
		fp = open(self.filename)
		fp.readline() # ignore two header lines
		fp.readline()
		for line in fp:
			data = line.strip().split(';')
			if len(data) == 2: # last line ends with "date;time"
				continue
			no, dt, pressure, temperature = data
			yield numpy.array((
				mpldtstrptime(dt, '%y/%m/%d %H:%M:%S'),
				float(pressure),
				float(temperature)
			))

	def __init__(self, *args, **kwargs):
		super(TPDirk, self).__init__(*args, **kwargs)
		data = numpy.array(list(self.readiter()))
		self.channels = [
			Struct(id='pressure', time=data[:,0], value=data[:,1]),
			Struct(id='temperature', time=data[:,0], value=data[:,2]),
		]


class OldGasCabinet(MultiTrend):
	controllers = ['MFC CO', 'MFC NO', 'MFC H2', 'MFC O2', 'MFC Shunt', 'BPC1', 'BPC2', 'MFM Ar']
	parameters = ['valve output', 'measure', 'set point']
	data = None

	def __init__(self, *args, **kwargs):
		super(OldGasCabinet, self).__init__(*args, **kwargs)
		self.data = numpy.loadtxt(self.filename)
		# FIXME: this is an ugly hack to determine the date. the fileformat should be
		# modified such that date information is stored INSIDE the file
		y, m, d = re.search('(20[0-9]{2})([0-9]{2})([0-9]{2})', self.filename).groups()
		self.offset = mpldtfromdatetime(localtz.localize(datetime.datetime(int(y), int(m), int(d))))

		columns = self.data.shape[1]
		assert (columns - 2)  % 4 == 0
		self.channels = []
		for i in range((columns - 2) // 4):
			time = self.data[:,i*4]/86400 + self.offset
			for j, p in enumerate(self.parameters):
				self.channels.append(Struct(time=time, value=self.data[:,i*4+j+1], id='{0} {1}'.format(self.controllers[i], p), parameter=p, controller=self.controllers[i]))
		# NOTE: the last two columns (Leak dectector) are ignored
