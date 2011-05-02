import sys, os
sys.path.append(os.path.realpath('lib'))
import spacetime.version

print """
; Based on: NSIS Modern User Interface/Basic Example Script by Joost Verburg

;--------------------------------
;Include Modern UI

  !include "MUI2.nsh"

;--------------------------------
;General

  ;Name and file
"""

print """
  Name "Spacetime #VERSION#"
  OutFile "Spacetime-#VERSION#.exe"
""".replace('#VERSION#', spacetime.version.version)

print """
  ;Default installation folder
  InstallDir "$PROGRAMFILES\Spacetime"
  
  ;Get installation folder from registry if available
  InstallDirRegKey HKCU "Software\Spacetime" ""

  ;Request application privileges for Windows Vista
  RequestExecutionLevel user

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

  File python-dist\python.exe
  File python-dist\pythonw.exe
  File python-dist\python26.dll
  File /r /x .* python-dist\Lib

  File debug.bat

  ; AUTOMATICALLY GENERATED LIST OF FILES AND DIRS
"""

uninstall_dirs = []
uninstall_files = []
os.chdir('lib')

for dirpath, dirnames, files in os.walk('spacetime'):
	dirpath = dirpath.replace('/', '\\')
	uninstall_dirs.append(dirpath)

	print '  CreateDirectory "$INSTDIR\%s"' % dirpath
	print '  SetOutPath "$INSTDIR\%s"' % dirpath
	for f in files:
		extension = f.split('.')[-1]
		if f.startswith('.') or extension in ('pyc', 'pyo', 'orig'):
			continue
		uninstall_files.append('%s\%s' % (dirpath, f))
		if extension == 'py':
			uninstall_files.append('%s\%sc' % (dirpath, f))
			uninstall_files.append('%s\%so' % (dirpath, f))
		print '  File ..\lib\%s\%s' % (dirpath, f)

print """
  ; END AUTOMATICALLY GENERATED LIST

  CreateShortCut "$INSTDIR\Spacetime.lnk" "$INSTDIR\pythonw.exe" "-m spacetime.app" "$INSTDIR\spacetime\icons\spacetime-icon.ico"
  CreateShortCut "$INSTDIR\Spacetime (presentation mode).lnk" "$INSTDIR\pythonw.exe" "-m spacetime.app --presentation" "$INSTDIR\spacetime\icons\spacetime-icon.ico"
  CreateShortCut "$INSTDIR\Spacetime (debug mode).lnk" "$INSTDIR\debug.bat" "" "$INSTDIR\spacetime\icons\spacetime-icon.ico"

  CreateDirectory "$SMPROGRAMS\Spacetime"
  CreateShortCut "$SMPROGRAMS\Spacetime\Spacetime.lnk" "$INSTDIR\pythonw.exe" "-m spacetime.app" "$INSTDIR\spacetime\icons\spacetime-icon.ico"
  CreateShortCut "$SMPROGRAMS\Spacetime\Spacetime (presentation mode).lnk" "$INSTDIR\pythonw.exe" "-m spacetime.app --presentation" "$INSTDIR\spacetime\icons\spacetime-icon.ico"
  CreateShortCut "$SMPROGRAMS\Spacetime\Spacetime (debug mode).lnk" "$INSTDIR\debug.bat" "" "$INSTDIR\spacetime\icons\spacetime-icon.ico"
  CreateShortCut "$SMPROGRAMS\Spacetime\Uninstall.lnk" "$INSTDIR\Uninstall.exe"
  
  ;Store installation folder
  WriteRegStr HKCU "Software\Spacetime" "" $INSTDIR

  ;Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

SectionEnd

;--------------------------------
;Uninstaller Section

Section "Uninstall"

  Delete "$INSTDIR\python.exe"
  Delete "$INSTDIR\pythonw.exe"
  Delete "$INSTDIR\python26.dll"
  RMDir /r "$INSTDIR\Lib"

  Delete "$INSTDIR\debug.bat"
  Delete "$INSTDIR\Spacetime.lnk"
  Delete "$INSTDIR\Spacetime (presentation mode).lnk"
  Delete "$INSTDIR\Spacetime (debug mode).lnk"

  ; AUTOMATICALLY GENERATED LIST OF FILES AND DIRS
"""

for f in uninstall_files:
	print '  Delete "$INSTDIR\%s"' % f

uninstall_dirs.reverse()
for d in uninstall_dirs:
	print '  RMDir "$INSTDIR\%s"' % d

print """
  ; END AUTOMATICALLY GENERATED LIST

  RMDir /r "$SMPROGRAMS\Spacetime"
  
  Delete "$INSTDIR\Uninstall.exe"

  RMDir "$INSTDIR"

  DeleteRegKey /ifempty HKCU "Software\Spacetime"

SectionEnd
"""
