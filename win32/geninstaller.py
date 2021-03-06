import sys, os
sys.path.append(os.path.realpath('lib'))
import spacetime.version

upgrade = '--upgrade' in sys.argv
pypy = '--pypy' in sys.argv


#### NSIS DETECT ACCOUNT TYPE
#
#Name "UserInfo.dll test"
#OutFile UserInfo.exe
#
#Section
#	ClearErrors
#	UserInfo::GetName
#	IfErrors Win9x
#	Pop $0
#	UserInfo::GetAccountType
#	Pop $1
#	StrCmp $1 "Admin" 0 +3
#		MessageBox MB_OK 'User "$0" is in the Administrators group'
#		Goto done
#	StrCmp $1 "Power" 0 +3
#		MessageBox MB_OK 'User "$0" is in the Power Users group'
#		Goto done
#	StrCmp $1 "User" 0 +3
#		MessageBox MB_OK 'User "$0" is just a regular user'
#		Goto done
#	StrCmp $1 "Guest" 0 +3
#		MessageBox MB_OK 'User "$0" is a guest'
#		Goto done
#	MessageBox MB_OK "Unknown error"
#	Goto done
#
#	Win9x:
#		# This one means you don't need to care about admin or
#		# not admin because Windows 9x doesn't either
#		MessageBox MB_OK "Error! This DLL can't run under Windows 9x!"
#
#	done:
#SectionEnd
#
#
#### STRCPY INTO $INSTDIR
# strCpy $INSTDIR "C:\Your\Path"
#
####


class Installer(object):
	def __init__(self):
		self.install_commands = []
		self.uninstall_files = []
		self.uninstall_dirs = []

	def install_recursively(self, srcpath, srcdir):
		oldpath = os.getcwd()
		os.chdir(srcpath)
		srcpath = srcpath.replace('/', '\\')

		for dirpath, dirnames, files in os.walk(srcdir):
			dirpath = dirpath.replace('/', '\\')
			self.uninstall_dirs.append(dirpath)

			self.install_commands.append('  CreateDirectory "$INSTDIR\%s"' % dirpath)
			self.install_commands.append('  SetOutPath "$INSTDIR\%s"' % dirpath)
			for f in files:
				extension = f.split('.')[-1]
				if f.startswith('.') or extension in ('pyc', 'pyo', 'orig'):
					continue
				self.uninstall_files.append('%s\%s' % (dirpath, f))
				if extension == 'py':
					self.uninstall_files.append('%s\%sc' % (dirpath, f))
					self.uninstall_files.append('%s\%so' % (dirpath, f))
				self.install_commands.append('  File ..\%s\%s\%s' % (srcpath, dirpath, f))
		os.chdir(oldpath)

	def print_install(self):
		print "\n".join(self.install_commands)

	def print_uninstall(self):
		for f in self.uninstall_files:
			print '  Delete "$INSTDIR\%s"' % f

		self.uninstall_dirs.reverse()
		for d in self.uninstall_dirs:
			print '  RMDir "$INSTDIR\%s"' % d


installer = Installer()
installer.install_recursively('lib', 'spacetime')
installer.install_recursively('win32', 'licenses')


print r"""
; Based on: NSIS Modern User Interface/Basic Example Script by Joost Verburg

;--------------------------------
;Include Modern UI

  !include "MUI2.nsh"

  !include "fileassoc.nsh"

;--------------------------------
;General

  ;Name and file
"""

if upgrade:
	print r"""
  Name "Spacetime upgrade {version}"
  OutFile "Spacetime-upgrade-{version}.exe"
""".format(version=spacetime.version.version)
elif pypy:
	print r"""
  Name "Spacetime with PyPy {version}"
  OutFile "Spacetime-pypy-{version}.exe"
""".format(version=spacetime.version.version)
else:
	print r"""
  Name "Spacetime {version}"
  OutFile "Spacetime-{version}.exe"
""".format(version=spacetime.version.version)

print r"""
  ;Default installation folder
  InstallDir "$PROGRAMFILES\Spacetime"
  
  ;Get installation folder from registry if available
  InstallDirRegKey HKCU "Software\Spacetime" ""

  ;Request application privileges for Windows Vista
  RequestExecutionLevel admin

;--------------------------------
;Interface Settings

  !define MUI_ABORTWARNING

;--------------------------------
;Pages

;  !insertmacro MUI_PAGE_LICENSE "${NSISDIR}\Docs\Modern UI\License.txt"
;  !insertmacro MUI_PAGE_COMPONENTS
  !insertmacro MUI_PAGE_DIRECTORY
  !insertmacro MUI_PAGE_INSTFILES
  
  !insertmacro MUI_UNPAGE_CONFIRM
  !insertmacro MUI_UNPAGE_INSTFILES
  
;--------------------------------
;Languages
 
  !insertmacro MUI_LANGUAGE "English"

;--------------------------------
;Installer Sections

Section

  SetOutPath "$INSTDIR"

  File ..\README.md
  File ..\LICENSE.txt
  File ..\CREDITS.txt
"""

if not upgrade:
	print r"""
  File python-dist\python.exe
  File python-dist\pythonw.exe
  File python-dist\python27.dll
  File python-dist\ffmpeg.exe
  File python-dist\avbin.dll
  File /r /x .* python-dist\Lib
"""
	if pypy:
		print r'  File /r /x .* python-dist\pypy'

print r"""
  File debug.bat
  File reset_preferences.py

  ; AUTOMATICALLY GENERATED LIST OF FILES AND DIRS
"""

installer.print_install()

print r"""
  ; END AUTOMATICALLY GENERATED LIST

  SetOutPath "$INSTDIR"

  CreateShortCut "$INSTDIR\Spacetime.lnk" "$INSTDIR\pythonw.exe" "-m spacetime.gui.main" "$INSTDIR\spacetime\icons\spacetime-icon.ico"
  CreateShortCut "$INSTDIR\Spacetime (debug mode).lnk" "$INSTDIR\debug.bat" "" "$INSTDIR\spacetime\icons\spacetime-icon.ico"

  CreateDirectory "$SMPROGRAMS\Spacetime"
  CreateShortCut "$SMPROGRAMS\Spacetime\Spacetime.lnk" "$INSTDIR\pythonw.exe" "-m spacetime.gui.main" "$INSTDIR\spacetime\icons\spacetime-icon.ico"
  CreateShortCut "$SMPROGRAMS\Spacetime\Spacetime (debug mode).lnk" "$INSTDIR\debug.bat" "" "$INSTDIR\spacetime\icons\spacetime-icon.ico"
"""
if pypy:
	print r'  CreateShortCut "$SMPROGRAMS\Spacetime\Spacetime (pypy, experimental).lnk" "$INSTDIR\pythonw.exe" "-m spacetime.gui.main --pypy" "$INSTDIR\spacetime\icons\spacetime-icon.ico"'

print r"""
  CreateShortCut "$SMPROGRAMS\Spacetime\Reset preferences.lnk" "$INSTDIR\pythonw.exe" "reset_preferences.py"
  CreateShortCut "$SMPROGRAMS\Spacetime\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  
  !insertmacro APP_ASSOCIATE "spacetime" "Spacetime.Project" "Spacetime project" "$INSTDIR\spacetime\icons\spacetime-project.ico" "Open with Spacetime" '$INSTDIR\pythonw.exe -m spacetime.gui.main "%1"'
  !insertmacro UPDATEFILEASSOC

  ;Store installation folder
  WriteRegStr HKCU "Software\Spacetime" "" $INSTDIR

  ;Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ExecWait '"$INSTDIR\python.exe" -m compileall "$INSTDIR\Spacetime" "$INSTDIR\Lib"'
"""
if pypy:
	print r"""  ExecWait '"$INSTDIR\pypy\pypy.exe" -m compileall "$INSTDIR\pypy"'"""

print r"""

SectionEnd

;--------------------------------
;Uninstaller Section

Section "Uninstall"

  Delete "$INSTDIR\python.exe"
  Delete "$INSTDIR\pythonw.exe"
  Delete "$INSTDIR\python27.dll"
  Delete "$INSTDIR\ffmpeg.exe"
  Delete "$INSTDIR\avbin.dll"
  Delete "$INSTDIR\README.html"
  Delete "$INSTDIR\LICENSE.txt"
  Delete "$INSTDIR\CREDITS.txt"
  RMDir /r "$INSTDIR\Lib"
"""
if pypy:
	print r'  RMDir /r "$INSTDIR\pypy"'
print r"""
  Delete "$INSTDIR\debug.bat"
  Delete "$INSTDIR\reset_preferences.py"
  Delete "$INSTDIR\Spacetime.lnk"
  Delete "$INSTDIR\Spacetime (debug mode).lnk"

  ; AUTOMATICALLY GENERATED LIST OF FILES AND DIRS
"""

installer.print_uninstall()

print r"""
  ; END AUTOMATICALLY GENERATED LIST

  RMDir /r "$SMPROGRAMS\Spacetime"

  !insertmacro APP_UNASSOCIATE "spacetime" "Spacetime.Project"
  !insertmacro UPDATEFILEASSOC
  
  Delete "$INSTDIR\Uninstall.exe"

  RMDir "$INSTDIR"

  DeleteRegKey /ifempty HKCU "Software\Spacetime"

SectionEnd
"""
