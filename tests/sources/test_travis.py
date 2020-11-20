import textwrap
from io import StringIO
from typing import List

import pytest

from check_python_versions.sources.travis import (
    XENIAL_SUPPORTED_PYPY_VERSIONS,
    get_travis_yml_python_versions,
    travis_normalize_py_version,
    update_travis_yml_python_versions,
)
from check_python_versions.versions import Version


def v(versions: List[str]) -> List[Version]:
    return [Version.from_string(v) for v in versions]


def test_get_travis_yml_python_versions(tmp_path):
    travis_yml = tmp_path / ".travis.yml"
    travis_yml.write_text(textwrap.dedent("""\
        python:
          - 2.7
          - 3.6
          - 3.10-dev
        matrix:
          include:
            - python: 3.7
            - name: something unrelated
        jobs:
          include:
            - python: 3.4
            - name: something unrelated
        env:
          - TOXENV=py35-docs
          - UNRELATED=variable
    """))
    assert get_travis_yml_python_versions(travis_yml) == v([
        '2.7', '3.4', '3.5', '3.6', '3.7', '3.10-dev',
    ])


def test_get_travis_yml_python_versions_no_list(tmp_path):
    travis_yml = StringIO(textwrap.dedent("""\
        python: 3.7
    """))
    travis_yml.name = '.travis.yml'
    assert get_travis_yml_python_versions(travis_yml) == v([
        '3.7',
    ])


def test_get_travis_yml_python_versions_no_python_only_matrix(tmp_path):
    travis_yml = tmp_path / ".travis.yml"
    travis_yml.write_text(textwrap.dedent("""\
        matrix:
          include:
            - python: 3.7
    """))
    assert get_travis_yml_python_versions(travis_yml) == v([
        '3.7',
    ])


@pytest.mark.parametrize('s, expected', [
    (3.6, '3.6'),
    ('3.7', '3.7'),
    ('pypy', 'PyPy'),
    ('pypy2', 'PyPy'),
    ('pypy2.7', 'PyPy'),
    ('pypy2.7-5.10.0', 'PyPy'),
    ('pypy3', 'PyPy3'),
    ('pypy3.5', 'PyPy3'),
    ('pypy3.5-5.10.1', 'PyPy3'),
    ('3.7-dev', '3.7-dev'),
    ('nightly', 'nightly'),
])
def test_travis_normalize_py_version(s, expected):
    assert travis_normalize_py_version(s) == Version.from_string(expected)


def test_update_travis_yml_python_versions():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - pypy
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, v(["2.7", "3.4"]))
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - 3.4
          - pypy
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_3_10():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        python:
          - 3.4
          - pypy3
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, v(["3.9", "3.10"]))
    # Note: we cannot say '- 3.10', that's a float and evaluates to 3.1!
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 3.9
          - "3.10"
          - pypy3
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_as_strings():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        python:
          - "3.4"
          - pypy3
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, v(["3.9"]))
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - "3.9"
          - pypy3
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_some_python_versions_as_strings():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        python:
          - 3.9
          - "3.10"
          - pypy3
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, v(["3.9", "3.10"]))
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 3.9
          - "3.10"
          - pypy3
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_drops_pypy():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - 3.4
          - pypy
          - pypy3
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, v(["3.8"]))
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 3.8
          - pypy3
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_drops_pypy3():
    # yes this test case is massively unrealistic
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - 3.4
          - pypy
          - pypy3
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, v(["2.7"]))
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - pypy
        install: pip install -e .
        script: pytest tests
     """)


def test_update_travis_yml_python_versions_keeps_dev():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        python:
          - 3.7
          - 3.8
          - 3.9-dev
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, v(["3.8"]))
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 3.8
          - 3.9-dev
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_drops_dist_trusty(monkeypatch):
    monkeypatch.setitem(
        XENIAL_SUPPORTED_PYPY_VERSIONS, 'pypy', 'pypy2.7-6.0.0')
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        dist: trusty
        python:
          - 2.7
          - pypy
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, v(["2.7", "3.7"]))
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - 3.7
          - pypy2.7-6.0.0
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_drops_sudo():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        sudo: false
        dist: xenial
        python:
          - 2.7
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, v(["2.7", "3.7"]))
    assert "".join(result) == textwrap.dedent("""\
        language: python
        dist: xenial
        python:
          - 2.7
          - 3.7
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_drops_matrix():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        python:
          - 2.6
          - 2.7
        matrix:
          include:
            - python: 3.7
              sudo: required
              dist: xenial
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, v(["2.7", "3.7"]))
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - 3.7
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_keeps_matrix():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        python:
          - 2.7
        matrix:
          include:
            - python: 2.7
              env: MINIMAL=1
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, v(["2.7", "3.7"]))
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - 3.7
        matrix:
          include:
            - python: 2.7
              env: MINIMAL=1
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_one_to_many():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        python: 2.7
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, v(["2.7", "3.4"]))
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - 3.4
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_matrix():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        matrix:
          exclude:
            - python: 2.6
          # this is where the fun begins!
          include:
            - python: 2.7
            - python: 3.3
            - python: pypy
            - name: docs
              python: 2.7
              install: pip install sphinx
              script: sphinx-build .
            - name: flake8
              python: 2.7
              install: pip install flake8
              script: flake8 .
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, v(["2.7", "3.4"]))
    assert "".join(result) == textwrap.dedent("""\
        language: python
        matrix:
          exclude:
            - python: 2.6
          # this is where the fun begins!
          include:
            - python: 2.7
            - python: 3.4
            - python: pypy
            - name: docs
              python: 2.7
              install: pip install sphinx
              script: sphinx-build .
            - name: flake8
              python: 2.7
              install: pip install flake8
              script: flake8 .
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_matrix_xenial(monkeypatch):
    monkeypatch.setitem(
        XENIAL_SUPPORTED_PYPY_VERSIONS, 'pypy', 'pypy2.7-6.0.0')
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        matrix:
          exclude:
            - python: 2.6
          # this is where the fun begins!
          include:
            - python: 2.7
            - python: 3.3
            - python: pypy
            - name: docs
              python: 2.7
              install: pip install sphinx
              script: sphinx-build .
            - name: flake8
              python: 2.7
              install: pip install flake8
              script: flake8 .
        install: pip install -e .
        script: pytest tests
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, v(["2.7", "3.7"]))
    assert "".join(result) == textwrap.dedent("""\
        language: python
        matrix:
          exclude:
            - python: 2.6
          # this is where the fun begins!
          include:
            - python: 2.7
            - python: 3.7
            - python: pypy2.7-6.0.0
            - name: docs
              python: 2.7
              install: pip install sphinx
              script: sphinx-build .
            - name: flake8
              python: 2.7
              install: pip install flake8
              script: flake8 .
        install: pip install -e .
        script: pytest tests
    """)


def test_update_travis_yml_python_versions_matrix_preserve_quotes():
    travis_yml = StringIO(textwrap.dedent("""\
        language: python
        matrix:
          include:
            - python: "2.7"
            - python: "3.3"
            - language: c
        install: pip install tox
        script: tox -e py
    """))
    travis_yml.name = '.travis.yml'
    result = update_travis_yml_python_versions(travis_yml, v(["3.8", "3.9"]))
    assert "".join(result) == textwrap.dedent("""\
        language: python
        matrix:
          include:
            - python: "3.8"
            - python: "3.9"
            - language: c
        install: pip install tox
        script: tox -e py
    """)
