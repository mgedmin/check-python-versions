import textwrap
from io import StringIO
from typing import List

import pytest

from check_python_versions.sources.github import (
    get_gha_python_versions,
    parse_gh_ver,
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
])
def test_parse_gh_ver(s, expected):
    assert parse_gh_ver(s) == Version.from_string(expected)
