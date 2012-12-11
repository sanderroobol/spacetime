import os
import wx
import spacetime.prefs

app = wx.App()

file = spacetime.prefs.get_prefs_path()
if os.path.exists(file):
	try:
		os.remove(file)
	except Exception as e:
		wx.MessageBox('Unable to reset preferences: {0}'.format(e), 'Spacetime', wx.OK | wx.ICON_ERROR)
	else:
		wx.MessageBox('Spacetime preferences have been reset.', 'Spacetime', wx.OK | wx.ICON_INFORMATION)
else:
	wx.MessageBox('Could not find preferences file. Preferences have already been reset or Spacetime has never run before.', 'Spacetime', wx.OK | wx.ICON_EXCLAMATION)

app.MainLoop()
