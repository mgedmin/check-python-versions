.PHONY: all
all:
	@echo "Nothing to build."

.PHONY: test
test:                           ##: run tests
	tox -p auto

.PHONY: coverage
coverage:                       ##: measure test coverage
	tox -e coverage

##:

.PHONY: lint
lint:                           ##: run all linters
	tox -p auto -e flake8,mypy,isort,check-manifest,check-python-versions

.PHONY: flake8
flake8:                         ##: check for style problems
	tox -e flake8

.PHONY: isort
isort:                          ##: check for incorrect import ordering
	tox -e isort

.PHONY: mypy
mypy:                           ##: check for type errors
	tox -e mypy

##:

.PHONY: releasechecklist
releasechecklist: check-readme  # also release.mk will add other checks

.PHONY: check-readme
check-readme:
	@rev_line='        rev: "'"`$(PYTHON) setup.py --version`"'"' && \
	    grep -q "^$$rev_line$$" README.rst || { \
	        echo "README.rst doesn't specify $$rev_line"; \
	        echo "Please run make update-readme"; exit 1; }

.PHONY: update-readme
update-readme:
	sed -i -e 's/rev: ".*"/rev: "$(shell $(PYTHON) setup.py --version)"/' README.rst

FILE_WITH_VERSION = src/check_python_versions/__init__.py
include release.mk
HELP_SECTION_SEP = ""
