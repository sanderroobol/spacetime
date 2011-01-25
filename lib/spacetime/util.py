import matplotlib.dates
import datetime

from .superstruct import Struct


class SharedXError(Exception):
	pass


# FIXME: These functions are currently not timezone aware, this could cause problems eventually.
def mpldtfromtimestamp(ts):
	return matplotlib.dates.date2num(datetime.datetime.fromtimestamp(ts))

mpldtfromdatetime = matplotlib.dates.date2num
datetimefrommpldt = matplotlib.dates.num2date


