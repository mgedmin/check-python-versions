check-python-versions
=====================

This is a tool for Python package maintainers who want to explicitly state
which Python versions they support.


**The problem**: to properly support e.g. Python 2.7 and 3.4+ you have to
run tests with these Pythons.  This means

- you need a tox.ini with envlist = py27, py34, py35, py36, py37
- you need a .travis.yml with python: [ 2.7, 3.4, 3.5, 3.6, 3.7 ]
- if you support Windows, you need an appveyor.yml with %PYTHON% set to
  C:\\Python2.7, C:\\Python3.4, and so on
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

    setup.py says:              2.7, 3.4, 3.5, 3.6, 3.7, PyPy
    - python_requires says:     2.7, 3.4, 3.5, 3.6, 3.7
    tox.ini says:               2.7, 3.4, 3.5, 3.6, 3.7, PyPy, PyPy3
    .travis.yml says:           2.7, 3.4, 3.5, 3.6, 3.7, PyPy, PyPy3
    appveyor.yml says:          2.7, 3.4, 3.5, 3.6, 3.7


    /home/mg/projects/dozer:

    setup.py says:              2.7, 3.4, 3.5, 3.6, 3.7
    tox.ini says:               2.7, 3.4, 3.5, 3.6, 3.7
    .travis.yml says:           2.7, 3.4, 3.5, 3.6, 3.7
    appveyor.yml says:          2.7, 3.4, 3.5, 3.6, 3.7


    /home/mg/projects/eazysvn:

    setup.py says:              2.7, 3.4, 3.5, 3.6, 3.7, PyPy
    tox.ini says:               2.7, 3.4, 3.5, 3.6, 3.7, PyPy, PyPy3
    .travis.yml says:           2.7, 3.4, 3.5, 3.6, 3.7, PyPy, PyPy3
    appveyor.yml says:          2.7, 3.4, 3.5, 3.6, 3.7

    ...

    all ok!

