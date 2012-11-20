import os
import spacetime.prefs

file = spacetime.prefs.get_prefs_path()
if os.path.exists(file):
	try:
		os.remove(file)
	except Exception as e:
		print "Unable to reset preferences: {0}".format(e)
	else:
		print "Preferences have been reset"
else:
	print "Could not find preferences file, nothing to reset"
raw_input("Press enter to close this window")
