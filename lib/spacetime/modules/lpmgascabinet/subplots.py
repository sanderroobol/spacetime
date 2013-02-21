# This file is part of Spacetime.
#
# Copyright (C) 2010-2013 Leiden University.
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

from ..generic.subplots import DoubleMultiTrend, MultiTrendFormatter

class GasCabinetFormatter(MultiTrendFormatter):
	prevcontroller = None

	def reset(self):
		self.prevcontroller = None
		super(GasCabinetFormatter, self).reset()

	def __call__(self, data):
		linestyle = '-'

		if data.type == 'controller':
			if data.parameter == 'setpoint':
				linestyle = '--' # dashed
			elif data.parameter == 'valve position':
				linestyle = ':'

			if self.prevcontroller != data.controller:
				self.increase_counter()
				self.prevcontroller = data.controller
		else:
			self.increase_counter()
			self.prevcontroller = None

		return self.colors[self.counter] + linestyle


class GasCabinet(DoubleMultiTrend):
	def __init__(self, data=None, secondarydata=None, formatter=None):
		if formatter is None:
			formatter = GasCabinetFormatter()
		super(GasCabinet, self).__init__(data, secondarydata, formatter)

	def draw(self):
		super(GasCabinet, self).draw()
		self.axes.set_ylabel('')
		self.secondaryaxes.set_ylabel('')

		if self.data and list(self.data.iterchannelnames()):
			if all(chan.startswith('MF') for chan in self.data.iterchannelnames()):
				self.axes.set_ylabel('Mass flow (mbar l/min)')
			elif all(chan.startswith('BPC') for chan in self.data.iterchannelnames()):
				self.axes.set_ylabel('Pressure (bar)')

		if self.secondarydata and list(self.secondarydata.iterchannelnames()):
			if all(chan.startswith('MF') for chan in self.secondarydata.iterchannelnames()):
				self.secondaryaxes.set_ylabel('Mass flow (mbar l/min)')
			elif all(chan.startswith('BPC') for chan in self.secondarydata.iterchannelnames()):
				self.secondaryaxes.set_ylabel('Pressure (bar)')

	def get_legend_items(self):
		handles, labels = super(GasCabinet, self).get_legend_items()
		newhandles = []
		newlabels = []
		previd = None
		for (h, l) in zip(handles, labels):
			id = l.split()[0]
			if id != previd:
				newhandles.append(h)
				newlabels.append(id)
				previd = id
		return newhandles, newlabels
