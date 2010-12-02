default:
	@echo "no target given"

wininst:
	find win32/python-dist -name .DS_Store -print0 | xargs -0 rm -f
	cd win32 && python -c "open('installer.nsi', 'w').write(open('installer.template').read().replace('#VERSION#', '`cd ../lib/spacetime && python -c \"import version; print version.version\"`'))"
	cd win32 && makensis installer.nsi

clean:
	rm -f win32/installer.nsi
