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

import numpy

from ... import util

def multistrptime(s, formats):
	for fmt in formats:
		try:
			return util.mpldtstrptime(s, fmt)
		except ValueError:
			pass
	raise ValueError("cannot parse timestamp {0} using format strings {1!r}".format(s, formats))
	
def parseDT(s):
	return multistrptime(s, ('%m/%d/%Y %I:%M:%S %p', '%m/%d/%Y %H:%M:%S', '%d-%m-%Y %H:%M:%S', '%m-%d-%Y %H:%M:%S', '%m-%d-%Y %I:%M:%S %p'))

def parseExtDT(s):
	return multistrptime(s, ('%m/%d/%Y %I:%M:%S.%f %p', '%m/%d/%Y %H:%M:%S.%f', '%d-%m-%Y %H:%M:%S.%f', '%m-%d-%Y %H:%M:%S.%f', '%m-%d-%Y %I:%M:%S.%f %p'))

def floatnan(s):
	if not s or s == '---':
		return numpy.nan
	return float(s)

def parseLine(line):
	data = line.rstrip('\r\n').split('\t')
	assert len(data) % 3 == 0
	return [floatnan(d) for (i,d) in enumerate(data) if (i % 3) in (1, 2)]

@util.pypy
def loadscan(filename):
	with open(filename) as fp:

		file_header = [fp.readline() for i in range(3)]

		# since Quadera 4.5:
		field = 'Start Time\t'
		fourpointfive = (fp.read(len(field)) == field)
		fp.seek(-len(field), 1)
		if fourpointfive:
			file_header.extend(fp.readline() for i in range(4))

		time_data = []
		ion_data = []
		scan_lengths = set()
		
		while 1:
			scan_header = [fp.readline() for i in range(7)]
			if scan_header[-1] == '':
				break
			while scan_header[0].strip() == '': # sometimes there are extra empty lines...
				scan_header.pop(0)
				scan_header.append(fp.readline())
			time_data.append(parseExtDT(scan_header[4].split('\t')[1].strip()))
			scan_data = []
			while 1:
				line = fp.readline().strip()
				if line == '': # empty line indicates end of scan
					break
				scan_data.append(numpy.array(line.split(), dtype=float))
			scan_data = numpy.array(scan_data)
			masses = scan_data[:, 0]
			if ion_data:
				if not (global_masses[:2] == masses[:2]).all():
					raise ValueError('File not supported: mass range was changed during acquisition.')
			else:
				global_masses = numpy.array(masses) # copy
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
		for i, m in enumerate(global_masses):
			d = util.Struct()
			d.id = str(m)
			d.time = time_data
			d.value = ion_data[:, i]
			channels.append(d)

		return global_masses, time_data, ion_data, channels

@util.pypy
def loadmid(filename):
	with open(filename) as fp:
		headerlines = [fp.readline() for i in range(6)]
		header = util.Struct()
		header.source     =            headerlines[0].split('\t')[1].strip()
		header.exporttime = headerlines[1].split('\t')[1].strip()
		header.starttime  = parseExtDT(headerlines[3].split('\t')[1].strip())
		header.stoptime   = parseExtDT(headerlines[4].split('\t')[1].strip())

		# for Quadera 4.5: there might be an extra empty line here
		line = fp.readline()
		if line.strip():
			fp.seek(-len(line), 1)

		masses = fp.readline().strip().split('\t\t\t')
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
