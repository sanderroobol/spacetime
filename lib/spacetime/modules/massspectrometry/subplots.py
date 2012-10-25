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

from ..generic.subplots import MultiTrend, Time2D

class Normalization(object):
	normalization_factor = normalization_channel = 1

	def set_normalization(self, factor, channel=None):
		self.normalization_factor = factor
		if channel:
			self.normalization_channel = next(channel.iterchannels()).value
		else:
			self.normalization_channel = 1


class MSTrend(Normalization, MultiTrend):
	def setup(self):
		super(MSTrend, self).setup()
		self.axes.set_ylabel('Ion current (A)')

	def get_ydata(self, chandata):
		return chandata.value * self.normalization_factor / self.normalization_channel


class MS2D(Normalization, Time2D):
	def setup(self):
		super(MS2D, self).setup()
		self.axes.set_ylabel('Mass (a.m.u.)')

	def get_imdata(self, imdata):
		return imdata.data * self.normalization_factor / self.normalization_channel
