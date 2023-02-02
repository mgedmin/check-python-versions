import argparse
import os
import re
import sys
import textwrap
from io import StringIO
from typing import List

import pytest

import check_python_versions.cli as cpv
from check_python_versions.sources.base import SourceFile
from check_python_versions.versions import Version


def v(versions: List[str]) -> List[Version]:
    return [Version.from_string(v) for v in versions]


def test_parse_version_list():
    assert cpv.parse_version_list(
        '2.7,3.4-3.6'
    ) == v(['2.7', '3.4', '3.5', '3.6'])


def test_parse_version_list_3_10():
    assert cpv.parse_version_list(
        '3.7-3.10'
    ) == v(['3.7', '3.8', '3.9', '3.10'])


def test_parse_version_list_magic_range(fix_max_python_3_version):
    fix_max_python_3_version(7)
    assert cpv.parse_version_list(
        '2.7,3.4-'
    ) == v(['2.7', '3.4', '3.5', '3.6', '3.7'])
    assert cpv.parse_version_list(
        '2.6,-3.4'
    ) == v(['2.6', '3.0', '3.1', '3.2', '3.3', '3.4'])


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


def test_is_package_with_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("")
    assert cpv.is_package(tmp_path)


def test_is_package_no_setup_py(tmp_path):
    assert not cpv.is_package(tmp_path)


def test_check_not_a_directory(tmp_path, capsys):
    assert not cpv.check_package(tmp_path / "xyzzy")
    assert capsys.readouterr().out == 'not a directory\n'


def test_check_not_a_package(tmp_path, capsys):
    assert not cpv.check_package(tmp_path)
    assert capsys.readouterr().out == 'no setup.py or pyproject.toml' \
                                      ' -- not a Python package?\n'


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
        setup.py says: (empty)
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
        setup.py says: 2.7, 3.6
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
        setup.py says: 2.7, 3.6
        tox.ini says:  2.7
    """)


def test_check_poetry_mismatch(tmp_path, capsys):
    poetry_pyproject = tmp_path / "pyproject.toml"
    poetry_pyproject.write_text(textwrap.dedent("""\
        [tool.poetry]
            name='foo'
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ]
    """))
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        [tox]
        envlist = py27
    """))
    assert cpv.check_versions(tmp_path) is False
    assert capsys.readouterr().out == textwrap.dedent("""\
        pyproject.toml says: 2.7, 3.6
        tox.ini says:        2.7
    """)


def test_check_setuptools_mismatch(tmp_path, capsys):
    setuptools_pyproject = tmp_path / "pyproject.toml"
    setuptools_pyproject.write_text(textwrap.dedent("""\
        [project]
            name='foo'
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ]
        [build-system]
            requires = ["setuptools", "setuptools-scm"]
            build-backend = "setuptools.build_meta"
    """))
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        [tox]
        envlist = py27
    """))
    assert cpv.check_versions(tmp_path) is False
    assert capsys.readouterr().out == textwrap.dedent("""\
        pyproject.toml says: 2.7, 3.6
        tox.ini says:        2.7
    """)


def test_check_flit_mismatch(tmp_path, capsys):
    setuptools_pyproject = tmp_path / "pyproject.toml"
    setuptools_pyproject.write_text(textwrap.dedent("""\
        [project]
            name='foo'
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ]
        [build-system]
            requires = ["flit_core >=3.2,<4"]
            build-backend = "flit_core.buildapi"
    """))
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        [tox]
        envlist = py27
    """))
    assert cpv.check_versions(tmp_path) is False
    assert capsys.readouterr().out == textwrap.dedent("""\
        pyproject.toml says: 2.7, 3.6
        tox.ini says:        2.7
    """)


def test_check_mismatch_pypy(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
                'Programming Language :: Python :: Implementation :: PyPy',
            ],
        )
    """))
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        [tox]
        envlist = py27, py36, pypy
    """))
    assert cpv.check_versions(tmp_path) is False
    assert capsys.readouterr().out == textwrap.dedent("""\
        setup.py says: 2.7, 3.6, PyPy, PyPy3
        tox.ini says:  2.7, 3.6, PyPy
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
                'Programming Language :: Python :: Implementation :: PyPy',
            ],
        )
    """))
    assert not cpv.check_versions(tmp_path, expect=v(['2.7', '3.6', '3.7']))
    assert capsys.readouterr().out == textwrap.dedent("""\
        setup.py says: 2.7, 3.6, PyPy, PyPy3
        expected:      2.7, 3.6, 3.7
    """)


def test_check_only(tmp_path, capsys):
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
    assert cpv.check_versions(tmp_path, only={'tox.ini'})
    assert capsys.readouterr().out == textwrap.dedent("""\
        tox.ini says: 2.7
    """)


def test_poetry_check_only(tmp_path, capsys):
    poetry_pyproject = tmp_path / "pyproject.toml"
    poetry_pyproject.write_text(textwrap.dedent("""\
        [tool.poetry]
            name='foo'
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ]
    """))
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        [tox]
        envlist = py27
    """))
    assert cpv.check_versions(tmp_path, only={'tox.ini'})
    assert capsys.readouterr().out == textwrap.dedent("""\
        tox.ini says: 2.7
    """)


def test_setuptools_check_only(tmp_path, capsys):
    setuptools_pyproject = tmp_path / "pyproject.toml"
    setuptools_pyproject.write_text(textwrap.dedent("""\
        [project]
            name='foo'
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ]
        [build-system]
            requires = ["setuptools", "setuptools-scm"]
            build-backend = "setuptools.build_meta"
    """))
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        [tox]
        envlist = py27
    """))
    assert cpv.check_versions(tmp_path, only={'tox.ini'})
    assert capsys.readouterr().out == textwrap.dedent("""\
        tox.ini says: 2.7
    """)


def test_flit_check_only(tmp_path, capsys):
    flit_pyproject = tmp_path / "pyproject.toml"
    flit_pyproject.write_text(textwrap.dedent("""\
        [project]
            name='foo'
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ]
        [build-system]
            requires = ["flit_core >=3.2,<4"]
            build-backend = "flit_core.buildapi"
    """))
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        [tox]
        envlist = py27
    """))
    assert cpv.check_versions(tmp_path, only={'tox.ini'})
    assert capsys.readouterr().out == textwrap.dedent("""\
        tox.ini says: 2.7
    """)


def test_check_only_glob_source(tmp_path, capsys):
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
    workflow1_yml = tmp_path / ".github/workflows/one.yml"
    workflow1_yml.parent.mkdir(parents=True)
    workflow1_yml.write_text(textwrap.dedent("""\
        jobs:
          test:
            strategy:
              matrix:
                python-version: [3.6]
    """))
    assert cpv.check_versions(tmp_path, only={
        os.path.join('.github', 'workflows', 'one.yml')
    })
    result = capsys.readouterr().out.replace(os.path.sep, '/')
    assert result == textwrap.dedent("""\
        .github/workflows/one.yml says: 3.6
    """)


def test_check_only_glob(tmp_path, capsys):
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
    workflow1_yml = tmp_path / ".github/workflows/one.yml"
    workflow1_yml.parent.mkdir(parents=True)
    workflow1_yml.write_text(textwrap.dedent("""\
        jobs:
          test:
            strategy:
              matrix:
                python-version: [3.6]
    """))
    assert cpv.check_versions(tmp_path, only={'.github/workflows/*.yml'})
    result = capsys.readouterr().out.replace(os.path.sep, '/')
    assert result == textwrap.dedent("""\
        .github/workflows/one.yml says: 3.6
    """)


def test_check_only_nothing_matches(tmp_path, capsys):
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
    assert not cpv.check_versions(tmp_path, only={'nosuchfile'})
    assert capsys.readouterr().out == textwrap.dedent("""\
        no file with version information found
    """)


def test_supported_versions_match_ignores_python_requires_upper_bound():
    sources = [
        SourceFile(title='setup.py', filename='setup.py', extract=None,
                   check_pypy_consistency=True, has_upper_bound=True,
                   pathname='setup.py', versions=v(['2.7', '3.6'])),
        SourceFile(title='python_requires', filename='setup.py', extract=None,
                   check_pypy_consistency=True, has_upper_bound=False,
                   pathname='setup.py', versions=v(['2.7', '3.6', '3.7'])),
    ]
    assert cpv.supported_versions_match(sources)


def test_update_versions(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'stdin', StringIO('y\n'))
    (tmp_path / "setup.py").write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    cpv.update_versions(tmp_path, add=v(['3.7']))
    assert (tmp_path / "setup.py").read_text() == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
                'Programming Language :: Python :: 3.7',
            ],
        )
    """)


def test_update_versions_dry_run(tmp_path):
    (tmp_path / "setup.py").write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    replacements = cpv.update_versions(tmp_path, add=v(['3.7']), dry_run=True)
    assert (tmp_path / "setup.py").read_text() == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """)
    filename = str(tmp_path / "setup.py")
    assert "".join(replacements[filename]) == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
                'Programming Language :: Python :: 3.7',
            ],
        )
    """)


def test_update_versions_dry_run_two_updaters_one_file(
    tmp_path, fix_max_python_3_version,
):
    fix_max_python_3_version(7)
    (tmp_path / "setup.py").write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>=2.7',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    replacements = cpv.update_versions(
        tmp_path, update=v(['2.7', '3.4', '3.5', '3.6', '3.7']), dry_run=True,
    )
    assert (tmp_path / "setup.py").read_text() == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>=2.7',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """)
    filename = str(tmp_path / "setup.py")
    assert "".join(replacements[filename]) == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.4',
                'Programming Language :: Python :: 3.5',
                'Programming Language :: Python :: 3.6',
                'Programming Language :: Python :: 3.7',
            ],
        )
    """)


def test_update_versions_diff(tmp_path, capsys):
    (tmp_path / "setup.py").write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    cpv.update_versions(tmp_path, add=v(['3.7']), diff=True)
    assert (tmp_path / "setup.py").read_text() == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """)
    assert (
        capsys.readouterr().out.replace(str(tmp_path) + os.path.sep, 'tmp/')
    ).expandtabs() == textwrap.dedent("""\
        --- tmp/setup.py        (original)
        +++ tmp/setup.py        (updated)
        @@ -4,5 +4,6 @@
             classifiers=[
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3.6',
        +        'Programming Language :: Python :: 3.7',
             ],
         )

    """)


def test_update_versions_no_change(tmp_path):
    (tmp_path / "setup.py").write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    assert cpv.update_versions(tmp_path, add=v(['3.6'])) == {}


def test_update_versions_only(tmp_path):
    (tmp_path / "setup.py").write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
            ],
        )
    """))
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        [tox]
        envlist = py27
    """))
    replacements = cpv.update_versions(
        tmp_path, add=v(['3.6']), only='tox.ini', dry_run=True,
    )
    assert set(replacements) == {str(tmp_path / 'tox.ini')}


def test_update_versions_computed(tmp_path):
    (tmp_path / "setup.py").write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: %s' % v
                for v in ['2.7']
            ],
        )
    """))
    replacements = cpv.update_versions(
        tmp_path, add=v(['3.6']), dry_run=True,
    )
    assert set(replacements) == set()


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
    assert '--expect: bad' in capsys.readouterr().err


@pytest.mark.parametrize('arg', ['--add', '--drop'])
def test_main_conflicting_args(monkeypatch, tmp_path, capsys, arg):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions',
        str(tmp_path),
        arg, '3.8',
        '--update', '3.6-3.7',
    ])
    with pytest.raises(SystemExit):
        cpv.main()
    assert (
        f'argument {arg}: not allowed with argument --update'
        in capsys.readouterr().err
    )


@pytest.mark.parametrize('arg', ['--diff', '--dry-run'])
def test_main_required_args(monkeypatch, tmp_path, capsys, arg):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions',
        str(tmp_path),
        arg,
    ])
    with pytest.raises(SystemExit):
        cpv.main()
    assert (
        f'argument {arg}: not allowed without --update/--add/--drop'
        in capsys.readouterr().err
    )


def test_main_diff_and_expect_and_dry_run_oh_my(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions',
        str(tmp_path),
        '--expect', '3.6-3.7',
        '--update', '3.6-3.7',
        '--diff',
    ])
    with pytest.raises(SystemExit):
        cpv.main()
    assert (
        'argument --expect: not allowed with --diff,'
        ' unless you also add --dry-run'
        in capsys.readouterr().err
    )


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


def test_main_only(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions',
        str(tmp_path),
        '--only', 'tox.ini,setup.py',
    ])
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
        envlist = py27,py36
    """))
    travis_yml = tmp_path / ".travis.yml"
    travis_yml.write_text(textwrap.dedent("""\
        python:
          - 2.7
          - 3.5
    """))
    cpv.main()
    assert (
        capsys.readouterr().out + '\n'
    ).replace(str(tmp_path) + os.path.sep, 'tmp/') == textwrap.dedent("""\
        setup.py says: 2.7, 3.6
        tox.ini says:  2.7, 3.6

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

        setup.py says:                2.7, 3.6
        expected:                     3.6, 3.7


        tmp/b:

        not a directory


        mismatch in tmp/a tmp/b!
    """)


def test_main_multiple_ok(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions',
        str(tmp_path / "a"),
        str(tmp_path / "b"),
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
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "setup.py").write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 3.6',
                'Programming Language :: Python :: 3.7',
            ],
        )
    """))
    cpv.main()
    assert (
        capsys.readouterr().out.endswith('\n\nall ok!\n')
    )


def test_main_update(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, 'stdin', StringIO('y\n'))
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions',
        str(tmp_path),
        '--add', '3.7,3.8',
    ])
    (tmp_path / "setup.py").write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    cpv.main()
    assert (
        capsys.readouterr().out
        .replace(str(tmp_path) + os.path.sep, 'tmp/')
        .expandtabs()
        .replace(' \n', '\n\n')
    ) == textwrap.dedent("""\
        --- tmp/setup.py        (original)
        +++ tmp/setup.py        (updated)
        @@ -4,5 +4,7 @@
             classifiers=[
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3.6',
        +        'Programming Language :: Python :: 3.7',
        +        'Programming Language :: Python :: 3.8',
             ],
         )

        Write changes to tmp/setup.py? [y/N]

        setup.py says: 2.7, 3.6, 3.7, 3.8
    """)
    assert (tmp_path / "setup.py").read_text() == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
                'Programming Language :: Python :: 3.7',
                'Programming Language :: Python :: 3.8',
            ],
        )
    """)


def test_main_update_rejected(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, 'stdin', StringIO('n\n'))
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions',
        str(tmp_path),
        '--add', '3.7,3.8',
    ])
    (tmp_path / "setup.py").write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    cpv.main()
    assert (
        capsys.readouterr().out
        .replace(str(tmp_path) + os.path.sep, 'tmp/')
        .expandtabs()
        .replace(' \n', '\n\n')
    ) == textwrap.dedent("""\
        --- tmp/setup.py        (original)
        +++ tmp/setup.py        (updated)
        @@ -4,5 +4,7 @@
             classifiers=[
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3.6',
        +        'Programming Language :: Python :: 3.7',
        +        'Programming Language :: Python :: 3.8',
             ],
         )

        Write changes to tmp/setup.py? [y/N]

        setup.py says: 2.7, 3.6
    """)
    assert (tmp_path / "setup.py").read_text() == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """)


def test_main_update_diff(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions',
        str(tmp_path),
        '--add', '3.7,3.8',
        '--diff',
    ])
    (tmp_path / "setup.py").write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    cpv.main()
    assert (
        capsys.readouterr().out
        .replace(str(tmp_path) + os.path.sep, 'tmp/')
        .expandtabs()
        .replace(' \n', '\n\n')
    ) == textwrap.dedent("""\
        --- tmp/setup.py        (original)
        +++ tmp/setup.py        (updated)
        @@ -4,5 +4,7 @@
             classifiers=[
                 'Programming Language :: Python :: 2.7',
                 'Programming Language :: Python :: 3.6',
        +        'Programming Language :: Python :: 3.7',
        +        'Programming Language :: Python :: 3.8',
             ],
         )

    """)
    assert (tmp_path / "setup.py").read_text() == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """)


def test_main_update_dry_run(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions',
        str(tmp_path),
        '--add', '3.7,3.8',
        '--dry-run',
    ])
    (tmp_path / "setup.py").write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    cpv.main()
    assert (
        capsys.readouterr().out
        .replace(str(tmp_path) + os.path.sep, 'tmp/')
        .expandtabs()
        .replace(' \n', '\n\n')
    ) == textwrap.dedent("""\
        setup.py says: 2.7, 3.6, 3.7, 3.8
    """)
    assert (tmp_path / "setup.py").read_text() == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """)


def test_main_handles_ctrl_c(monkeypatch):
    def raise_keyboard_interrupt():
        raise KeyboardInterrupt()
    monkeypatch.setattr(cpv, '_main', raise_keyboard_interrupt)
    with pytest.raises(SystemExit):
        cpv.main()
