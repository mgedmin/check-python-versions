
.PHONY: all
all:
	@echo "Nothing to build."


.PHONY: test check
test check:
	tox


.PHONY: coverage
coverage:
	tox -e coverage


.PHONY: flake8
flake8:
	flake8 src setup.py

include release.mk
