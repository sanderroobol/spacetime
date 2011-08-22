default:
	@echo "no target given"

tgz:
	hg archive -t tgz spacetime-`cd lib && python -c 'import spacetime.version; print spacetime.version.version'`.tgz

wininst:
	python win32/geninstaller.py > win32/installer.nsi
	cd win32 && makensis installer.nsi

clean:
	rm -f win32/installer.nsi
