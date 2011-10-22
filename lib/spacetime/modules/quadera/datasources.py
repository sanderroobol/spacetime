from __future__ import division

import datetime
import numpy

from ... import util
from ..generic.datasources import MultiTrend

class QMS(MultiTrend):
	channels = None
	masses = None
	fp = None

	@staticmethod
	def parseDT(s):
		return util.mpldtstrptime(s, '%m/%d/%Y %I:%M:%S %p')

	@staticmethod
	def parseExtDT(s):
		return util.mpldtstrptime(s, '%m/%d/%Y %I:%M:%S.%f %p')

	@staticmethod
	def floatnan(s):
		if not s:
			return numpy.nan
		return float(s)

	@staticmethod
	def parseLine(line):
		data = line.strip().split('\t')
		assert len(data) % 3 == 0
		return [QMS.floatnan(d) for (i,d) in enumerate(data) if (i % 3) in (1, 2)]

	def __init__(self, *args, **kwargs):
		super(QMS, self).__init__(*args, **kwargs)
		self.fp = open(self.filename)

		headerlines = [self.fp.readline() for i in range(6)]
		self.header = util.Struct()
		self.header.source     =                 headerlines[0].split('\t')[1].strip()
		self.header.exporttime =    self.parseDT(headerlines[1].split('\t')[1].strip())
		self.header.starttime  = self.parseExtDT(headerlines[3].split('\t')[1].strip())
		self.header.stoptime   = self.parseExtDT(headerlines[4].split('\t')[1].strip())

		self.masses = self.fp.readline().split()
		columntitles = self.fp.readline() # not used
		
		data = [self.parseLine(line) for line in self.fp if line.strip()]

		# the number of channels can be changed during measurement, and the last line is not guaranteed to be complete
		padlength = len(data[0]) # we assume that the first line is always the longest, this seems to be valid even when adding channels halfway
		nanlist = [numpy.nan]
		for line in data:
			line.extend(nanlist * (padlength - len(line)))
		rawdata = numpy.array(data)

		self.channels = []
		for i, mass in enumerate(self.masses):
			d = util.Struct()
			d.mass = mass
			d.id = str(mass)
			d.time = rawdata[:,2*i]/86400 + self.header.starttime
			d.value = rawdata[:,2*i+1]
			self.channels.append(d)
