# Based on the Javascript version written by Jon Nylander et al. from
# https://bitbucket.org/pellepim/jstimezonedetect
# which is provided under the "Do Whatever You Want With This Code License"

import time, datetime, calendar

HEMISPHERE_SOUTH = 'SOUTH'
HEMISPHERE_NORTH = 'NORTH'
HEMISPHERE_UNKNOWN = 'N/A'


class TimeZone(object):
	"""
	A simple object containing information of utc_offset, which olson timezone key to use, 
	and if the timezone cares about daylight savings or not.
	"""

	def __init__(self, offset, olson_tz, uses_dst):
		"""
		@param {string} offset - for example '-11:00'
		@param {string} olson_tz - the olson Identifier, such as "America/Denver"
		@param {boolean} uses_dst - flag for whether the time zone somehow cares about daylight savings.
		"""
		self.utc_offset = offset
		self.olson_tz = olson_tz
		self.uses_dst = uses_dst

	def ambiguity_check(self):
		"""
		Checks if a timezone has possible ambiguities. I.e timezones that are similar.

		If the preliminary scan determines that we're in America/Denver. We double check
		here that we're really there and not in America/Mazatlan.

		This is done by checking known dates for when daylight savings start for different
		timezones.
		"""
		if self.olson_tz not in olson_ambiguity_list:
			return

		for tz in olson_ambiguity_list[self.olson_tz]:
			if date_is_dst(olson_dst_start_dates[tz]):
				self.olson_tz = tz
				return


def date_is_dst(date):
	"""
	Checks whether a given date is in daylight savings time.

	If the date supplied is after june, we assume that we're checking
	for southern hemisphere DST.

	@param {Date} date
	@returns {boolean}
	"""
	if date.month > 6:
		base_offset = get_june_offset()
	else:
		base_offset = get_january_offset()
	
	date_offset = get_date_offset(date)
	
	return (base_offset - date_offset) != 0


def get_date_offset(date):
	"""
	Gets the offset in minutes from UTC for a certain date.

	@param date
	@returns {number}
	"""
	s = date.timetuple()
	return int((calendar.timegm(s) - time.mktime(s))/60.)


def get_timezone_info():
	"""
	This function does some basic calculations to create information about 
	the user's timezone.
	
	Returns a primitive object on the format
	{'utc_offset' : -9, 'dst': 1, hemisphere' : 'north'}
	where dst is 1 if the region uses daylight savings.
	
	@returns {Object}  
	"""
	january_offset = get_january_offset()
	june_offset = get_june_offset()
	diff = january_offset - june_offset

	if diff < 0:
		return january_offset, 1, HEMISPHERE_NORTH
	elif diff > 0:
		return june_offset, 1, HEMISPHERE_SOUTH
	return january_offset, 0, HEMISPHERE_UNKNOWN


def get_january_offset():
	return get_date_offset(datetime.datetime(datetime.datetime.now().year, 1, 1))


def get_june_offset():
	return get_date_offset(datetime.datetime(datetime.datetime.now().year, 6, 1))


def detect_timezone():
	"""
	Uses get_timezone_info() to formulate a key to use in the olson_timezones dictionary.
	
	Returns a olson timezone identifier
	"""

	utc_offset, dst, hemisphere = get_timezone_info()
		
	if hemisphere == HEMISPHERE_SOUTH:
		hemisphere_suffix = ',s'
	else:
		hemisphere_suffix = ''
	
	tz_key = "%s,%s%s" % (utc_offset, dst, hemisphere_suffix)
	
	tz = olson_timezones[tz_key]
	tz.ambiguity_check()
	return tz.olson_tz


# The keys in this dictionary are comma separated as such:
# 
# First the offset compared to UTC time in minutes.
#  
# Then a flag which is 0 if the timezone does not take daylight savings into account and 1 if it does.
# 
# Thirdly an optional 's' signifies that the timezone is in the southern hemisphere, only interesting for timezones with DST.
# 
# The values of the dictionary are TimeZone objects.
olson_timezones = {
	'-720,0'   : TimeZone('-12:00', 'Etc/GMT+12', False),
	'-660,0'   : TimeZone('-11:00', 'Pacific/Pago_Pago', False),
	'-600,1'   : TimeZone('-11:00', 'America/Adak', True),
	'-660,1,s' : TimeZone('-11:00', 'Pacific/Apia', True),
	'-600,0'   : TimeZone('-10:00', 'Pacific/Honolulu', False),
	'-570,0'   : TimeZone('-10:30', 'Pacific/Marquesas', False),
	'-540,0'   : TimeZone('-09:00', 'Pacific/Gambier', False),
	'-540,1'   : TimeZone('-09:00', 'America/Anchorage', True),
	'-480,1'   : TimeZone('-08:00', 'America/Los_Angeles', True),
	'-480,0'   : TimeZone('-08:00', 'Pacific/Pitcairn', False),
	'-420,0'   : TimeZone('-07:00', 'America/Phoenix', False),
	'-420,1'   : TimeZone('-07:00', 'America/Denver', True),
	'-360,0'   : TimeZone('-06:00', 'America/Guatemala', False),
	'-360,1'   : TimeZone('-06:00', 'America/Chicago', True),
	'-360,1,s' : TimeZone('-06:00', 'Pacific/Easter', True),
	'-300,0'   : TimeZone('-05:00', 'America/Bogota', False),
	'-300,1'   : TimeZone('-05:00', 'America/New_York', True),
	'-270,0'   : TimeZone('-04:30', 'America/Caracas', False),
	'-240,1'   : TimeZone('-04:00', 'America/Halifax', True),
	'-240,0'   : TimeZone('-04:00', 'America/Santo_Domingo', False),
	'-240,1,s' : TimeZone('-04:00', 'America/Asuncion', True),
	'-210,1'   : TimeZone('-03:30', 'America/St_Johns', True),
	'-180,1'   : TimeZone('-03:00', 'America/Godthab', True),
	'-180,0'   : TimeZone('-03:00', 'America/Argentina/Buenos_Aires', False),
	'-180,1,s' : TimeZone('-03:00', 'America/Montevideo', True),
	'-120,0'   : TimeZone('-02:00', 'America/Noronha', False),
	'-120,1'   : TimeZone('-02:00', 'Etc/GMT+2', True),
	'-60,1'    : TimeZone('-01:00', 'Atlantic/Azores', True),
	'-60,0'    : TimeZone('-01:00', 'Atlantic/Cape_Verde', False),
	'0,0'      : TimeZone('00:00', 'Etc/UTC', False),
	'0,1'      : TimeZone('00:00', 'Europe/London', True),
	'60,1'     : TimeZone('+01:00', 'Europe/Berlin', True),
	'60,0'     : TimeZone('+01:00', 'Africa/Lagos', False),
	'60,1,s'   : TimeZone('+01:00', 'Africa/Windhoek', True),
	'120,1'    : TimeZone('+02:00', 'Asia/Beirut', True),
	'120,0'    : TimeZone('+02:00', 'Africa/Johannesburg', False),
	'180,1'    : TimeZone('+03:00', 'Europe/Moscow', True),
	'180,0'    : TimeZone('+03:00', 'Asia/Baghdad', False),
	'210,1'    : TimeZone('+03:30', 'Asia/Tehran', True),
	'240,0'    : TimeZone('+04:00', 'Asia/Dubai', False),
	'240,1'    : TimeZone('+04:00', 'Asia/Yerevan', True),
	'270,0'    : TimeZone('+04:30', 'Asia/Kabul', False),
	'300,1'    : TimeZone('+05:00', 'Asia/Yekaterinburg', True),
	'300,0'    : TimeZone('+05:00', 'Asia/Karachi', False),
	'330,0'    : TimeZone('+05:30', 'Asia/Kolkata', False),
	'345,0'    : TimeZone('+05:45', 'Asia/Kathmandu', False),
	'360,0'    : TimeZone('+06:00', 'Asia/Dhaka', False),
	'360,1'    : TimeZone('+06:00', 'Asia/Omsk', True),
	'390,0'    : TimeZone('+06:30', 'Asia/Rangoon', False),
	'420,1'    : TimeZone('+07:00', 'Asia/Krasnoyarsk', True),
	'420,0'    : TimeZone('+07:00', 'Asia/Jakarta', False),
	'480,0'    : TimeZone('+08:00', 'Asia/Shanghai', False),
	'480,1'    : TimeZone('+08:00', 'Asia/Irkutsk', True),
	'525,0'    : TimeZone('+08:45', 'Australia/Eucla', True),
	'525,1,s'  : TimeZone('+08:45', 'Australia/Eucla', True),
	'540,1'    : TimeZone('+09:00', 'Asia/Yakutsk', True),
	'540,0'    : TimeZone('+09:00', 'Asia/Tokyo', False),
	'570,0'    : TimeZone('+09:30', 'Australia/Darwin', False),
	'570,1,s'  : TimeZone('+09:30', 'Australia/Adelaide', True),
	'600,0'    : TimeZone('+10:00', 'Australia/Brisbane', False),
	'600,1'    : TimeZone('+10:00', 'Asia/Vladivostok', True),
	'600,1,s'  : TimeZone('+10:00', 'Australia/Sydney', True),
	'630,1,s'  : TimeZone('+10:30', 'Australia/Lord_Howe', True),
	'660,1'    : TimeZone('+11:00', 'Asia/Kamchatka', True),
	'660,0'    : TimeZone('+11:00', 'Pacific/Noumea', False),
	'690,0'    : TimeZone('+11:30', 'Pacific/Norfolk', False),
	'720,1,s'  : TimeZone('+12:00', 'Pacific/Auckland', True),
	'720,0'    : TimeZone('+12:00', 'Pacific/Tarawa', False),
	'765,1,s'  : TimeZone('+12:45', 'Pacific/Chatham', True),
	'780,0'    : TimeZone('+13:00', 'Pacific/Tongatapu', False),
	'840,0'    : TimeZone('+14:00', 'Pacific/Kiritimati', False)
}

# This object contains information on when daylight savings starts for
# different timezones.
# 
# The list is short for a reason. Often we do not have to be very specific
# to single out the correct timezone. But when we do, this list comes in
# handy.
# 
# Each value is a date denoting when daylight savings starts for that timezone.

def jsdate(year, month, day, hour, min, sec, whatever):
	return datetime.datetime(year, month+1, day, hour, min, sec)

olson_dst_start_dates = {
	'America/Denver' : jsdate(2011, 2, 13, 3, 0, 0, 0),
	'America/Mazatlan' : jsdate(2011, 3, 3, 3, 0, 0, 0),
	'America/Chicago' : jsdate(2011, 2, 13, 3, 0, 0, 0),
	'America/Mexico_City' : jsdate(2011, 3, 3, 3, 0, 0, 0),
	'Atlantic/Stanley' : jsdate(2011, 8, 4, 7, 0, 0, 0),
	'America/Asuncion' : jsdate(2011, 9, 2, 3, 0, 0, 0),
	'America/Santiago' : jsdate(2011, 9, 9, 3, 0, 0, 0),
	'America/Campo_Grande' : jsdate(2011, 9, 16, 5, 0, 0, 0),
	'America/Montevideo' : jsdate(2011, 9, 2, 3, 0, 0, 0),
	'America/Sao_Paulo' : jsdate(2011, 9, 16, 5, 0, 0, 0),
	'America/Los_Angeles' : jsdate(2011, 2, 13, 8, 0, 0, 0),
	'America/Santa_Isabel' : jsdate(2011, 3, 5, 8, 0, 0, 0),
	'America/Havana' : jsdate(2011, 2, 13, 2, 0, 0, 0),
	'America/New_York' : jsdate(2011, 2, 13, 7, 0, 0, 0),
	'Asia/Gaza' : jsdate(2011, 2, 26, 23, 0, 0, 0),
	'Asia/Beirut' : jsdate(2011, 2, 27, 1, 0, 0, 0),
	'Europe/Minsk' : jsdate(2011, 2, 27, 3, 0, 0, 0),
	'Europe/Istanbul' : jsdate(2011, 2, 27, 7, 0, 0, 0),
	'Asia/Damascus' : jsdate(2011, 3, 1, 2, 0, 0, 0),
	'Asia/Jerusalem' : jsdate(2011, 3, 1, 6, 0, 0, 0),
	'Africa/Cairo' : jsdate(2011, 3, 29, 4, 0, 0, 0),
	'Asia/Yerevan' : jsdate(2011, 2, 27, 4, 0, 0, 0),
	'Asia/Baku'    : jsdate(2011, 2, 27, 8, 0, 0, 0),
	'Pacific/Auckland' : jsdate(2011, 8, 26, 7, 0, 0, 0),
	'Pacific/Fiji' : jsdate(2010, 11, 29, 23, 0, 0, 0),
	'America/Halifax' : jsdate(2011, 2, 13, 6, 0, 0, 0),
	'America/Goose_Bay' : jsdate(2011, 2, 13, 2, 1, 0, 0),
	'America/Miquelon' : jsdate(2011, 2, 13, 5, 0, 0, 0),
	'America/Godthab' : jsdate(2011, 2, 27, 1, 0, 0, 0)
}

# The keys in this object are timezones that we know may be ambiguous after
# a preliminary scan through the olson_tz object.
# 
# The array of timezones to compare must be in the order that daylight savings
# starts for the regions.
olson_ambiguity_list = {
	'America/Denver' : ['America/Denver', 'America/Mazatlan'],
	'America/Chicago' : ['America/Chicago', 'America/Mexico_City'],
	'America/Asuncion' : ['Atlantic/Stanley', 'America/Asuncion', 'America/Santiago', 'America/Campo_Grande'],
	'America/Montevideo' : ['America/Montevideo', 'America/Sao_Paulo'],
	'Asia/Beirut' : ['Asia/Gaza', 'Asia/Beirut', 'Europe/Minsk', 'Europe/Istanbul', 'Asia/Damascus', 'Asia/Jerusalem', 'Africa/Cairo'],
	'Asia/Yerevan' : ['Asia/Yerevan', 'Asia/Baku'],
	'Pacific/Auckland' : ['Pacific/Auckland', 'Pacific/Fiji'],
	'America/Los_Angeles' : ['America/Los_Angeles', 'America/Santa_Isabel'],
	'America/New_York' : ['America/Havana', 'America/New_York'],
	'America/Halifax' : ['America/Goose_Bay', 'America/Halifax'],
	'America/Godthab' : ['America/Miquelon', 'America/Godthab']
}
