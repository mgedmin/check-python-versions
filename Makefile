.PHONY: all
all:
	@echo "Nothing to build."

.PHONY: test
test:                           ##: run tests
	tox -p auto

.PHONY: coverage
coverage:                       ##: measure test coverage
	tox -e coverage

.PHONY: flake8
flake8:                         ##: check for style problems
	flake8 src setup.py


FILE_WITH_VERSION = src/check_python_versions/__init__.py
include release.mk
