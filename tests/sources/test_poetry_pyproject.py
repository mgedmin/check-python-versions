import textwrap
from io import StringIO
from typing import List

import pytest

from check_python_versions.sources.poetry_pyproject import (
    get_python_requires,
    get_supported_python_versions,
    get_toml_content,
    update_python_requires,
    update_supported_python_versions,
)
from check_python_versions.versions import Version


def v(versions: List[str]) -> List[Version]:
    return [Version.from_string(v) for v in versions]


def test_get_supported_python_versions(tmp_path):
    filename = tmp_path / "pyproject.toml"
    filename.write_text(textwrap.dedent("""\
        [tool.poetry]
            name='foo'
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
                'Programming Language :: Python :: 3.10',
            ]
    """))
    assert get_supported_python_versions(str(filename)) == v(['2.7', '3.6', '3.10'])


def test_get_supported_python_versions_keep_comments(tmp_path):
    filename = tmp_path / "pyproject.toml"
    filename.write_text(textwrap.dedent("""\
        [tool.poetry]
            name='foo'
            # toml comment
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
                'Programming Language :: Python :: 3.10',
            ]
    """))

    assert get_toml_content(str(filename)) == ['[tool.poetry]',
                                               '    name=\'foo\'',
                                               '    # toml comment',
                                               '    classifiers=[',
                                               '        \'Programming Language :: Python :: 2.7\',',
                                               '        \'Programming Language :: Python :: 3.6\',',
                                               '        \'Programming Language :: Python :: 3.10\',',
                                               '    ]',
                                               '']


def test_get_supported_python_versions_string(tmp_path, capsys):
    filename = tmp_path / "pyproject.toml"
    filename.write_text(textwrap.dedent("""\
        [tool.poetry]
            name='foo'
            classifiers='''
                Programming Language :: Python :: 2.7
                Programming Language :: Python :: 3.6
            '''
    """))
    assert get_supported_python_versions(str(filename)) == []
    assert (
        "The value passed to classifiers is not a list"
        in capsys.readouterr().err
    )


# def test_update_supported_python_versions_not_matching(tmp_path, capsys):
#     filename = tmp_path / "pyproject.toml"
#     filename.write_text(textwrap.dedent("""\
#         [tool.poetry]
#             name='foo'
#             classifiers=[
#                 'Programming Language :: Python :: 2.7',
#                 'Programming Language :: Python :: 3.6',
#             ]
#     """))
#     _what = update_supported_python_versions(str(filename),
#                                             v(['3.7', '3.8']))
#     assert _what is None
#     assert (
#         'The value passed to classifiers is not a list'
#         in capsys.readouterr().err
#     )


def test_get_python_requires(tmp_path, fix_max_python_3_version):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [tool.poetry]
            name='foo'
            [tool.poetry.dependencies]
                python = ">=3.6"
    """))
    fix_max_python_3_version(7)
    assert get_python_requires(str(pyproject_toml)) == v(['3.6', '3.7'])
    fix_max_python_3_version(10)
    assert get_python_requires(str(pyproject_toml)) == v([
        '3.6', '3.7', '3.8', '3.9', '3.10',
    ])


def test_get_python_requires_not_specified(tmp_path, capsys):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [tool.poetry]
            name='foo'
    """))
    assert get_python_requires(str(pyproject_toml)) is None
    assert capsys.readouterr().err.strip() == 'The value passed to python dependency is not a string'


def test_get_python_requires_not_a_string(tmp_path, capsys):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [tool.poetry]
            name='foo'
            [tool.poetry.dependencies]
                python = [">=3.6"]
    """))
    assert get_python_requires(str(pyproject_toml)) is None
    assert (
        'The value passed to python dependency is not a string'
        in capsys.readouterr().err
    )


def test_update_python_requires(tmp_path, fix_max_python_3_version):
    fix_max_python_3_version(7)
    filename = tmp_path / "pyproject.toml"
    filename.write_text(textwrap.dedent("""\
        [tool.poetry]
            name='foo'
            [tool.poetry.dependencies]
                python = ">=3.4"
    """))
    result = update_python_requires(str(filename), v(['3.5', '3.6', '3.7']))
    assert result is not None
    assert "\n".join(result) == textwrap.dedent("""\
        [tool.poetry]
            name='foo'
            [tool.poetry.dependencies]
                python = ">=3.5"
    """)


# def test_update_python_requires_file_object(fix_max_python_3_version):
#     fix_max_python_3_version(7)
#     fp = StringIO(textwrap.dedent("""\
#         [tool.poetry]
#             name='foo'
#             [tool.poetry.dependencies]
#                 python = ">=3.4"
#     """))
#     fp.name = "pyproject.toml"
#     result = update_python_requires(fp, v(['3.5', '3.6', '3.7']))
#     assert result is not None
#     assert "".join(result) == textwrap.dedent("""\
#         [tool.poetry]
#             name='foo'
#             [tool.poetry.dependencies]
#                 python = ">=3.5"
#     """)


def test_update_python_requires_when_missing(capsys):
    fp = StringIO(textwrap.dedent("""\
        [tool.poetry]
            name='foo'
    """))
    fp.name = "pyproject.toml"
    result = update_python_requires(fp, v(['3.5', '3.6', '3.7']))
    assert result is None
    assert capsys.readouterr().err == ""


# def test_update_python_requires_preserves_style(fix_max_python_3_version):
#     fix_max_python_3_version(2)
#     fp = StringIO(textwrap.dedent("""\
#         [tool.poetry]
#             name='foo'
#             [tool.poetry.dependencies]
#                 python = ">=2.7,!=3.0.*"
#     """))
#     fp.name = "pyproject.toml"
#     result = update_python_requires(fp, v(['2.7', '3.2']))
#     assert "".join(result) == textwrap.dedent("""\
#         [tool.poetry]
#             name='foo'
#             [tool.poetry.dependencies]
#                 python = ">=2.7,!=3.0.*,!=3.1.*"
#     """)

#
# def test_update_python_requires_multiline(fix_max_python_3_version):
#     fix_max_python_3_version(2)
#     fp = StringIO(textwrap.dedent("""\
#         [tool.poetry]
#             name='foo'
#             [tool.poetry.dependencies]
#                 python = ', '.join([
#                 '>=2.7',
#                 '!=3.0.*',
#             ])
#     """))
#     fp.name = "pyproject.toml"
#     result = update_python_requires(fp, v(['2.7', '3.2']))
#     assert result is not None
#     assert "".join(result) == textwrap.dedent("""\
#         [tool.poetry]
#             name='foo'
#             [tool.poetry.dependencies]
#                 python = ', '.join([
#                 '>=2.7',
#                 '!=3.0.*',
#                 '!=3.1.*',
#             ])
#     """)


# def test_update_python_requires_multiline_variations(fix_max_python_3_version):
#     fix_max_python_3_version(2)
#     fp = StringIO(textwrap.dedent("""\
#         [tool.poetry]
#             name='foo'
#             [tool.poetry.dependencies]
#                 python = ",".join([
#                 ">=2.7",
#                 "!=3.0.*",
#             ])
#     """))
#     fp.name = "pyproject.toml"
#     result = update_python_requires(fp, v(['2.7', '3.2']))
#     assert result is not None
#     assert "".join(result) == textwrap.dedent("""\
#         [tool.poetry]
#             name='foo'
#             [tool.poetry.dependencies]
#                 python = ",".join([
#                 ">=2.7",
#                 "!=3.0.*",
#                 "!=3.1.*",
#             ])
#     """)


# def test_update_python_requires_multiline_error(capsys):
#     fp = StringIO(textwrap.dedent("""\
#         [tool.poetry]
#             name='foo'
#             [tool.poetry.dependencies]
#                 python = '>=2.7, !=3.0.*'
#     """))
#     fp.name = "pyproject.toml"
#     result = update_python_requires(fp, v(['2.7', '3.2']))
#     assert result == fp.getvalue().splitlines(True)
#     assert (
#         "Did not understand python_requires formatting in python dependency"
#         in capsys.readouterr().err
#     )
