Changelog
=========

0.12.0 (unreleased)
-------------------

- Ignore unreleased Python versions (3.8 at the moment).

- Allow half-open ranges like ``--expect 3.5-``.


0.11.0 (2019-02-13)
-------------------

- Implement a full PEP-440 parser for python_requires.


0.10.0 (2018-12-11)
-------------------

- Do not consider "X.Y-dev" in .travis.yml as support for Python X.Y.
- Print warnings to stderr, not stdout.
- Add a test suite.
- Fix a lot of minor buglets.


0.9.2 (2018-12-03)
------------------

- Strip trailing spaces from classifiers.


0.9.1 (2018-11-30)
------------------

- Parse TOXENV in appveyor.yml.


0.9.0 (2018-11-19)
------------------

- Handle syntax errors while parsing setup.py.
- Handle 'Programming Language :: Python :: {N} :: Only" classifiers.
- New option: --skip-non-packages.


0.8.0 (2018-11-16)
------------------

- First public release.
