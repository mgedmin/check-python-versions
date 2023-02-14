"""
Check supported Python versions in a Python package.

Makes sure the set of supported Python versions is consistent between

- setup.py PyPI classifiers
- tox.ini default env list
- .travis-ci.yml
- appveyor.yml
- (optionally) .manylinux-install.sh as used by various ZopeFoundation projects
- .github/workflows/*.yml

"""

__author__ = 'Marius Gedminas <marius@gedmin.as>'
__version__ = '0.21.2'
