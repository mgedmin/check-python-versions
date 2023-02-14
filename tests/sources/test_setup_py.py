import os
import shutil
import sys
import textwrap
from io import StringIO
from typing import List

import pytest

from check_python_versions.sources.setup_py import (
    find_python,
    get_python_requires,
    get_setup_py_keyword,
    get_supported_python_versions,
    update_python_requires,
    update_setup_py_keyword,
    update_supported_python_versions,
)
from check_python_versions.versions import Version


def v(versions: List[str]) -> List[Version]:
    return [Version.from_string(v) for v in versions]


def stderr(capsys, tmp_path=None) -> str:
    err = capsys.readouterr().err
    if tmp_path:
        err = err.replace(str(tmp_path), '/tmp').replace(os.path.sep, '/')
    return err


def assert_stderr(message, capsys, tmp_path=None):
    err = stderr(capsys, tmp_path)
    assert message in err


def test_get_supported_python_versions(tmp_path):
    filename = tmp_path / "setup.py"
    filename.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
                'Programming Language :: Python :: 3.10',
            ],
        )
    """))
    assert get_supported_python_versions(filename) == v(['2.7', '3.6', '3.10'])


def test_get_supported_python_versions_computed(tmp_path):
    filename = tmp_path / "setup.py"
    filename.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: %s' % v
                for v in ['2.7', '3.7']
            ],
        )
    """))
    assert get_supported_python_versions(filename) == v(['2.7', '3.7'])


def test_get_supported_python_versions_string(tmp_path, capsys):
    filename = tmp_path / "setup.py"
    filename.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers='''
                Programming Language :: Python :: 2.7
                Programming Language :: Python :: 3.6
            ''',
        )
    """))
    assert get_supported_python_versions(filename) == []
    assert_stderr(
        "The value passed to setup(classifiers=...) in /tmp/setup.py"
        " is not a list",
        capsys, tmp_path,
    )


def test_get_supported_python_versions_from_file_object_cannot_run_setup_py():
    fp = StringIO(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: %s' % v
                for v in ['2.7', '3.7']
            ],
        )
    """))
    fp.name = 'setup.py'
    assert get_supported_python_versions(fp) == []


def test_update_supported_python_versions_not_literal(tmp_path, capsys):
    filename = tmp_path / "setup.py"
    filename.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: %s' % v
                for v in ['2.7', '3.7']
            ],
        )
    """))
    assert update_supported_python_versions(filename,
                                            v(['3.7', '3.8'])) is None
    assert_stderr(
        'Non-literal classifiers= passed to setup() in /tmp/setup.py',
        capsys, tmp_path,
    )


def test_update_supported_python_versions_not_a_list(tmp_path, capsys):
    filename = tmp_path / "setup.py"
    filename.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers='''
                Programming Language :: Python :: 2.7
                Programming Language :: Python :: 3.6
            ''',
        )
    """))
    assert update_supported_python_versions(filename,
                                            v(['3.7', '3.8'])) is None
    assert_stderr(
        'The value passed to setup(classifiers=...) in /tmp/setup.py'
        ' is not a list',
        capsys, tmp_path,
    )


def test_get_python_requires(tmp_path, fix_max_python_3_version):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>= 3.6',
        )
    """))
    fix_max_python_3_version(7)
    assert get_python_requires(setup_py) == v(['3.6', '3.7'])
    fix_max_python_3_version(10)
    assert get_python_requires(setup_py) == v([
        '3.6', '3.7', '3.8', '3.9', '3.10',
    ])


def test_get_python_requires_not_specified(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
        )
    """))
    assert get_python_requires(setup_py) is None
    assert capsys.readouterr().err == ''


def test_get_python_requires_not_a_string(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires=['>= 3.6'],
        )
    """))
    assert get_python_requires(setup_py) is None
    assert_stderr(
        'The value passed to setup(python_requires=...) in /tmp/setup.py'
        ' is not a string',
        capsys, tmp_path,
    )


def test_get_setup_py_keyword_syntax_error(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
        # uh do I need to close parens?  what if I forget? ;)
    """))
    assert get_setup_py_keyword(setup_py, 'name') is None
    assert_stderr(
        'Could not parse /tmp/setup.py',
        capsys, tmp_path,
    )


def test_get_setup_py_keyword_dotted_call(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        import setuptools
        setuptools.setup(
            name='foo',
        )
    """))
    assert get_setup_py_keyword(setup_py, 'name') == 'foo'


def test_update_setup_py_keyboard_dotted_call(tmp_path):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        import setuptools
        setuptools.setup(
            name='foo',
        )
    """))
    result = update_setup_py_keyword(setup_py, 'name', 'bar')
    assert "".join(result) == textwrap.dedent("""\
        import setuptools
        setuptools.setup(
            name='bar',
        )
    """)


def test_update_python_requires(tmp_path, fix_max_python_3_version):
    fix_max_python_3_version(7)
    filename = tmp_path / "setup.py"
    filename.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>= 3.4',
        )
    """))
    result = update_python_requires(filename, v(['3.5', '3.6', '3.7']))
    assert result is not None
    assert "".join(result) == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>= 3.5',
        )
    """)


def test_update_python_requires_file_object(fix_max_python_3_version):
    fix_max_python_3_version(7)
    fp = StringIO(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>=3.4',
        )
    """))
    fp.name = "setup.py"
    result = update_python_requires(fp, v(['3.5', '3.6', '3.7']))
    assert result is not None
    assert "".join(result) == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>=3.5',
        )
    """)


def test_update_python_requires_when_missing(capsys):
    fp = StringIO(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
        )
    """))
    fp.name = "setup.py"
    result = update_python_requires(fp, v(['3.5', '3.6', '3.7']))
    assert result is None
    assert capsys.readouterr().err == ""


def test_update_python_requires_preserves_style(fix_max_python_3_version):
    fix_max_python_3_version(2)
    fp = StringIO(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>=2.7,!=3.0.*',
        )
    """))
    fp.name = "setup.py"
    result = update_python_requires(fp, v(['2.7', '3.2']))
    assert result is not None  # make mypy happy
    assert "".join(result) == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>=2.7,!=3.0.*,!=3.1.*',
        )
    """)


def test_update_python_requires_multiline(fix_max_python_3_version):
    fix_max_python_3_version(2)
    fp = StringIO(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires=', '.join([
                '>=2.7',
                '!=3.0.*',
            ]),
        )
    """))
    fp.name = "setup.py"
    result = update_python_requires(fp, v(['2.7', '3.2']))
    assert result is not None
    assert "".join(result) == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires=', '.join([
                '>=2.7',
                '!=3.0.*',
                '!=3.1.*',
            ]),
        )
    """)


def test_update_python_requires_multiline_variations(fix_max_python_3_version):
    fix_max_python_3_version(2)
    fp = StringIO(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires=",".join([
                ">=2.7",
                "!=3.0.*",
            ]),
        )
    """))
    fp.name = "setup.py"
    result = update_python_requires(fp, v(['2.7', '3.2']))
    assert result is not None
    assert "".join(result) == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires=",".join([
                ">=2.7",
                "!=3.0.*",
                "!=3.1.*",
            ]),
        )
    """)


def test_update_python_requires_multiline_error(capsys):
    fp = StringIO(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires=', '.join([
                '>=2.7',
                '!=3.0.*']),
        )
    """))
    fp.name = "setup.py"
    result = update_python_requires(fp, v(['2.7', '3.2']))
    assert result == fp.getvalue().splitlines(True)
    assert_stderr(
        "Did not understand python_requires= formatting in setup() call",
        capsys,
    )


@pytest.mark.parametrize(['available', 'chosen'], [
    ({'python': '/usr/bin/python'}, 'python'),
    ({'python3': '/usr/bin/python3'}, 'python3'),
    ({'python': '/usr/bin/python', 'python3': '/usr/bin/python3'}, 'python3'),
    ({}, sys.executable),
])
def test_find_python(monkeypatch, available, chosen):
    monkeypatch.setattr(shutil, 'which', available.get)
    assert find_python() == chosen
