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

import numpy
import scipy.stats

from camera.formats import raw


def bgs_line_by_line(data):
	new = numpy.zeros(data.shape)
	pixels = numpy.arange(data.shape[1])
	#params = []
	for i, line in enumerate(data):
		slope, intercept, r_value, p_value, stderr = scipy.stats.linregress(pixels, line)
		new[i, :] = line - (slope * pixels + intercept)
		#params.append((slope, intercept))
	return new


def bgs_plane(data):
	# this code is based on Gwyddion's gwy_data_field_fit_plane
	ny, nx = data.shape
	xgrid, ygrid = numpy.meshgrid(numpy.arange(nx), numpy.arange(ny))

	sumxi = (nx-1)/2.
	sumxixi = (2*nx-1)*(nx-1)/6.
	sumyi = (ny-1)/2.
	sumyiyi = (2*ny-1)*(ny-1)/6.

	sumsi = data.mean()
	sumsixi = (data*xgrid).mean()
	sumsiyi = (data*ygrid).mean()

	bx = (sumsixi - sumsi*sumxi) / (sumxixi - sumxi*sumxi)
	by = (sumsiyi - sumsi*sumyi) / (sumyiyi - sumyi*sumyi)
	a = sumsi - bx*sumxi - by*sumyi

	return data - a - bx*xgrid - by*ygrid


def diff_line(data):
	# central differences for interior and first differences for endpoints
	out = numpy.zeros_like(data)
	out[:, 1:-1] = (data[:, 2:] - data[:, :-2])/2.
	out[:, 0] = data[:, 1] - data[:, 0]
	out[:, -1] = data[:, -1] - data[:, -2]
	return out


# for use with the bgs_* functions
def array(func):
	def filter(frame):
		# FIXME: this modifies the frame in-place, I'm not sure if this is desired behaviour
		frame.image = func(frame.image)
		return frame
	return filter


def ClipStdDev(number):
	# FIXME: this modifies the frame in-place, I'm not sure if this is desired behaviour
	def clip(frame):
		avg, stddev = frame.image.mean(), frame.image.std()
		frame.image = numpy.clip(frame.image, avg - number * stddev, avg + number * stddev)
		return frame
	return clip


def average(npoints):
	# FIXME: this modifies the frame in-place, I'm not sure if this is desired behaviour
	def avgn(data):
		data.value = numpy.array(map(numpy.mean, numpy.array_split(data.value, numpy.ceil(data.value.size/npoints))))
		data.time = numpy.array(map(numpy.mean, numpy.array_split(data.time, numpy.ceil(data.time.size/npoints))))
		return data
	return avgn


def merge_directions(lrdata, rldata):
	if lrdata.shape != rldata.shape:
		raise ValueError('L2R and R2L arrays have different shape')
	ret = numpy.zeros((lrdata.shape[0], lrdata.shape[1]*2))
	ret[:, 0:lrdata.shape[1]] = lrdata
	ret[:, lrdata.shape[1]:] = rldata[:, ::-1]
	return ret

def split_directions(data):
	lr = data[:, 0:(data.shape[1] // 2)]
	rl = data[:, :(data.shape[1] // 2)-1:-1]
	return lr, rl

def code2func(expr, preexec, variable='x'):
	def filter(x):
		env = {variable: x}
		exec preexec in env
		return eval(expr, env)
	return filter

def fourier(filter):
	def fourierfilter(frame):
		if frame.direction == (raw.RawFileChannelInfo.LR | raw.RawFileChannelInfo.RL):
			data = frame.image
		else:
			data = merge_directions(frame.lrimage, frame.rlimage)

		z = scipy.fftpack.fft(data.flatten())
		freq = scipy.fftpack.fftfreq(z.size, 1/frame.pixelrate)
		filtered_data = scipy.fftpack.ifft(filter(freq) * z).real.reshape(data.shape)
		print filtered_data

		frame.lrimage, frame.rlimage = split_directions(filtered_data)
		if frame.direction == (raw.RawFileChannelInfo.LR | raw.RawFileChannelInfo.RL):
			frame.image = filtered_data
		elif frame.direction == raw.RawFileChannelInfo.LR:
			frame.image = frame.lrimage
		else:
			frame.image = frame.rlimage
	
		return frame
	return fourierfilter
