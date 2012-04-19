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

from ..generic.datasources import DataSource, MultiTrend, DataChannel, ImageFrame

import numpy

from camera.formats import raw

from ... import util, mathutil

# Camera class for image mode and trend mode
class Camera(MultiTrend):
	direction = raw.RawFileChannelInfo.LR
	averaging = False # only for trend mode
	fft = False

	def __init__(self, *args, **kwargs):
		super(Camera, self).__init__(*args, **kwargs)
		self.rawfile = raw.RawFileReader(self.filename)

	def getdata(self, channel, frame):
		ret = ImageFrame()
		ret.image = self.rawfile.channelImage(frame, channel).asArray(direction=self.direction)
		ysize, xsize = ret.image.shape

		frameinfo = self.rawfile.frameInfo(frame)
		ret.tstart = util.mpldtfromtimestamp(frameinfo.acquisitionTime)
		ret.tend = ret.tstart + ret.image.size * 2 / frameinfo.pixelclock_kHz / 1000 * frameinfo.samplesPerPoint / 86400
		return ret

	def getchanneldata(self, channel, frameiter=None):
		data = []
		time = []
		if frameiter is None:
			frameiter = self.framenumberiter()
		for frameno in frameiter:
			frame = self.rawfile.channelImage(frameno, channel)
			frameinfo = self.rawfile.frameInfo(frameno)
			tstart = util.mpldtfromtimestamp(frameinfo.acquisitionTime)

			if self.direction == (raw.RawFileChannelInfo.LR | raw.RawFileChannelInfo.RL):
				lrdata = frame.asArray(direction=raw.RawFileChannelInfo.LR)
				rldata = frame.asArray(direction=raw.RawFileChannelInfo.RL)

				image = numpy.zeros((lrdata.shape[0], lrdata.shape[1]*2))
				image[:, 0:lrdata.shape[1]] = lrdata
				image[:, lrdata.shape[1]:] = rldata[:, ::-1]
				tend = tstart + image.size / frameinfo.pixelclock_kHz / 1000 * frameinfo.samplesPerPoint / 86400
			else:
				image = frame.asArray(direction=self.direction)
				tend = tstart + image.size * 2 / frameinfo.pixelclock_kHz / 1000 * frameinfo.samplesPerPoint / 86400

			if self.fft:
				freq, power = mathutil.easyfft(image.flatten(), frameinfo.pixelclock_kHz * 1000 / frameinfo.samplesPerPoint)
				data.append(power)
				time.append(freq)
			else:
				if self.averaging:
					im = image.mean(axis=1)
				else:
					im = image.flatten()
				data.append(im)
				time.append(numpy.linspace(tstart, tend, im.size))
		return DataChannel(id=str(channel), value=numpy.hstack(data), time=numpy.hstack(time))

	def getframecount(self):
		return self.rawfile.header.frameCount

	def getchannelcount(self):
		return self.rawfile.header.channelCount

	def selectchannel(self, channel):
		return CameraChannel(self, channel)
	
	def selectframes(self, *args, **kwargs):
		return CameraSelectedFrames(self, *args, **kwargs)

	def framenumberiter(self):
		return xrange(self.getframecount())

	def iterchannelnames(self):
		return (str(i) for i in range(self.getchannelcount()))

	def iterchannels(self):
		return (self.getchanneldata(channel) for channel in range(self.getchannelcount()))


# image mode and trend mode
class CameraSelectedFrames(MultiTrend):
	def __init__(self, cameradata, firstframe, lastframe, step=1):
		self.cameradata = cameradata
		self.firstframe = firstframe
		self.lastframe = lastframe
		self.step = step

	def framenumberiter(self):
		return xrange(max(0, self.firstframe), min(self.lastframe+1, self.cameradata.getframecount()), self.step)

	def selectframes(self, *args, **kwargs):
		return self.cameradata.selectframes(*args, **kwargs)

	def selectchannel(self, channel):
		return CameraChannel(self, channel)

	def getdata(self, channel, frame):
		return self.cameradata.getdata(channel, frame)

	def iterchannelnames(self):
		return self.cameradata.iterchannelnames()

	def iterchannels(self):
		return (self.cameradata.getchanneldata(channel, self.framenumberiter()) for channel in range(self.cameradata.getchannelcount()))


# image mode only
class CameraChannel(DataSource):
	def __init__(self, cameradata, channel):
		self.cameradata = cameradata
		self.channel = channel

	def selectframes(self, *args, **kwargs):
		return self.cameradata.selectframes(*args, **kwargs).selectchannel(self.channel)

	def iterframes(self):
		for i in self.cameradata.framenumberiter():
			yield self.cameradata.getdata(self.channel, i)


class ChainedImage(DataSource):
	def __init__(self, *args):
		self.args = args

	def iterframes(self):
		for arg in self.args:
			for frame in arg.iterframes():
				yield frame
