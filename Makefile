
.PHONY: all
all:
	@echo "Nothing to build."


.PHONY: test check
test check:
	tox


.PHONY: coverage
coverage:
	tox -e coverage


include release.mk
