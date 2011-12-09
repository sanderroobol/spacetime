from __future__ import division

import datetime
import numpy

from ... import util
from ..generic.datasources import MultiTrend


def multistrptime(s, formats):
	for fmt in formats:
		try:
			return util.mpldtstrptime(s, fmt)
		except ValueError:
			pass
	raise ValueError("cannot parse timestamp {0} using format strings {1:r}".format(s, formats))
	
def parseDT(s):
	return multistrptime(s, ('%m/%d/%Y %I:%M:%S %p', '%m/%d/%Y %H:%M:%S'))

def parseExtDT(s):
	return multistrptime(s, ('%m/%d/%Y %I:%M:%S.%f %p', '%m/%d/%Y %H:%M:%S.%f'))

def floatnan(s):
	if not s:
		return numpy.nan
	return float(s)

def parseLine(line):
	data = line.strip().split('\t')
	assert len(data) % 3 == 0
	return [floatnan(d) for (i,d) in enumerate(data) if (i % 3) in (1, 2)]


class QuaderaScan(MultiTrend):
	def __init__(self, *args, **kwargs):
		super(QuaderaScan, self).__init__(*args, **kwargs)
		self.fp = open(self.filename)	

		file_header = [self.fp.readline() for i in range(3)]
		time_data = []
		ion_data = []
		scan_lengths = set()
		
		while 1:
			scan_header = [self.fp.readline() for i in range(7)]
			if scan_header[-1] == '':
				break
			time_data.append(parseExtDT(scan_header[4].split('\t')[1].strip()))
			scan_data = []
			while 1:
				line = self.fp.readline().strip()
				if line == '': # empty line indicates end of scan
					break
				scan_data.append(numpy.array(line.split(), dtype=float))
			scan_data = numpy.array(scan_data)
			masses = scan_data[:, 0]
			if not ion_data:
				self.masses = numpy.array(masses) # copy
			ion_data.append(scan_data[:, 1])
			scan_lengths.add(len(masses))
			
		self.time_data = numpy.array(time_data)

		# pad the ion data array if necessary
		if len(scan_lengths) != 1:
			pad = max(scan_lengths)
			nid = []
			for i in ion_data:
				if i.size < pad:
					nid.append(numpy.append(i, numpy.zeros(pad - i.size)))
				else:
					nid.append(i)
			ion_data = nid
		self.ion_data = numpy.array(ion_data)

		self.channels = []
		for i, m in enumerate(self.masses):
			d = util.Struct()
			d.id = str(m)
			d.time = self.time_data
			d.value = self.ion_data[:, i]
			self.channels.append(d)

	def iterimages(self):
		d = util.Struct()
		d.data = self.ion_data.transpose()
		d.tstart = self.time_data[0]
		d.tend = self.time_data[-1]
		d.ybottom = self.masses[0]
		d.ytop = self.masses[-1]
		yield d


class QuaderaMID(MultiTrend):
	channels = None
	masses = None
	fp = None

	def __init__(self, *args, **kwargs):
		super(QuaderaMID, self).__init__(*args, **kwargs)
		self.fp = open(self.filename)

		headerlines = [self.fp.readline() for i in range(6)]
		self.header = util.Struct()
		self.header.source     =            headerlines[0].split('\t')[1].strip()
		self.header.exporttime =    parseDT(headerlines[1].split('\t')[1].strip())
		self.header.starttime  = parseExtDT(headerlines[3].split('\t')[1].strip())
		self.header.stoptime   = parseExtDT(headerlines[4].split('\t')[1].strip())

		self.masses = self.fp.readline().split()
		columntitles = self.fp.readline() # not used
		
		data = [parseLine(line) for line in self.fp if line.strip()]

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
