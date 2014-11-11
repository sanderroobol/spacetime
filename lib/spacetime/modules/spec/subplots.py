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

from ..generic.subplots import MultiTrend

class Normalization(MultiTrend):
	normalization_factor = normalization_channel = 1

	def set_normalization(self, factor, channel=None):
		self.normalization_factor = factor
		if channel:
			self.normalization_channel = next(channel.iterchannels()).value
		else:
			self.normalization_channel = 1

	def get_ydata(self, chandata):
		return chandata.value * self.normalization_factor / self.normalization_channel
