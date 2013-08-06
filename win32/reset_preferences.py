import os
import wx
import spacetime.util

app = wx.App(redirect=False)

try: # put in some extra effort to always show a wx.MessageBox
	file = spacetime.util.get_persistant_path('preferences')
	if os.path.exists(file):
		try:
			raise Exception()
			os.remove(file)
		except Exception as e:
			wx.MessageBox('Unable to reset preferences: {0}'.format(e), 'Spacetime', wx.OK | wx.ICON_ERROR)
		else:
			wx.MessageBox('Spacetime preferences have been reset.', 'Spacetime', wx.OK | wx.ICON_INFORMATION)
	else:
		wx.MessageBox('Could not find preferences file. Preferences have already been reset or Spacetime has never run before.', 'Spacetime', wx.OK | wx.ICON_EXCLAMATION)
except Exception as e:
	wx.MessageBox('An unexpected error occurred: {0!r}'.format(e), 'Spacetime', wx.OK | wx.ICON_ERROR)

app.MainLoop()
