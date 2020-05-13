import textwrap
from io import StringIO

import pytest

from check_python_versions.parsers.tox import (
    brace_expand,
    get_tox_ini_python_versions,
    parse_envlist,
    tox_env_to_py_version,
    update_ini_setting,
    update_tox_envlist,
    update_tox_ini_python_versions,
)


def test_get_tox_ini_python_versions(tmp_path):
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        [tox]
        envlist = py27,py36,py27-docs
    """))
    assert get_tox_ini_python_versions(tox_ini) == ['2.7', '3.6']


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


def test_update_tox_ini_python_versions():
    fp = StringIO(textwrap.dedent("""\
        [tox]
        envlist = py26, py27
    """))
    result = update_tox_ini_python_versions(fp, ['3.6', '3.7'])
    assert "".join(result) == textwrap.dedent("""\
        [tox]
        envlist = py36, py37
    """)


def test_update_tox_ini_python_syntax_error(capsys):
    fp = StringIO(textwrap.dedent("""\
        [tox
        envlist = py26, py27
    """))
    fp.name = 'tox.ini'
    result = update_tox_ini_python_versions(fp, ['3.6', '3.7'])
    assert "".join(result) == textwrap.dedent("""\
        [tox
        envlist = py26, py27
    """)
    assert (
        "Could not parse tox.ini:"
        in capsys.readouterr().err
    )


def test_update_tox_envlist():
    result = update_tox_envlist('py26,py27,pypy,flake8', ['3.6', '3.7'])
    assert result == 'py36,py37,pypy,flake8'


def test_update_tox_envlist_with_suffixes():
    result = update_tox_envlist(
        'py27,py34,py35,py36,py37,py27-numpy,py37-numpy,pypy,pypy3',
        ['3.6', '3.7'])
    assert result == 'py36,py37,py37-numpy,pypy,pypy3'


def test_update_tox_envlist_with_spaces():
    result = update_tox_envlist(
        'py27, py34, py35, pypy3',
        ['3.6', '3.7'])
    assert result == 'py36, py37, pypy3'


@pytest.mark.parametrize('s, expected', [
    # note that configparser trims leading whitespace, so \n is never
    # followed by a space
    ('py27,\npy34,\npy35,\npypy3', 'py36,\npy37,\npypy3'),
    ('py27\npy34\npy35\npypy3', 'py36\npy37\npypy3'),
])
def test_update_tox_envlist_with_newlines(s, expected):
    result = update_tox_envlist(s, ['3.6', '3.7'])
    assert result == expected


@pytest.mark.parametrize('s, expected', [
    # these are contrived
    ('py{27,34,35,36,37}{,-foo,-bar},docs', 'py{36,37}{,-foo,-bar},docs'),
    ('py{27,34,py,py3}', 'py{36,37,py,py3}'),
    ('py27,py30,py{ramid,gmalion}', 'py36,py37,py{ramid,gmalion}'),
    ('py{27,34,py,py3},py{27,34}-docs', 'py{36,37,py,py3},py{36,37}-docs'),
    ('py{27,36,27-extra,36-docs}', 'py36,py37,py36-docs'),
    # these were taken from tox's documentation at
    # https://tox.readthedocs.io/en/latest/config.html#generative-envlist
    ('{py36,py27}-django{15,16}', '{py36,py37}-django{15,16}'),
    ('{py27,py36}-django{ 15, 16 }, docs, flake',
     '{py36,py37}-django{ 15, 16 }, docs, flake'),
    # these are examples from real projects
    ('py{27,py,34,35,36}-{test,stylecheck}', 'py{36,37,py}-{test,stylecheck}'),
    # pyjwt
    ('lint\n'
     'typing\n'
     'py{35,36,37,38}-crypto\n'
     'py{35,36,37,38}-contrib_crypto\n'
     'py{35,36,37,38}-nocrypto',
     'lint\n'
     'typing\n'
     'py{36,37}-crypto\n'
     'py{36,37}-contrib_crypto\n'
     'py{36,37}-nocrypto'),
])
def test_update_tox_envlist_with_braces(s, expected):
    result = update_tox_envlist(s, ['3.6', '3.7'])
    assert result == expected


def test_update_ini_setting():
    source_lines = textwrap.dedent("""\
        [tox]
        envlist = py26,py27
        usedevelop = true
    """).splitlines(True)
    result = update_ini_setting(source_lines, 'tox', 'envlist', 'py36,py37')
    assert "".join(result) == textwrap.dedent("""\
        [tox]
        envlist = py36,py37
        usedevelop = true
    """)


def test_update_ini_setting_nospaces():
    source_lines = textwrap.dedent("""\
        [tox]
        envlist=py26,py27
        usedevelop=true
    """).splitlines(True)
    result = update_ini_setting(source_lines, 'tox', 'envlist', 'py36,py37')
    assert "".join(result) == textwrap.dedent("""\
        [tox]
        envlist=py36,py37
        usedevelop=true
    """)


def test_update_ini_setting_from_empty():
    source_lines = textwrap.dedent("""\
        [tox]
        envlist =
        usedevelop = true
    """).splitlines(True)
    result = update_ini_setting(source_lines, 'tox', 'envlist', 'py36,py37')
    assert "".join(result) == textwrap.dedent("""\
        [tox]
        envlist = py36,py37
        usedevelop = true
    """)


def test_update_ini_setting_multiline():
    source_lines = textwrap.dedent("""\
        [tox]
        envlist =
            py26,
            py27
        usedevelop = true
    """).splitlines(True)
    result = update_ini_setting(source_lines, 'tox', 'envlist', 'py36,\npy37')
    assert "".join(result) == textwrap.dedent("""\
        [tox]
        envlist =
            py36,
            py37
        usedevelop = true
    """)


def test_update_ini_setting_multiline_first_on_same_line():
    source_lines = textwrap.dedent("""\
        [tox]
        envlist = py26,
                  py27
        usedevelop = true
    """).splitlines(True)
    result = update_ini_setting(source_lines, 'tox', 'envlist', 'py36,\npy37')
    assert "".join(result) == textwrap.dedent("""\
        [tox]
        envlist = py36,
                  py37
        usedevelop = true
    """)


def test_update_ini_setting_multiline_with_comments():
    source_lines = textwrap.dedent("""\
        [tox]
        envlist =
        # blah blah
        #   py26,py27,pypy
            py26,py27
        usedevelop = true
    """).splitlines(True)
    result = update_ini_setting(source_lines, 'tox', 'envlist', 'py36,py37')
    assert "".join(result) == textwrap.dedent("""\
        [tox]
        envlist =
        # blah blah
        #   py26,py27,pypy
            py36,py37
        usedevelop = true
    """)


def test_update_ini_setting_no_section(capsys):
    source_lines = textwrap.dedent("""\
        [toxx]
    """).splitlines(True)
    result = update_ini_setting(source_lines, 'tox', 'envlist', 'py36,py37')
    assert "".join(result) == textwrap.dedent("""\
        [toxx]
    """)
    assert (
        "Did not find [tox] section in tox.ini"
        in capsys.readouterr().err
    )


def test_update_ini_setting_no_key(capsys):
    source_lines = textwrap.dedent("""\
        [tox]
        usedevelop = true
    """).splitlines(True)
    result = update_ini_setting(source_lines, 'tox', 'envlist', 'py36,py37')
    assert "".join(result) == textwrap.dedent("""\
        [tox]
        usedevelop = true
    """)
    assert (
        "Did not find envlist= in [tox] in tox.ini"
        in capsys.readouterr().err
    )
