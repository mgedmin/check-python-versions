import argparse
import os
import re
import sys
import textwrap

import pytest

import check_python_versions.cli as cpv


def test_parse_version_list():
    assert cpv.parse_version_list(
        '2.7,3.4-3.6'
    ) == ['2.7', '3.4', '3.5', '3.6']


def test_parse_version_list_magic_range(fix_max_python_3_version):
    fix_max_python_3_version(7)
    assert cpv.parse_version_list(
        '2.7,3.4-'
    ) == ['2.7', '3.4', '3.5', '3.6', '3.7']
    assert cpv.parse_version_list(
        '2.6,-3.4'
    ) == ['2.6', '3.0', '3.1', '3.2', '3.3', '3.4']


@pytest.mark.parametrize('v', [
    '4.1-',     # unknown major version
    '-',        # both endpoints missing
    '2.7-3.4',  # major versions differ
])
def test_parse_version_list_bad_range(v):
    with pytest.raises(argparse.ArgumentTypeError,
                       match=re.escape(f'bad range: {v}')):
        cpv.parse_version_list(v)


def test_parse_version_list_bad_number():
    with pytest.raises(argparse.ArgumentTypeError):
        cpv.parse_version_list('2.x')


def test_parse_version_list_too_few():
    with pytest.raises(argparse.ArgumentTypeError):
        cpv.parse_version_list('2')


def test_parse_version_list_too_many_dots():
    with pytest.raises(argparse.ArgumentTypeError):
        cpv.parse_version_list('2.7.1')


def test_is_package(tmp_path):
    (tmp_path / "setup.py").write_text("")
    assert cpv.is_package(tmp_path)


def test_is_package_no_setup_py(tmp_path):
    assert not cpv.is_package(tmp_path)


def test_check_not_a_directory(tmp_path, capsys):
    assert not cpv.check_package(tmp_path / "xyzzy")
    assert capsys.readouterr().out == 'not a directory\n'


def test_check_not_a_package(tmp_path, capsys):
    assert not cpv.check_package(tmp_path)
    assert capsys.readouterr().out == 'no setup.py -- not a Python package?\n'


def test_check_package(tmp_path):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
        )
    """))
    assert cpv.check_package(tmp_path) is True


def test_check_unknown(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
        )
    """))
    assert cpv.check_versions(tmp_path) is True
    assert capsys.readouterr().out == textwrap.dedent("""\
        setup.py says:              (empty)
    """)


def test_check_minimal(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    assert cpv.check_versions(tmp_path) is True
    assert capsys.readouterr().out == textwrap.dedent("""\
        setup.py says:              2.7, 3.6
    """)


def test_check_mismatch(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        [tox]
        envlist = py27
    """))
    assert cpv.check_versions(tmp_path) is False
    assert capsys.readouterr().out == textwrap.dedent("""\
        setup.py says:              2.7, 3.6
        tox.ini says:               2.7
    """)


def test_check_expectation(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    assert cpv.check_versions(tmp_path, expect=['2.7', '3.6', '3.7']) is False
    assert capsys.readouterr().out == textwrap.dedent("""\
        setup.py says:              2.7, 3.6
        expected:                   2.7, 3.6, 3.7
    """)


def test_main_help(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['check-python-versions', '--help'])
    with pytest.raises(SystemExit):
        cpv.main()


@pytest.mark.parametrize('arg', [
    'xyzzy',
    '1,2,3',
    '2.x',
    '1.2.3',
    '2.7-3.6',
])
def test_main_expect_error_handling(monkeypatch, arg, capsys):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions', '--expect', arg,
    ])
    with pytest.raises(SystemExit):
        cpv.main()
    # the error is either 'bad version: ...' or 'bad range: ...'
    assert f'--expect: bad' in capsys.readouterr().err


def test_main_here(monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions',
    ])
    cpv.main()
    assert 'mismatch' not in capsys.readouterr().out


def test_main_skip_non_packages(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions', '--skip-non-packages', str(tmp_path),
    ])
    cpv.main()
    assert capsys.readouterr().out == ''


def test_main_single(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions',
        str(tmp_path / "a"),
    ])
    with pytest.raises(SystemExit) as exc_info:
        cpv.main()
    assert (
        capsys.readouterr().out + str(exc_info.value) + '\n'
    ).replace(str(tmp_path), 'tmp') == textwrap.dedent("""\
        not a directory

        mismatch!
    """)


def test_main_multiple(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions',
        str(tmp_path / "a"),
        str(tmp_path / "b"),
        '--expect', '3.6, 3.7'
    ])
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "setup.py").write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    with pytest.raises(SystemExit) as exc_info:
        cpv.main()
    assert (
        capsys.readouterr().out + str(exc_info.value) + '\n'
    ).replace(str(tmp_path) + os.path.sep, 'tmp/') == textwrap.dedent("""\
        tmp/a:

        setup.py says:              2.7, 3.6
        expected:                   3.6, 3.7


        tmp/b:

        not a directory


        mismatch in tmp/a tmp/b!
    """)


def test_main_multiple_ok(monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions', '.', '.',
    ])
    cpv.main()
    assert (
        capsys.readouterr().out.endswith('\n\nall ok!\n')
    )
