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

from ..generic.subplots import DoubleMultiTrend

class TPDirk(DoubleMultiTrend):
	def __init__(self, data=None, formatter=None):
		self.set_data(data)
		super(TPDirk, self).__init__(self.data, self.secondarydata, formatter)
	
	def set_data(self, data):
		self.realdata = data
		if data:
			self.data = data.selectchannels(lambda x: x.id == 'pressure')
			self.secondarydata = data.selectchannels(lambda x: x.id == 'temperature')
		else:
			self.data = None
			self.secondarydata = None

	def setup(self):
		super(TPDirk, self).setup()
		self.axes.set_ylabel('Pressure (mbar)')
		self.axes.set_yscale('log')
		self.secondaryaxes.set_ylabel('Temperature (K)')
