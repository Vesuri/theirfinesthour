# Release archives: Psygore's two v1.1 archives (tmp/, never committed) with the new slave
# and ReadMe -> dist/ (ignored). See tools/package_release.py.
.PHONY: dist
dist:
	python3 tools/package_release.py
