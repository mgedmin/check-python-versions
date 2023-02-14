Changelog
=========

0.21.2 (2023-02-14)
-------------------

- Ignore pyproject.toml that has no static metadata instead of
  causing a mismatch error.  `GH #41
  <https://github.com/mgedmin/check-python-versions/issues/#41>`_.

- Make sure all the error messages about parsing issues mention the name of the
  file that contains the error.


0.21.1 (2023-02-08)
-------------------

- Document pyproject.toml support in the README.


0.21.0 (2023-02-08)
-------------------

- Add support for pyproject.toml (primarily, Flit, Poetry, and setuptools,
  but any build system that specifies static PEP 621 metadata should work).
  Contributed by Gabriele Pongelli.  `GH #34
  <https://github.com/mgedmin/check-python-versions/pull/34>`_


0.20.0 (2022-10-27)
-------------------

- Add support for Python 3.11: threat it as a released version, run CI tests on
  3.11.


0.19.2 (2022-07-12)
-------------------

- Drop support for Python 3.6.

- Recognize ``include`` directives in GitHub Actions build matrixes.


0.19.1 (2021-10-13)
-------------------

- Don't complain about unbounded python_requires allowing new Python 3 releases
  when all other sources don't allow it yet.  `GH #31
  <https://github.com/mgedmin/check-python-versions/issues/31>`_


0.19.0 (2021-10-12)
-------------------

- Add support for Python 3.10: threat it as a released version, run CI tests on
  3.10.


0.18.2 (2021-09-27)
-------------------

- Don't drop all PyPy builds when adding/dropping supported versions to GitHub
  Actions files that use a build matrix based on ``python-version``.  `GH #29
  <https://github.com/mgedmin/check-python-versions/issues/#29>`_


0.18.1 (2021-07-02)
-------------------

- Treat versions like ``3.10.0-beta.3`` as prerelease versions.  `GH #28
  <https://github.com/mgedmin/check-python-versions/issues/#28>`_.


0.18.0 (2021-01-28)
-------------------

- PyPy support is now checked for consistency: if setup.py declares PyPy
  support, you need to also run tests on PyPy in your primary CI systems (tox,
  GitHub Actions, Travis CI), and vice versa.  Secondary CI systems (Appveyor,
  manylinux.sh) are excluded from this check.  `GH #26
  <https://github.com/mgedmin/check-python-versions/issues/#26>`_.


0.17.1 (2020-12-18)
-------------------

- Support ``pypy-N.M[-vX.Y.Z]`` in GitHub Actions, in addition to
  ``pypy2``/``pypy3`` (`issue 24
  <https://github.com/mgedmin/check-python-versions/issues/24>`_).


0.17.0 (2020-11-20)
-------------------

- Initial supprot for GitHub Actions (`issue 22
  <https://github.com/mgedmin/check-python-versions/issues/22>`_).
- Correctly detect the end of a YAML list even if it's not indented.
- Try to preserve envlist order in ``tox.ini``.
- Preserve quotes around Python versions in Travis matrix jobs.


0.16.1 (2020-11-08)
-------------------

- Preserve trailing commas in ``tox.ini``.
- Do not duplicate comments in ``tox.ini``.
- If all versions in .travis.yml are quoted, keep the quotes.


0.16.0 (2020-10-27)
-------------------

- Add support for Python 3.9.

- Preliminary Python 3.10 support: sort 3.10 after 3.9, quote "3.10" when
  updating YAML files so it doesn't get treated as a floating point
  number (`GH #19
  <https://github.com/mgedmin/check-python-versions/issues/19>`_)


0.15.1 (2020-08-19)
-------------------

- Correctly handle ``tox.ini`` brace expressions with spaces in them
  (e.g. ``py{35, 36}``; `GH #18
  <https://github.com/mgedmin/check-python-versions/issues/18>`_)


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
