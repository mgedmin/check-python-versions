import textwrap
from io import StringIO
from typing import List

import pytest

from check_python_versions.sources.github import (
    get_gha_python_versions,
    parse_gh_ver,
    update_gha_python_versions,
)
from check_python_versions.versions import Version


def v(versions: List[str]) -> List[Version]:
    return [Version.from_string(v) for v in versions]


def test_get_gha_python_versions():
    tests_yml = StringIO(textwrap.dedent("""\
        name: Python package
        on: [push]
        jobs:
          build:
            runs-on: ubuntu-latest
            strategy:
              matrix:
                python-version: [2.7, 3.5, 3.6, 3.7, 3.8]
            steps:
            - uses: actions/checkout@v2
            - name: Set up Python ${{ matrix.python-version }}
              uses: actions/setup-python@v2
              with:
                python-version: ${{ matrix.python-version }}
            - name: Install dependencies
              run: |
                python -m pip install --upgrade pip
                pip install pytest
                pip install -r requirements.txt
            - name: Test with pytest
              run: |
                pytest
    """))
    tests_yml.name = '.github/workflows/tests.yml'
    assert get_gha_python_versions(tests_yml) == v([
        '2.7', '3.5', '3.6', '3.7', '3.8',
    ])


def test_get_gha_python_versions_with_includes():
    tests_yml = StringIO(textwrap.dedent("""\
        name: Python package
        on: [push]
        jobs:
          build:
            runs-on: ubuntu-latest
            strategy:
              matrix:
                python-version: [3.7, 3.8, 3.9]
                include:
                  - python-version: "3.10"
                  - python-version: "pypy3.7"
                  - something-unrelated: foo
            # ...
    """))
    tests_yml.name = '.github/workflows/tests.yml'
    assert get_gha_python_versions(tests_yml) == v([
        '3.7', '3.8', '3.9', '3.10', 'PyPy3'
    ])


def test_get_gha_python_versions_zopefoundation():
    tests_yml = StringIO(textwrap.dedent("""\
        name: tests
        on:
          push:
            branches: [ master ]
          pull_request:
          schedule:
            - cron: '0 12 * * 0'  # run once a week on Sunday
        jobs:
          build:
            strategy:
              matrix:
                config:
                # [Python version, tox env]
                - ["3.8",   "lint"]
                - ["2.7",   "py27"]
                - ["3.5",   "py35"]
                - ["3.6",   "py36"]
                - ["3.7",   "py37"]
                - ["3.8",   "py38"]
                - ["3.9",   "py39"]
                - ["pypy2", "pypy"]
                - ["pypy3", "pypy3"]
                - ["3.8",   "coverage"]

            runs-on: ubuntu-latest
            name: ${{ matrix.config[1] }}
            steps:
            - uses: actions/checkout@v2
            - name: Set up Python
              uses: actions/setup-python@v2
              with:
                python-version: ${{ matrix.config[0] }}
            - ...
    """))
    tests_yml.name = '.github/workflows/tests.yml'
    assert get_gha_python_versions(tests_yml) == v([
        '2.7', '3.5', '3.6', '3.7', '3.8', '3.9', 'PyPy', 'PyPy3',
    ])


def test_get_gha_python_versions_no_version_matrix():
    tests_yml = StringIO(textwrap.dedent("""\
        name: Python package
        on: [push]
        jobs:
          build:
            runs-on: ${{ matrix.os }}
            strategy:
              matrix:
                os: [ubuntu-latest, macos-latest, windows-latest]
            steps:
            - ...
    """))
    tests_yml.name = '.github/workflows/tests.yml'
    assert get_gha_python_versions(tests_yml) is None


@pytest.mark.parametrize('s, expected', [
    (3.6, '3.6'),
    ('3.7', '3.7'),
    ('pypy2', 'PyPy'),
    ('pypy3', 'PyPy3'),
    ('pypy-2.7', 'PyPy'),
    ('pypy-3.6', 'PyPy3'),
    ('pypy-3.7-v7.3.3', 'PyPy3'),
])
def test_parse_gh_ver(s, expected):
    assert parse_gh_ver(s) == Version.from_string(expected)


def test_update_gha_python_versions():
    tests_yml = StringIO(textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                python-version:
                  - 2.7
                  - 3.5
                  - 3.6
                  - 3.7
                  - 3.8
            steps:
            - ...
    """))
    tests_yml.name = '.github/workflows/tests.yml'
    result = update_gha_python_versions(tests_yml, v(["3.8", "3.9", "3.10"]))
    assert "".join(result) == textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                python-version:
                  - 3.8
                  - 3.9
                  - "3.10"
            steps:
            - ...
    """)


def test_update_gha_python_versions_quote_all_of_them():
    tests_yml = StringIO(textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                python-version:
                  - "2.7"
                  - "3.5"
                  - "3.6"
                  - "3.7"
                  - "3.8"
            steps:
            - ...
    """))
    tests_yml.name = '.github/workflows/tests.yml'
    result = update_gha_python_versions(tests_yml, v(["3.8", "3.9", "3.10"]))
    assert "".join(result) == textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                python-version:
                  - "3.8"
                  - "3.9"
                  - "3.10"
            steps:
            - ...
    """)


def test_update_gha_python_versions_zopefoundation():
    tests_yml = StringIO(textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                config:
                # [Python version, tox env]
                - ["3.8",   "lint"]
                - ["2.7",   "py27"]
                - ["3.5",   "py35"]
                - ["3.6",   "py36"]
                - ["3.7",   "py37"]
                - ["3.8",   "py38"]
                - ["3.9",   "py39"]
                - ["pypy2", "pypy"]
                - ["pypy3", "pypy3"]
                - ["3.8",   "coverage"]
            steps:
            - ...
    """))
    tests_yml.name = '.github/workflows/tests.yml'
    result = update_gha_python_versions(tests_yml, v(["2.7", "3.8", "3.9"]))
    assert "".join(result) == textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                config:
                # [Python version, tox env]
                - ["3.8",   "lint"]
                - ["2.7",   "py27"]
                - ["3.8",   "py38"]
                - ["3.9",   "py39"]
                - ["pypy2", "pypy"]
                - ["pypy3", "pypy3"]
                - ["3.8",   "coverage"]
            steps:
            - ...
    """)


def test_update_gha_python_versions_quotes_3_10():
    tests_yml = StringIO(textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                config:
                # [Python version, tox env]
                - ["3.8",   "lint"]
                - ["3.8",   "py38"]
                - ["3.9",   "py39"]
                - ["pypy3", "pypy3"]
                - ["3.8",   "coverage"]
            steps:
            - ...
    """))
    tests_yml.name = '.github/workflows/tests.yml'
    result = update_gha_python_versions(tests_yml, v(["3.8", "3.9", "3.10"]))
    assert "".join(result) == textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                config:
                # [Python version, tox env]
                - ["3.8",   "lint"]
                - ["3.8",   "py38"]
                - ["3.9",   "py39"]
                - ["3.10",  "py310"]
                - ["pypy3", "pypy3"]
                - ["3.8",   "coverage"]
            steps:
            - ...
    """)


def test_update_gha_python_versions_can_drop_pypy():
    tests_yml = StringIO(textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                config:
                # [Python version, tox env]
                - ["3.8",   "lint"]
                - ["2.7",   "py27"]
                - ["3.5",   "py35"]
                - ["3.6",   "py36"]
                - ["3.7",   "py37"]
                - ["3.8",   "py38"]
                - ["3.9",   "py39"]
                - ["pypy2", "pypy"]
                - ["pypy3", "pypy3"]
                - ["3.8",   "coverage"]
            steps:
            - ...
    """))
    tests_yml.name = '.github/workflows/tests.yml'
    result = update_gha_python_versions(tests_yml, v(["3.8", "3.9"]))
    assert "".join(result) == textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                config:
                # [Python version, tox env]
                - ["3.8",   "lint"]
                - ["3.8",   "py38"]
                - ["3.9",   "py39"]
                - ["pypy3", "pypy3"]
                - ["3.8",   "coverage"]
            steps:
            - ...
    """)


def test_update_gha_python_versions_can_drop_pypy2():
    # Reg. test for https://github.com/mgedmin/check-python-versions/issues/29
    tests_yml = StringIO(textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                python-version:
                  - "2.7"
                  - "3.5"
                  - "3.6"
                  - "pypy2"
                  - "pypy3"
            steps:
              - ...
    """))
    tests_yml.name = '.github/workflows/tests.yml'
    result = update_gha_python_versions(tests_yml, v(["3.5", "3.6"]))
    assert "".join(result) == textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                python-version:
                  - "3.5"
                  - "3.6"
                  - "pypy3"
            steps:
              - ...
    """)


def test_update_gha_python_versions_can_drop_pypy3():
    # Reg. test for https://github.com/mgedmin/check-python-versions/issues/29
    tests_yml = StringIO(textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                python-version:
                  - "2.7"
                  - "3.5"
                  - "3.6"
                  - "pypy2"
                  - "pypy3"
            steps:
              - ...
    """))
    tests_yml.name = '.github/workflows/tests.yml'
    result = update_gha_python_versions(tests_yml, v(["2.7"]))
    assert "".join(result) == textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                python-version:
                  - "2.7"
                  - "pypy2"
            steps:
              - ...
    """)


def test_update_gha_python_versions_can_drop_pypy3_in_config():
    tests_yml = StringIO(textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                config:
                # [Python version, tox env]
                - ["2.7",   "py27"]
                - ["3.5",   "py35"]
                - ["3.6",   "py36"]
                - ["pypy2", "pypy"]
                - ["pypy3", "pypy3"]
            steps:
            - ...
    """))
    tests_yml.name = '.github/workflows/tests.yml'
    result = update_gha_python_versions(tests_yml, v(["2.7"]))
    assert "".join(result) == textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                config:
                # [Python version, tox env]
                - ["2.7",   "py27"]
                - ["pypy2", "pypy"]
            steps:
            - ...
    """)


def test_update_gha_python_versions_keeps_what_it_doesnt_understand():
    tests_yml = StringIO(textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                config:
                # [Python version, tox env]
                - ["3.8",   "py38"]
                - [null, null, null]
            steps:
            - ...
    """))
    tests_yml.name = '.github/workflows/tests.yml'
    result = update_gha_python_versions(tests_yml, v(["3.9"]))
    assert "".join(result) == textwrap.dedent("""\
        jobs:
          build:
            strategy:
              matrix:
                config:
                # [Python version, tox env]
                - ["3.9",   "py39"]
                - [null, null, null]
            steps:
            - ...
    """)
