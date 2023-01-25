import textwrap
from io import StringIO
from tomlkit import dumps
from typing import List

from check_python_versions.sources.pyproject import (
    get_python_requires,
    get_supported_python_versions,
    is_flit_toml,
    is_poetry_toml,
    is_setuptools_toml,
    load_toml,
    update_python_requires,
)
from check_python_versions.utils import (
    FileLines,
    FileOrFilename,
)
from check_python_versions.versions import Version


def v(versions: List[str]) -> List[Version]:
    return [Version.from_string(v) for v in versions]


def get_toml_content(
    filename: FileOrFilename
) -> FileLines:
    """Utility method to see if TOML library keeps style and comments."""
    table = load_toml(filename)
    return dumps(table).split('\n')


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
    assert get_supported_python_versions(str(filename)) == \
           v(['2.7', '3.6', '3.10'])


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

    assert get_toml_content(str(filename)) == \
           ['[tool.poetry]',
            '    name=\'foo\'',
            '    # toml comment',
            '    classifiers=[',
            '         \'Programming Language :: Python :: 2.7\',',
            '        \'Programming Language :: Python :: 3.6\',',
            '        \'Programming Language :: Python :: 3.10\',',
            '    ]',
            '']


def test_update_supported_python_versions_not_a_list(tmp_path, capsys):
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
        "The value specified for classifiers is not an array"
        in capsys.readouterr().err
    )


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
    assert capsys.readouterr().err.strip() == \
           'The value specified for python dependency is not a string'


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
        'The value specified for python dependency is not a string'
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


def test_update_python_requires_file_object(fix_max_python_3_version):
    fix_max_python_3_version(7)
    fp = StringIO(textwrap.dedent("""\
        [tool.poetry]
            name='foo'
            [tool.poetry.dependencies]
                python = ">=3.4"
    """))
    fp.name = "pyproject.toml"
    result = update_python_requires(fp, v(['3.5', '3.6', '3.7']))
    assert result is not None
    assert "\n".join(result) == textwrap.dedent("""\
        [tool.poetry]
            name='foo'
            [tool.poetry.dependencies]
                python = ">=3.5"
    """)


def test_update_python_requires_when_missing(capsys):
    fp = StringIO(textwrap.dedent("""\
        [tool.poetry]
            name='foo'
    """))
    fp.name = "pyproject.toml"
    result = update_python_requires(fp, v(['3.5', '3.6', '3.7']))
    assert result is None
    assert capsys.readouterr().err == ""


def test_update_python_requires_preserves_style(fix_max_python_3_version):
    fix_max_python_3_version(2)
    fp = StringIO(textwrap.dedent("""\
        [tool.poetry]
            name='foo'
            [tool.poetry.dependencies]
                python = ">=2.7,!=3.0.*"
    """))
    fp.name = "pyproject.toml"
    result = update_python_requires(fp, v(['2.7', '3.2']))
    assert "\n".join(result) == textwrap.dedent("""\
        [tool.poetry]
            name='foo'
            [tool.poetry.dependencies]
                python = ">=2.7,!=3.0.*,!=3.1.*"
    """)


def test_update_python_requires_multiline_error(capsys):
    fp = StringIO(textwrap.dedent("""\
        [tool.poetry]
            name='foo'
            [tool.poetry.dependencies]
                python = '>=2.7, !=3.0.*'
    """))
    fp.name = "pyproject.toml"
    result = update_python_requires(fp, v(['2.7', '3.2']))
    assert result == ['[tool.poetry]',
                      "    name='foo'",
                      '    [tool.poetry.dependencies]',
                      '        python = ">=2.7, !=3.0.*, !=3.1.*, !=3.3.*,'
                      ' !=3.4.*, !=3.5.*, !=3.6.*, !=3.7.*, '
                      '!=3.8.*, !=3.9.*, !=3.10.*, !=3.11.*"',
                      '']


def test_poetry_toml_from_tools(tmp_path):
    filename = tmp_path / "pyproject.toml"
    filename.write_text(textwrap.dedent("""\
        [tool.poetry]
            name='foo'
    """))
    _table = load_toml(str(filename))
    assert is_poetry_toml(_table)
    assert not is_setuptools_toml(_table)
    assert not is_flit_toml(_table)


def test_poetry_toml_from_build_backend(tmp_path):
    filename = tmp_path / "pyproject.toml"
    filename.write_text(textwrap.dedent("""\
        [build-system]
            build-backend = "poetry.core.masonry.api"
    """))
    _table = load_toml(str(filename))
    assert is_poetry_toml(_table)
    assert not is_setuptools_toml(_table)
    assert not is_flit_toml(_table)


def test_poetry_toml_from_build_requires(tmp_path):
    filename = tmp_path / "pyproject.toml"
    filename.write_text(textwrap.dedent("""\
        [build-system]
            requires = ["poetry-core>=1.0.0"]
    """))
    _table = load_toml(str(filename))
    assert is_poetry_toml(_table)
    assert not is_setuptools_toml(_table)
    assert not is_flit_toml(_table)
