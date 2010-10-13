import matplotlib.dates
import datetime
from superstruct import Struct


# FIXME: These functions are currently not timezone aware, this could cause problems eventually.
def mpdtfromtimestamp(ts):
	return matplotlib.dates.date2num(datetime.datetime.fromtimestamp(ts))

mpdtfromdatetime = matplotlib.dates.date2num


