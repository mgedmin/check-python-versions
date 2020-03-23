check-python-versions
=====================

.. image:: https://img.shields.io/pypi/v/check-python-versions.svg
    :target: https://pypi.org/project/check-python-versions/
    :alt: Latest release

.. image:: https://img.shields.io/pypi/pyversions/check-python-versions.svg
    :target: https://pypi.org/project/check-python-versions/
    :alt: Supported Python versions

.. image:: https://travis-ci.org/mgedmin/check-python-versions.svg?branch=master
    :target: https://travis-ci.org/mgedmin/check-python-versions
    :alt: Build status

.. image:: https://coveralls.io/repos/mgedmin/check-python-versions/badge.svg?branch=master
    :target: https://coveralls.io/r/mgedmin/check-python-versions
    :alt: Test coverage


This is a tool for Python package maintainers who want to explicitly state
which Python versions they support.


**The problem**: to properly support e.g. Python 2.7 and 3.5+ you have to
run tests with these Pythons.  This means

- you need a tox.ini with envlist = py27, py35, py36, py37, py38
- you need a .travis.yml with python: [ 2.7, 3.5, 3.6, 3.7, 3.8 ]
- if you support Windows, you need an appveyor.yml with %PYTHON% set to
  C:\\Python2.7, C:\\Python3.5, and so on
- if you're building manylinux wheels you need to ... you get the idea
- you have to tell the users which Python versions you support by specifying
  trove classifiers like "Programming Language :: Python :: 2.7"
- you probably also want to tell pip which versions you support by specifying
  python_requires=">= 2.7, !=3.0.* ..." because AFAIU PyPI classifiers are
  not fine-grained enough

Keeping all these lists consistent is a pain.

**The solution**: ``check-python-versions`` will compare these lists and warn
you if they don't match ::

    $ check-python-versions ~/projects/*
    /home/mg/projects/check-manifest:

    setup.py says:              2.7, 3.5, 3.6, 3.7, 3.8, PyPy
    - python_requires says:     2.7, 3.5, 3.6, 3.7, 3.8
    tox.ini says:               2.7, 3.5, 3.6, 3.7, 3.8, PyPy, PyPy3
    .travis.yml says:           2.7, 3.5, 3.6, 3.7, 3.8, PyPy, PyPy3
    appveyor.yml says:          2.7, 3.5, 3.6, 3.7, 3.8


    /home/mg/projects/dozer:

    setup.py says:              2.7, 3.5, 3.6, 3.7, 3.8
    tox.ini says:               2.7, 3.5, 3.6, 3.7, 3.8
    .travis.yml says:           2.7, 3.5, 3.6, 3.7, 3.8
    appveyor.yml says:          2.7, 3.5, 3.6, 3.7, 3.8


    /home/mg/projects/eazysvn:

    setup.py says:              2.7, 3.5, 3.6, 3.7, 3.8, PyPy
    tox.ini says:               2.7, 3.5, 3.6, 3.7, 3.8, PyPy, PyPy3
    .travis.yml says:           2.7, 3.5, 3.6, 3.7, 3.8, PyPy, PyPy3
    appveyor.yml says:          2.7, 3.5, 3.6, 3.7, 3.8

    ...

    all ok!


Installation
------------

You need Python 3.6 or newer (f-strings!) to run check-python-versions.
Install it with ::

    python3 -m pip install check-python-versions


Usage
-----

::

    $ check-python-versions --help
    usage: check-python-versions [-h] [--version] [--expect VERSIONS]
                                 [--skip-non-packages] [--only FILES]
                                 [--add VERSIONS] [--drop VERSIONS]
                                 [--update VERSIONS] [--diff] [--dry-run]
                                 [where [where ...]]

    verify that supported Python versions are the same in setup.py, tox.ini,
    .travis.yml and appveyor.yml

    positional arguments:
      where                directory where a Python package with a setup.py and
                           other files is located

    optional arguments:
      -h, --help           show this help message and exit
      --version            show program's version number and exit
      --expect VERSIONS    expect these versions to be supported, e.g. --expect
                           2.7,3.5-3.8
      --skip-non-packages  skip arguments that are not Python packages without
                           warning about them
      --only FILES         check only the specified files (comma-separated list,
                           e.g. --only tox.ini,appveyor.yml)

    updating supported version lists (EXPERIMENTAL):
      --add VERSIONS       add these versions to supported ones, e.g --add 3.8
      --drop VERSIONS      drop these versions from supported ones, e.g --drop
                           2.6,3.4
      --update VERSIONS    update the set of supported versions, e.g. --update
                           2.7,3.5-3.8
      --diff               show a diff of proposed changes
      --dry-run            verify proposed changes without writing them to disk

If run without any arguments, check-python-versions will look for a setup.py in
the current working directory.

Exit status is 0 if all Python packages had consistent version numbers (and, if
--expect is specified, those numbers match your stated expectations).

If you specify multiple directories on the command line, then all packages
that failed a check will be listed at the end of the run, separated with
spaces, for easier copying and pasting onto shell command lines.  This is
helpful when, e.g. you want to run ::

    check-python-versions ~/src/zopefoundation/*

to check all 380+ packages, and then want re-run the checks only on the failed
ones, for a faster turnabout.

There's also experimental support for updating supported Python versions
so you can do things like ::

    check-python-versions ~/projects/* --add 3.8 --dry-run --expect 2.7,3.5-3.8
    check-python-versions ~/projects/* --drop 3.4 --diff
    check-python-versions ~/projects/* --update 2.7,3.5- --dry-run --diff
    check-python-versions ~/projects/* --add 3.8 --drop=-2.6,-3.4

(the last one will show a diff for each file and ask for interactive
confirmation before making any changes.)

Programmatically updating human-writable files is difficult, so expect
bugs (and please file issues).


Files
-----

**setup.py** is the only required file; if any of the others are missing,
they'll be ignored (and this will not be considered a failure).

- **setup.py**: the ``classifiers`` argument passed to ``setup()`` is expected
  to have classifiers of the form::

        classifiers=[
            ...
            "Programming Language :: Python :: x.y",
            ...
        ],

  check-python-versions will attempt to parse the file and walk the AST to
  extract classifiers, but if that fails, it'll execute
  ``python setup.py --classifiers`` and parse the output.

  There's rudimentary support for dynamically-computed classifiers if at
  least one part is a list literal, e.g. this can work and can even be
  updated ::

        classifiers=[
            ...
            "Programming Language :: Python :: x.y",
            ...
        ] + ... expression that computes extra classifiers ...,

- **setup.py**: the ``python_requires`` argument passed to ``setup()``, if
  present::

        python_requires=">=2.7, !=3.0.*, !=3.1.*",

  check-python-versions will attempt to parse the file and walk the AST to
  extract the ``python_requires`` value.  It expects to find a string literal
  or a simple expression of the form ``"literal".join(["...", "..."])``.

- **tox.ini**: if present, it's expected to have ::

    [tox]
    envlist = pyXY, ...

  Environment names like pyXY-ZZZ are also accepted; the suffix is ignored.

- **.travis.yml**: if present, it's expected to have ::

    python:
      - X.Y
      - ...

  and/or ::

    matrix:
      include:
        - python: X.Y
          ...
        - ...

  and/or ::

    jobs:
      include:
        - python: X.Y
          ...
        - ...

  and/or ::

    env:
      - TOXENV=...

  (but not all of these forms are supported for updates)

- **appveyor.yml**: if present, it's expected to have ::

    environment:
      matrix:
        - PYTHON: C:\\PythonX.Y
        - ...

  The environment variable name is assumed to be ``PYTHON`` (case-insensitive).
  The values should be one of

  - ``X.Y``
  - ``C:\\PythonX.Y`` (case-insensitive)
  - ``C:\\PythonX.Y-x64`` (case-insensitive)

  Alternatively, you can use ``TOXENV`` with the usual values (pyXY).

  (``TOXENV`` is currently not supported for updates.)

- **.manylinux-install.sh**: if present, it's expected to contain a loop like
  ::

    for PYBIN in /opt/python/*/bin; do
        if [[ "${PYBIN}" == *"cp27"* ]] || \
           [[ "${PYBIN}" == *"cp35"* ]] || \
           [[ "${PYBIN}" == *"cp36"* ]] || \
           [[ "${PYBIN}" == *"cp37"* ]] || \
           [[ "${PYBIN}" == *"cp38"* ]]; then
            "${PYBIN}/pip" install -e /io/
            "${PYBIN}/pip" wheel /io/ -w wheelhouse/
               rm -rf /io/build /io/*.egg-info
        fi
    done

  check-python-versions will look for $PYBIN tests of the form ::

    [[ "${PYBIN}" == *"cpXY"* ]]

  where X and Y are arbitrary digits.

  These scripts are used in several zopefoundation repositories like
  zopefoundation/zope.interface.  It's the least standartized format.


Python versions
---------------

In addition to CPython X.Y, check-python-versions will recognize PyPy and PyPy3
in some of the files:

- **setup.py** may have a ::

        'Programming Language :: Python :: Implementation :: PyPy',

  classifier

- **tox.ini** may have pypy[-suffix] and pypy3[-suffix] environments

- **.travis.yml** may have pypy and pypy3 jobs with optional version suffixes
  (e.g. pypy2.7-6.0.0, pypy3.5-6.0.0)

- **appveyor.yml** and **.manylinux-install.sh** do not usually have pypy tests,
  so check-python-versions cannot recognize them.

These extra Pythons are shown, but not compared for consistency.

Upcoming Python releases (such as 3.9 in setup.py or 3.9-dev in a .travis.yml)
are also shown but do not cause mismatch errors.

In addition, ``python_requires`` in setup.py usually has a lower limit, but no
upper limit.  check-python-versions will assume this means support up to the
current Python 3.x release (3.8 at the moment).

When you're specifying Python version ranges for --expect, --add, --drop or
--update, you can use

- ``X.Y`` (e.g. ``--add 3.8``)
- ``X.Y-U.V`` for an inclusive range (e.g. ``--add 3.5-3.8``)
- ``X.Y-``, which means from X.Y until the latest known release from the X
  series (e.g. ``--add 3.5-`` is equivalent to ``--add 3.5-3.7``)
- ``-X.Y``, which is the same as ``X.0-X.Y``
  (e.g. ``--drop -3.4`` is equivalent to ``--drop 3.0-3.4``)

or a comma-separated list of the above (e.g. ``--expect 2.7,3.5-``,
``--drop -2.6,-3.4``).
