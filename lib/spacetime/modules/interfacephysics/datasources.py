# This file is part of Spacetime.
#
# Copyright 2010-2014 Leiden University.
# Written by Sander Roobol.
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

import numpy
import re
import codecs

from ..generic.datasources import MultiTrend, DataChannel
from ...import util


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
				util.mpldtstrptime(dt, '%y/%m/%d %H:%M:%S'),
				float(pressure),
				float(temperature)
			))

	def __init__(self, *args, **kwargs):
		super(TPDirk, self).__init__(*args, **kwargs)
		data = numpy.array(list(self.readiter()))
		self.channels = [
			DataChannel(id='pressure', time=data[:,0], value=data[:,1]),
			DataChannel(id='temperature', time=data[:,0], value=data[:,2]),
		]


class OldGasCabinet(MultiTrend):
	controllers = ['MFC_CO', 'MFC_NO', 'MFC_H2', 'MFC_O2', 'MFC_Shunt', 'BPC1', 'BPC2', 'MFM_Ar']
	parameters = ['valve position', 'measure', 'setpoint']
	data = None

	def __init__(self, *args, **kwargs):
		super(OldGasCabinet, self).__init__(*args, **kwargs)
		self.data = util.loadtxt(self.filename)
		# FIXME: this is an ugly hack to determine the date. the fileformat should be
		# modified such that date information is stored INSIDE the file
		y, m, d = re.search('(20[0-9]{2})([0-9]{2})([0-9]{2})', self.filename).groups()
		self.offset = util.mpldtlikedatetime(int(y), int(m), int(d))

		columns = self.data.shape[1]
		assert (columns - 2)  % 4 == 0
		self.channels = []
		for i in range((columns - 2) // 4):
			time = self.data[:,i*4]/86400 + self.offset
			for j, p in enumerate(self.parameters):
				self.channels.append(DataChannel(time=time, value=self.data[:,i*4+j+1], id='{0} {1}'.format(self.controllers[i], p), parameter=p, controller=self.controllers[i], type='controller'))
		# NOTE: the last two columns (Leak dectector) are ignored


class TEMHeater(MultiTrend):
	month_names = dict((m, i+1) for (i, m) in enumerate(('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')))
	month_names.update(dict((m, i+1) for (i, m) in enumerate(('jan', 'feb', 'mrt', 'apr', 'mei', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'dec'))))
	decimal_separator = '.'

	lasttime = 0.
	offset = 0.

	def __init__(self, *args, **kwargs):
		super(TEMHeater, self).__init__(*args, **kwargs)
		with codecs.open(self.filename, encoding='latin1') as fp:
			fp.readline() # empty
			fp.readline() # some unknown values

			date = fp.readline().strip()
			day, month, year = date.split(' ')

			time = fp.readline().strip()
			if ',' in time:
				self.decimal_separator = ','
			HMS, ms = time.split(self.decimal_separator)
			H, M, S = HMS.split(':')
		
			self.tstart = util.mpldtlikedatetime(int(year), self.month_names[month], int(day), int(H), int(M), int(S), int(ms)*1000)

			self.channel_labels = fp.readline().strip().split('\t')[2:]
			self._read_bulk(fp)

	def _parsetime(self, str):
		MS, ms = str.split('.')
		M,S = MS.split(':')
		time = self.offset + float(M)/1440 + float(S)/86400 + float(ms)/86400000
		if self.lasttime > time:
			self.offset += 1./24
			time += 1./24
		self.lasttime = time
		return time

	def _read_bulk(self, fp):
		time = []
		data = []
		for line in fp:
			if self.decimal_separator != '.':
				line = line.replace(self.decimal_separator, '.')
			line = line.strip().split('\t')
			time.append(self.tstart + self._parsetime(line[1]))
			data.append(tuple(float(i) for i in line[2:]))

		time = numpy.asarray(time)
		self.data = numpy.asarray(data)

		self.channels = []
		for (i, v) in enumerate(self.channel_labels):
			self.channels.append(DataChannel(id=v, time=time, value=self.data[:,i]))
