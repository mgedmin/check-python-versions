import textwrap

import pytest

from check_python_versions.parsers.tox import (
    brace_expand,
    get_tox_ini_python_versions,
    parse_envlist,
    tox_env_to_py_version,
)


def test_get_tox_ini_python_versions(tmp_path):
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        [tox]
        envlist = py27,py36,py27-docs
    """))
    assert get_tox_ini_python_versions(tox_ini) == ['2.7', '3.6']


def test_get_tox_ini_python_versions_no_tox_ini(tmp_path):
    tox_ini = tmp_path / "tox.ini"
    assert get_tox_ini_python_versions(tox_ini) == []


def test_get_tox_ini_python_versions_syntax_error(tmp_path):
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        ...
    """))
    assert get_tox_ini_python_versions(tox_ini) == []


def test_get_tox_ini_python_versions_no_tox_section(tmp_path):
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        [flake8]
        source = foo
    """))
    assert get_tox_ini_python_versions(tox_ini) == []


def test_get_tox_ini_python_versions_no_tox_envlist(tmp_path):
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        [tox]
        minversion = 3.4.0
    """))
    assert get_tox_ini_python_versions(tox_ini) == []


@pytest.mark.parametrize('s, expected', [
    ('', []),
    ('py36,py37', ['py36', 'py37']),
    ('py36, py37', ['py36', 'py37']),
    ('\n  py36,\n  py37', ['py36', 'py37']),
    ('py3{6,7},pypy', ['py36', 'py37', 'pypy']),
])
def test_parse_envlist(s, expected):
    assert parse_envlist(s) == expected


@pytest.mark.parametrize('s, expected', [
    ('', ['']),
    ('py36', ['py36']),
    ('py3{6,7}', ['py36', 'py37']),
    ('py3{6,7}-lint', ['py36-lint', 'py37-lint']),
    ('py3{6,7}{,-lint}', ['py36', 'py36-lint', 'py37', 'py37-lint']),
])
def test_brace_expand(s, expected):
    assert brace_expand(s) == expected


@pytest.mark.parametrize('s, expected', [
    ('py36', '3.6'),
    ('py37-lint', '3.7'),
    ('pypy', 'PyPy'),
    ('pypy3', 'PyPy3'),
    ('flake8', 'flake8'),
])
def test_tox_env_to_py_version(s, expected):
    assert tox_env_to_py_version(s) == expected
