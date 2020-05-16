import shutil
import sys
import textwrap
from io import StringIO

import pytest

from check_python_versions.sources.setup_py import (
    compute_python_requires,
    find_python,
    get_python_requires,
    get_setup_py_keyword,
    get_supported_python_versions,
    get_versions_from_classifiers,
    parse_python_requires,
    update_classifiers,
    update_python_requires,
    update_setup_py_keyword,
    update_supported_python_versions,
)


def test_get_supported_python_versions(tmp_path):
    filename = tmp_path / "setup.py"
    filename.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    assert get_supported_python_versions(filename) == ['2.7', '3.6']


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
    assert get_supported_python_versions(filename) == ['2.7', '3.7']


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
    assert (
        "The value passed to setup(classifiers=...) is not a list"
        in capsys.readouterr().err
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


def test_get_versions_from_classifiers():
    assert get_versions_from_classifiers([
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ]) == ['2.7', '3.6', '3.7', 'PyPy']


def test_get_versions_from_classifiers_major_only():
    assert get_versions_from_classifiers([
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ]) == ['2', '3']


def test_get_versions_from_classifiers_with_only_suffix():
    assert get_versions_from_classifiers([
        'Programming Language :: Python :: 2 :: Only',
    ]) == ['2']


def test_get_versions_from_classifiers_with_trailing_whitespace():
    # I was surprised too that this is allowed!
    assert get_versions_from_classifiers([
        'Programming Language :: Python :: 3.6 ',
    ]) == ['3.6']


def test_update_classifiers():
    assert update_classifiers([
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Typing :: Typed',
    ], ['2.7', '3.7']) == [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Typing :: Typed',
    ]


def test_update_classifiers_drop_major():
    assert update_classifiers([
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Typing :: Typed',
    ], ['3.6', '3.7']) == [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Typing :: Typed',
    ]


def test_update_classifiers_no_major():
    assert update_classifiers([
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Typing :: Typed',
    ], ['2.7', '3.7']) == [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Typing :: Typed',
    ]


def test_update_classifiers_none_were_present():
    assert update_classifiers([
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
    ], ['2.7', '3.7']) == [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.7',
    ]


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
    assert update_supported_python_versions(filename, ['3.7', '3.8']) is None
    assert (
        'Non-literal classifiers= passed to setup()'
        in capsys.readouterr().err
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
    assert update_supported_python_versions(filename, ['3.7', '3.8']) is None
    assert (
        'The value passed to setup(classifiers=...) is not a list'
        in capsys.readouterr().err
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
    assert get_python_requires(setup_py) == ['3.6', '3.7']


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
    assert (
        'The value passed to setup(python_requires=...) is not a string'
        in capsys.readouterr().err
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
    assert 'Could not parse' in capsys.readouterr().err


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
    result = update_python_requires(filename, ['3.5', '3.6', '3.7'])
    assert "".join(result) == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>=3.5',
        )
    """)


def test_update_python_requires_file_object(fix_max_python_3_version):
    fix_max_python_3_version(7)
    fp = StringIO(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>= 3.4',
        )
    """))
    fp.name = "setup.py"
    result = update_python_requires(fp, ['3.5', '3.6', '3.7'])
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
    result = update_python_requires(fp, ['3.5', '3.6', '3.7'])
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
    result = update_python_requires(fp, ['2.7', '3.2'])
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
    result = update_python_requires(fp, ['2.7', '3.2'])
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
    result = update_python_requires(fp, ['2.7', '3.2'])
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
    result = update_python_requires(fp, ['2.7', '3.2'])
    assert result == fp.getvalue().splitlines(True)
    assert (
        "Did not understand python_requires= formatting in setup() call"
        in capsys.readouterr().err
    )


@pytest.mark.parametrize('constraint, result', [
    ('~= 2.7', ['2.7']),
    ('~= 2.7.12', ['2.7']),
])
def test_parse_python_requires_approximately(constraint, result):
    assert parse_python_requires(constraint) == result


def test_parse_python_requires_approximately_not_enough_dots(capsys):
    assert parse_python_requires('~= 2') is None
    assert (
        'Bad python_requires specifier: ~= 2'
        ' (~= requires a version with at least one dot)'
        in capsys.readouterr().err
    )


@pytest.mark.parametrize('constraint, result', [
    ('== 2.7', ['2.7']),
    ('== 2.7.*', ['2.7']),
    ('== 2.7.12', ['2.7']),
    ('== 2.*, >= 2.6', ['2.6', '2.7']),
    ('== 3.0', ['3.0']),
    ('== 3', ['3.0']),
])
def test_parse_python_requires_matching_version(constraint, result):
    assert parse_python_requires(constraint) == result


def test_parse_python_requires_greater_than(fix_max_python_3_version):
    fix_max_python_3_version(8)
    assert parse_python_requires('>= 3.6') == ['3.6', '3.7', '3.8']


@pytest.mark.parametrize('constraint, result', [
    ('>= 2.7, != 3.*', ['2.7']),
    ('>= 2.7.12, != 3.*', ['2.7']),
    ('>= 2.7, != 3.0.*, != 3.1.*', ['2.7', '3.2', '3.3']),
    # != 3.2 means we reject 3.2.0 but still accept any other 3.2.x
    ('>= 2.7, != 3.2', ['2.7', '3.0', '3.1', '3.2', '3.3']),
    ('>= 2.7, != 3.2.1', ['2.7', '3.0', '3.1', '3.2', '3.3']),
    ('>= 2.7, <= 3', ['2.7', '3.0']),
    ('>= 2.7, <= 3.2', ['2.7', '3.0', '3.1', '3.2']),
    ('>= 2.7, <= 3.2.1', ['2.7', '3.0', '3.1', '3.2']),
    ('>= 3', ['3.0', '3.1', '3.2', '3.3']),
])
def test_parse_python_requires_greater_than_with_exceptions(
    fix_max_python_3_version, constraint, result
):
    fix_max_python_3_version(3)
    assert parse_python_requires(constraint) == result


def test_parse_python_requires_multiple_greater_than(fix_max_python_3_version):
    fix_max_python_3_version(7)
    assert parse_python_requires('>= 2.7, >= 3.6') == ['3.6', '3.7']


@pytest.mark.parametrize('constraint, result', [
    ('> 2, < 3.1', ['3.0']),
    ('> 2.6, < 3', ['2.7']),
    ('> 2.7.12, < 3', ['2.7']),
    ('> 2.7.12, < 3.0', ['2.7']),
    ('> 2.7.12, < 3.1', ['2.7', '3.0']),
    ('> 2.7.12, < 3.0.1', ['2.7', '3.0']),
])
def test_parse_python_requires_exclusive_ordering(constraint, result):
    assert parse_python_requires(constraint) == result


@pytest.mark.parametrize('constraint, result', [
    ('=== 2.7', ['2.7']),
    ('=== 2.7.12', ['2.7']),
    ('=== 3', []),
])
def test_parse_python_requires_arbitrary_version(constraint, result):
    assert parse_python_requires(constraint) == result


@pytest.mark.parametrize('op', ['~=', '>=', '<=', '>', '<', '==='])
def test_parse_python_requires_unexpected_dot_star(fix_max_python_3_version,
                                                   capsys, op):
    fix_max_python_3_version(7)
    assert parse_python_requires(f'{op} 3.6.*') is None
    assert (
        f'Bad python_requires specifier: {op} 3.6.* ({op} does not allow a .*)'
        in capsys.readouterr().err
    )


@pytest.mark.parametrize('specifier', [
    '%= 42',
    '== nobody.knows',
    '!= *.*.*',
    'xyzzy',
])
def test_parse_python_requires_syntax_errors(capsys, specifier):
    assert parse_python_requires(specifier) is None
    assert (
        f'Bad python_requires specifier: {specifier}'
        in capsys.readouterr().err
    )


@pytest.mark.parametrize('versions, expected', [
    (['2.7'], '==2.7.*'),
    (['3.6', '3.7'], '>=3.6'),
    (['2.7', '3.4', '3.5', '3.6', '3.7'],
     '>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*'),
])
def test_compute_python_requires(versions, expected, fix_max_python_3_version):
    fix_max_python_3_version(7)
    result = compute_python_requires(versions)
    assert result == expected
    assert parse_python_requires(result) == versions


@pytest.mark.parametrize(['available', 'chosen'], [
    ({'python': '/usr/bin/python'}, 'python'),
    ({'python3': '/usr/bin/python3'}, 'python3'),
    ({'python': '/usr/bin/python', 'python3': '/usr/bin/python3'}, 'python3'),
    ({}, sys.executable),
])
def test_find_python(monkeypatch, available, chosen):
    monkeypatch.setattr(shutil, 'which', available.get)
    assert find_python() == chosen
