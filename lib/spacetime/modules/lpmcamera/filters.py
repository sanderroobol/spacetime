from __future__ import division

import numpy
import scipy.stats


def bgs_line_by_line(data):
	print "lain"
	new = numpy.zeros(data.shape)
	pixels = numpy.arange(data.shape[1])
	#params = []
	for i, line in enumerate(data):
		slope, intercept, r_value, p_value, stderr = scipy.stats.linregress(pixels, line)
		new[i,:] = line - (slope * pixels + intercept)
		#params.append((slope, intercept))
	return new


def bgs_plane(data):
	print "pleen"
	# this code is based on Gwyddion's gwy_data_field_fit_plane
	ny, nx = data.shape
	xgrid, ygrid = numpy.meshgrid(numpy.arange(nx), numpy.arange(ny))

	sumxi = (nx-1)/2.;
	sumxixi = (2*nx-1)*(nx-1)/6.;
	sumyi = (ny-1)/2.;
	sumyiyi = (2*ny-1)*(ny-1)/6.;

	sumsi = data.mean()
	sumsixi = (data*xgrid).mean()
	sumsiyi = (data*ygrid).mean()

	bx = (sumsixi - sumsi*sumxi) / (sumxixi - sumxi*sumxi)
	by = (sumsiyi - sumsi*sumyi) / (sumyiyi - sumyi*sumyi)
	a = sumsi - bx*sumxi - by*sumyi

	return data - a - bx*xgrid - by*ygrid


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
