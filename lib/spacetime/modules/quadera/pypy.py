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

import numpy

from ... import util

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

@util.pypy
def loadscan(filename):
	with open(filename) as fp:

		file_header = [fp.readline() for i in range(3)]
		time_data = []
		ion_data = []
		scan_lengths = set()
		
		while 1:
			scan_header = [fp.readline() for i in range(7)]
			if scan_header[-1] == '':
				break
			time_data.append(parseExtDT(scan_header[4].split('\t')[1].strip()))
			scan_data = []
			while 1:
				line = fp.readline().strip()
				if line == '': # empty line indicates end of scan
					break
				scan_data.append(numpy.array(line.split(), dtype=float))
			scan_data = numpy.array(scan_data)
			masses = scan_data[:, 0]
			if not ion_data:
				masses = numpy.array(masses) # copy
			ion_data.append(scan_data[:, 1])
			scan_lengths.add(len(masses))
			
		time_data = numpy.array(time_data)

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
		ion_data = numpy.array(ion_data)

		channels = []
		for i, m in enumerate(masses):
			d = util.Struct()
			d.id = str(m)
			d.time = time_data
			d.value = ion_data[:, i]
			channels.append(d)

		return masses, time_data, ion_data, channels

@util.pypy
def loadmid(filename):
	with open(filename) as fp:
		headerlines = [fp.readline() for i in range(6)]
		header = util.Struct()
		header.source     =            headerlines[0].split('\t')[1].strip()
		header.exporttime =    parseDT(headerlines[1].split('\t')[1].strip())
		header.starttime  = parseExtDT(headerlines[3].split('\t')[1].strip())
		header.stoptime   = parseExtDT(headerlines[4].split('\t')[1].strip())

		masses = fp.readline().split()
		columntitles = fp.readline() # not used
		
		data = [parseLine(line) for line in fp if line.strip()]

		# the number of channels can be changed during measurement, and the last line is not guaranteed to be complete
		padlength = len(data[0]) # we assume that the first line is always the longest, this seems to be valid even when adding channels halfway
		nanlist = [numpy.nan]
		for line in data:
			line.extend(nanlist * (padlength - len(line)))
		rawdata = numpy.array(data)

		channels = []
		for i, mass in enumerate(masses):
			d = util.Struct()
			d.mass = mass
			d.id = str(mass)
			d.time = rawdata[:,2*i]/86400. + header.starttime
			d.value = rawdata[:,2*i+1]
			channels.append(d)

		return header, masses, channels
