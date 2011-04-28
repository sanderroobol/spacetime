default:
	@echo "no target given"

wininst:
	python win32/geninstaller.py > win32/installer.nsi
	cd win32 && makensis installer.nsi

clean:
	rm -f win32/installer.nsi
