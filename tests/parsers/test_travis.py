import textwrap
from io import StringIO

import pytest

try:
    import yaml
except ImportError:
    yaml = None

from check_python_versions.parsers.travis import (
    XENIAL_SUPPORTED_PYPY_VERSIONS,
    add_yaml_node,
    drop_yaml_node,
    get_travis_yml_python_versions,
    travis_normalize_py_version,
    update_travis_yml_python_versions,
    update_yaml_list,
)


needs_pyyaml = pytest.mark.skipif(yaml is None, reason="PyYAML not installed")


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
def test_get_travis_yml_python_versions_no_list(tmp_path):
    travis_yml = StringIO(textwrap.dedent("""\
        python: 3.7
    """))
    travis_yml.name = '.travis.yml'
    assert get_travis_yml_python_versions(travis_yml) == [
        '3.7',
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
    result = update_travis_yml_python_versions(travis_yml, ["2.7", "3.4"])
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
          - 2.7
          - 3.4
          - pypy
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
    result = update_travis_yml_python_versions(travis_yml, ["2.7", "3.7"])
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
    result = update_travis_yml_python_versions(travis_yml, ["2.7", "3.7"])
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
    result = update_travis_yml_python_versions(travis_yml, ["2.7", "3.7"])
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
    result = update_travis_yml_python_versions(travis_yml, ["2.7", "3.7"])
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
    result = update_travis_yml_python_versions(travis_yml, ["2.7", "3.4"])
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
    result = update_travis_yml_python_versions(travis_yml, ["2.7", "3.4"])
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
    result = update_travis_yml_python_versions(travis_yml, ["2.7", "3.7"])
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


def test_update_yaml_list_not_found(capsys):
    source_lines = textwrap.dedent("""\
        language: python
        install: pip install -e .
        script: pytest tests
    """).splitlines(True)
    result = update_yaml_list(source_lines, "python", ["2.7", "3.7"])
    assert "".join(result) == textwrap.dedent("""\
        language: python
        install: pip install -e .
        script: pytest tests
    """)
    assert (
        "Did not find python: setting in .travis.yml"
        in capsys.readouterr().err
    )


def test_update_yaml_list_nested_keys_not_found(capsys):
    source_lines = textwrap.dedent("""\
        language: python
        matrix:
          allow_failures:
            - python: 3.8
        install: pip install -e .
        script: pytest tests
    """).splitlines(True)
    result = update_yaml_list(
        source_lines, ("matrix", "include"), ["python: 2.7"])
    assert "".join(result) == textwrap.dedent("""\
        language: python
        matrix:
          allow_failures:
            - python: 3.8
        install: pip install -e .
        script: pytest tests
    """)
    assert (
        "Did not find matrix.include: setting in .travis.yml"
        in capsys.readouterr().err
    )


def test_update_yaml_list_nesting_does_not_confuse():
    source_lines = textwrap.dedent("""\
        language: python
        matrix:
          include:

            - name: flake8
              script:
                - flake8

            - python: 2.7
              env:
                - PURE_PYTHON: 1
          allow_failures:
            - python: 3.8
        install: pip install -e .
        script: pytest tests
    """).splitlines(True)
    result = update_yaml_list(
        source_lines, ("matrix", "include"), [],
        keep=lambda job: job.startswith('python:'))
    assert "".join(result) == textwrap.dedent("""\
        language: python
        matrix:
          include:
            - python: 2.7
              env:
                - PURE_PYTHON: 1
          allow_failures:
            - python: 3.8
        install: pip install -e .
        script: pytest tests
    """)


def test_update_yaml_list_nesting_some_garbage():
    source_lines = textwrap.dedent("""\
        language: python
        matrix:
          include:
            - python: 2.7
            garbage
        install: pip install -e .
        script: pytest tests
    """).splitlines(True)
    result = update_yaml_list(
        source_lines, ("matrix", "include"), ['python: 2.7'])
    assert "".join(result) == textwrap.dedent("""\
        language: python
        matrix:
          include:
            - python: 2.7
            garbage
        install: pip install -e .
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


def test_drop_yaml_node_when_duplicate(capsys):
    source_lines = textwrap.dedent("""\
        language: python
        sudo: false
        matrix:
          include:
            - python: 2.7
        python:
           - 3.6
        matrix:
          include:
            - python: 3.7
        script: pytest tests
    """).splitlines(True)
    result = drop_yaml_node(source_lines, 'matrix')
    assert "".join(result) == textwrap.dedent("""\
        language: python
        sudo: false
        matrix:
          include:
            - python: 2.7
        python:
           - 3.6
        script: pytest tests
    """)
    assert (
        "Duplicate matrix: setting in .travis.yml (lines 3 and 8)"
        in capsys.readouterr().err
    )


def test_add_yaml_node():
    source_lines = textwrap.dedent("""\
        language: python
        python:
           - 3.6
        script: pytest tests
    """).splitlines(True)
    result = add_yaml_node(source_lines, 'dist', 'xenial')
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
           - 3.6
        script: pytest tests
        dist: xenial
    """)


def test_add_yaml_node_before():
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


def test_add_yaml_node_at_end_when_before_not_found():
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


def test_add_yaml_node_before_alternatives():
    source_lines = textwrap.dedent("""\
        language: python
        python:
           - 3.6
        script: pytest tests
    """).splitlines(True)
    result = add_yaml_node(source_lines, 'dist', 'xenial',
                           before=('sudo', 'python'))
    assert "".join(result) == textwrap.dedent("""\
        language: python
        dist: xenial
        python:
           - 3.6
        script: pytest tests
    """)
