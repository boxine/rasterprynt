testall: lint test

lint:
	flake8 .

test:
	python3 -m unittest discover

run:
	./test_demodhcpd.py

pypi:
	python setup.py sdist bdist_wheel upload

release:
	if test -z "${VERSION}"; then echo VERSION missing; exit 1; fi
	sed -i "s#^\(__version__\s*=\s*'\)[^']*'\$$#\1${VERSION}'#" rasterprynt/__init__.py
	sed -i "s#^\(\s*version=\s*'\)[^']*\(',.*\)\$$#\1${VERSION}\2#" setup.py
	git diff
	git add rasterprynt/__init__.py setup.py
	git commit -m "release ${VERSION}"
	git tag "v${VERSION}"
	git push
	git push --tags
	$(MAKE) pypi


.PHONY: lint test testall run