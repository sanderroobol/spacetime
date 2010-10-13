import numpy
import pylab, matplotlib
from superstruct import Struct

from camera.formats import raw

def parseDT(str):
	return str

def parseExtDT(str):
	return str

def parseLine(line):
	data = line.strip().split('\t')
	assert len(data) % 3 == 0
	return [float(d) for (i,d) in enumerate(data) if (i % 3) in (1, 2)]

def readMID(filename):
	fp = open(filename)

	headerlines = [fp.readline() for i in range(6)]
	header = Struct()
	header.source     =            headerlines[0].split('\t')[1].strip()
	header.exporttime =    parseDT(headerlines[1].split('\t')[1].strip())
	header.starttime  = parseExtDT(headerlines[3].split('\t')[1].strip())
	header.stoptime   = parseExtDT(headerlines[4].split('\t')[1].strip())

	masses = [int(i) for i in fp.readline().split()]
	columntitles = fp.readline() # not used

	data = [parseLine(line) for line in fp if line.strip()]
	if len(data[-2]) > len(data[-1]):
		data[-1].extend([0.] * (len(data[-2]) - len(data[-1])))
	rawdata = numpy.array(data)

	data = {}
	for i, mass in enumerate(masses):
		data[mass] = rawdata[:,2*i], rawdata[:,2*i+1]
	

	return header, data

def hide_xticklabels(ax):
	for label in ax.get_xticklabels():
		label.set_visible(False)

def matplotfiginit(size=(14,8), legend=0):
	pylab.figure(figsize=size)

	width, height = size
	def wabs2rel(x): return x / width
	def habs2rel(x): return x / height

	lrborder = .75
	tbborder = .45
	hspace = .2
	wspace = .2
	
	pylab.subplots_adjust(
			left=wabs2rel(lrborder),
			right=1-wabs2rel(lrborder + legend),
			top=1-habs2rel(tbborder),
			bottom=habs2rel(tbborder),
			hspace=habs2rel(hspace),
			wspace=wabs2rel(wspace),
	)
	return pylab.gcf()



def bgsubtract(image):
	return image # doens't improve the situation
	# poor man's per-line background subtraction
	out = numpy.zeros(image.shape)
	for i in range(image.shape[0]):
		out[i,:] = image[i,:] - numpy.linspace(image[i,0], image[i,-1], image.shape[1])
	return out

fig = matplotfiginit()
ax_spm = fig.add_subplot(211)
ax_qms = fig.add_subplot(212, sharex=ax_spm)

### QMS
header, data = readMID('qms sample/MID.asc')

for mass, (time, current) in data.iteritems():
	ax_qms.plot(time, current, label=str(mass))

ax_qms.set_xlabel('Time (s)')
ax_qms.set_ylabel('Ion current (A)')
ax_qms.legend()

### CAMERA
r = raw.RawFileReader('camera sample/100916_PdNPAl2O3_RT_TurboON_ArgonFlow_072mlmin.raw')
tstart, tend = 0, 0
for frameno in range(r.header.frameCount):
	image = r.channelImage(frameno, 0).asArray()
	ysize, xsize = image.shape

	frameinfo = r.frameInfo(frameno)
	tstart = frameinfo.acquisitionTime - 1284643013
	print "new tstart=%d, old tend=%d" % (tstart, tend)
	tend = tstart + xsize*ysize / frameinfo.pixelclock_kHz / 1000 * 2

	# map the linenunumber to the time axis and the individual points to some arbitrary unit axis
	time, pixel = numpy.meshgrid(numpy.linspace(tstart, tend, ysize+1), numpy.linspace(0., 1., xsize+1))
	
	# transpose the image data to plot scanlines vertical
	ax_spm.pcolormesh(time, pixel, bgsubtract(image).T)

ax_spm.set_ylim(0, 1)
ax_spm.set_yticks([])
hide_xticklabels(ax_spm)

pylab.show()
