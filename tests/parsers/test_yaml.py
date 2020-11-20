import textwrap

import pytest

from check_python_versions.parsers.yaml import (
    add_yaml_node,
    drop_yaml_node,
    quote_string,
    update_yaml_list,
)


@pytest.mark.parametrize('s, expected', [
    ('', ''),
    ('3.1', '3.1'),
    ('3.10', '"3.10"'),
    ('pypy', 'pypy'),
])
def test_quote_string(s, expected):
    assert quote_string(s) == expected


def test_update_yaml_list():
    source_lines = textwrap.dedent("""\
        language: python
        python:
          - 2.6
          - 2.7
        install: pip install -e .
        script: pytest tests
    """).splitlines(True)
    result = update_yaml_list(source_lines, "python", ["2.7", "3.7"],
                              filename='.travis.yml')
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
                              keep=lambda line: line == 'pypy',
                              filename='.travis.yml')
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
           - 2.7
           - 3.7
          # XXX: should probably remove 2.6
           - pypy
        script: pytest tests
    """)


def test_update_yaml_list_keep_before_and_after():
    source_lines = textwrap.dedent("""\
        jobs:
          - lint
          - py27
          - py35
          - coverage
    """).splitlines(True)
    result = update_yaml_list(source_lines, "jobs", ["py27", "py38"],
                              keep=lambda line: line in {'lint', 'coverage'},
                              filename='ci.yml')
    assert "".join(result) == textwrap.dedent("""\
        jobs:
          - lint
          - py27
          - py38
          - coverage
    """)


def test_update_yaml_list_no_indent():
    source_lines = textwrap.dedent("""\
        matrix:
          python:
          - 2.7
          - 3.5
          os:
          - linux
          - windows
    """).splitlines(True)
    result = update_yaml_list(source_lines, ("matrix", "python"),
                              ["2.7", "3.8"], filename='ci.yml')
    assert "".join(result) == textwrap.dedent("""\
        matrix:
          python:
          - 2.7
          - 3.8
          os:
          - linux
          - windows
    """)


def test_update_yaml_list_not_found(capsys):
    source_lines = textwrap.dedent("""\
        language: python
        install: pip install -e .
        script: pytest tests
    """).splitlines(True)
    result = update_yaml_list(source_lines, "python", ["2.7", "3.7"],
                              filename='.travis.yml')
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
        source_lines, ("matrix", "include"), ["python: 2.7"],
        filename='.travis.yml')
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
        keep=lambda job: job.startswith('python:'),
        filename='.travis.yml')
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
        source_lines, ("matrix", "include"), ['python: 2.7'],
        filename='.travis.yml')
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
    result = drop_yaml_node(source_lines, 'matrix',
                            filename='.travis.yml')
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
    result = drop_yaml_node(source_lines, 'matrix',
                            filename='.travis.yml')
    assert "".join(result) == textwrap.dedent("""\
        language: python
        python:
           - 3.6
        script: pytest tests
    """)


def test_drop_yaml_node_when_missing():
    source_lines = textwrap.dedent("""\
        language: python
        python:
           - 3.6
        script: pytest tests
    """).splitlines(True)
    result = drop_yaml_node(source_lines, 'matrix',
                            filename='.travis.yml')
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
    result = drop_yaml_node(source_lines, 'sudo',
                            filename='.travis.yml')
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
    result = drop_yaml_node(source_lines, 'matrix',
                            filename='.travis.yml')
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
    result = drop_yaml_node(source_lines, 'matrix',
                            filename='.travis.yml')
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
