import textwrap
from io import StringIO

import pytest

try:
    import yaml
except ImportError:
    yaml = None

from check_python_versions.parsers.travis import (
    add_yaml_node,
    drop_yaml_node,
    get_travis_yml_python_versions,
    travis_normalize_py_version,
    update_travis_yml_python_versions,
    update_yaml_list,
)


needs_pyyaml = pytest.mark.skipIf(yaml is None, "PyYAML not installed")


@needs_pyyaml
def test_get_travis_yml_python_versions(tmp_path):
    travis_yml = tmp_path / ".travis.yml"
    travis_yml.write_text(textwrap.dedent("""\
        python:
          - 2.7
          - 3.6
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
    assert get_travis_yml_python_versions(travis_yml) == [
        '2.7', '3.4', '3.5', '3.6', '3.7',
    ]


@needs_pyyaml
def test_get_travis_yml_python_versions_no_python_only_matrix(tmp_path):
    travis_yml = tmp_path / ".travis.yml"
    travis_yml.write_text(textwrap.dedent("""\
        matrix:
          include:
            - python: 3.7
    """))
    assert get_travis_yml_python_versions(travis_yml) == [
        '3.7',
    ]


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
    assert travis_normalize_py_version(s) == expected


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
    result = update_travis_yml_python_versions(travis_yml, ["2.7", "3.7"])
    assert "".join(result) == textwrap.dedent("""\
        language: python
        dist: xenial
        python:
          - 2.7
          - 3.7
          - pypy2.7-6.0.0
        install: pip install -e .
        script: pytest tests
    """)


def test_update_yaml_list():
    source_lines = textwrap.dedent("""\
        language: python
        python:
          - 2.6
          - 2.7
        install: pip install -e .
        script: pytest tests
    """).splitlines(True)
    result = update_yaml_list(source_lines, "python", ["2.7", "3.7"])
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - 3.7
        install: pip install -e .
        script: pytest tests
    """)


def test_update_yaml_list_keep_indent_comments_and_pypy():
    source_lines = textwrap.dedent("""\
        language: python
        python:
           - 2.6
          # XXX: should probably remove 2.6
           - 2.7
           - pypy
           - 3.3
        script: pytest tests
    """).splitlines(True)
    result = update_yaml_list(source_lines, "python", ["2.7", "3.7"],
                              keep=lambda line: line == 'pypy')
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
           - 2.7
           - 3.7
          # XXX: should probably remove 2.6
           - pypy
        script: pytest tests
    """)


def test_drop_yaml_node():
    source_lines = textwrap.dedent("""\
        language: python
        python:
           - 3.6
        matrix:
          include:
            - python: 3.7
              dist: xenial
              sudo: required
        script: pytest tests
    """).splitlines(True)
    result = drop_yaml_node(source_lines, 'matrix')
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
           - 3.6
        script: pytest tests
    """)


def test_drop_yaml_node_when_empty():
    source_lines = textwrap.dedent("""\
        language: python
        python:
           - 3.6
        matrix:
        script: pytest tests
    """).splitlines(True)
    result = drop_yaml_node(source_lines, 'matrix')
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
           - 3.6
        script: pytest tests
    """)


def test_drop_yaml_node_when_text():
    source_lines = textwrap.dedent("""\
        language: python
        sudo: false
        python:
           - 3.6
        script: pytest tests
    """).splitlines(True)
    result = drop_yaml_node(source_lines, 'sudo')
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
           - 3.6
        script: pytest tests
    """)


def test_drop_yaml_node_when_last_in_file():
    source_lines = textwrap.dedent("""\
        language: python
        python:
           - 3.6
        matrix:
          include:
            - python: 3.7
              dist: xenial
              sudo: required
    """).splitlines(True)
    result = drop_yaml_node(source_lines, 'matrix')
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
           - 3.6
    """)


def test_add_yaml_node():
    source_lines = textwrap.dedent("""\
        language: python
        python:
           - 3.6
        script: pytest tests
    """).splitlines(True)
    result = add_yaml_node(source_lines, 'dist', 'xenial', before='python')
    assert "".join(result) == textwrap.dedent("""\
        language: python
        dist: xenial
        python:
           - 3.6
        script: pytest tests
    """)


def test_add_yaml_node_at_end():
    source_lines = textwrap.dedent("""\
        language: python
        python:
           - 3.6
        script: pytest tests
    """).splitlines(True)
    result = add_yaml_node(source_lines, 'dist', 'xenial', before='sudo')
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
           - 3.6
        script: pytest tests
        dist: xenial
    """)
