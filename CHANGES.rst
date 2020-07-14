Changelog
=========

0.15.0 (2020-07-14)
-------------------

- Add ``pre-commit`` integration. See README file for instructions.


0.14.3 (2020-07-02)
-------------------

- Recognize ``setuptools.setup()`` calls in setup.py.

- When parsing setup.py fails and check-python-versions falls back to running
  ``python setup.py --classifiers``, it will try to use python3, falling back
  to python, and then to whatever interpreter was used to run
  check-python-versions.

- Preserve formatting in ``python_requires``, e.g. when dropping 3.5,
  ``python_requires='>= 3.5'`` now becomes ``python_requires='>= 3.6'``
  instead of ``python_requires='>=3.6'``.


0.14.2 (2020-05-16)
-------------------

- When check-python-versions falls back to executing python setup.py, it
  redirects the stdin to /dev/null, to prevent freezing in case setup.py
  decides to ask the user some questions.

- Better error reporting in some obscure corner cases while parsing setup.py.

- The codebase now has docstrings and type hints, and passes mypy --strict.

- When tox.ini has an environment named 'pylint' we no longer consider this to
  be Python version l.int.

- Recognize ``PYTHON: C:\PythonXY\python.exe`` in appveyor.yml.


0.14.1 (2020-05-15)
-------------------

- Fix regression in updating tox.ini that looked like this::

      envlist =
          py27,py34,py35,py36

  0.14.0 would incorrectly expand it to ::

      envlist =
          py27
          py34
          py35
          py36


0.14.0 (2020-05-13)
-------------------

- Improvements in Python version updating:

  - preserve multiline ``python_requires=', '.join([...])`` expressions
    (`GH #10 <https://github.com/mgedmin/check-python-versions/issues/10>`_)
  - preserve generative envlists (``envlist = py{27,36}``) in tox.ini
    (`GH #13 <https://github.com/mgedmin/check-python-versions/issues/#13>`_)
  - accept ``envlist=...`` with no spaces around the ``=`` in tox.ini
  - preserve newline-separated envlists with no commas in tox.ini
  - drop PyPy when dropping all supported Python 2.x versions
    (`GH #11 <https://github.com/mgedmin/check-python-versions/issues/ #11>`_)


0.13.2 (2020-05-04)
-------------------

- More robust Appveyor parsing: accept forward slashes (c:/pythonXY), do not
  crash if the PYTHON environment variable doesn't point to a versioned Python
  directory that we recognize (`GH #12
  <https://github.com/mgedmin/check-python-versions/issues/12>`_).


0.13.1 (2020-03-23)
-------------------

- When updating a tox.ini keep multiline lists on multiple lines.


0.13.0 (2019-10-15)
-------------------

- Support Python 3.8.

- Stop adding ``dist: xenial`` to .travis.yml as that is now the default.


0.12.1 (2019-05-02)
-------------------

- Improvements in Python version updating:

  - preserve comma style in python_requires lines
  - no longer upgrade 'pypy' to 'pypy2.7-6.0.0' and 'pypy3' to 'pypy3.5-6.0.0'
    because xenial now has 'pypy' and 'pypy3' available


0.12.0 (2019-04-18)
-------------------

- Ignore unreleased Python versions (3.8 at the moment).

- Allow half-open ranges like ``--expect 3.5-``.

- Add experimental support for updating supported Python versions in
  setup.py, tox.ini, .travis.yml, appveyor.yml and .manylinux-install.sh:

  - command-line options --add and --drop to add and/or drop specific versions

  - command-line option --update to explicitly enumerate all supported versions

  - all changes are shown as diffs with confirmation before applying

  - command-line option --diff to show the diffs and exit without any prompting

  - command-line option --dry-run to re-run the parser and checker on in-memory
    copies of updated files, to see if the update would succeed

  - command-line option --only to limit the checks/update to some of the
    supported files


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
