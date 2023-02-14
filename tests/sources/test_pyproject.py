import os
import textwrap
from typing import List, cast

import pytest
from tomlkit.toml_document import TOMLDocument

from check_python_versions.parsers.poetry_version_spec import (
    parse_poetry_version_constraint,
)
from check_python_versions.sources.pyproject import (
    get_python_requires,
    get_supported_python_versions,
    traverse,
    update_python_requires,
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
    err = stderr(capsys, tmp_path).splitlines()
    assert message in err


def test_traverse():
    d = cast(TOMLDocument, {'a': {'b': 'c'}})
    assert traverse(d, 'a.b') == 'c'
    assert traverse(d, 'a.b.c') is None
    assert traverse(d, 'a.c') is None


def test_get_supported_python_versions_setuptools(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [project]
        name = 'foo'
        classifiers = [
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
        ]

        [build-system]
        requires = ["setuptools", "setuptools-scm"]
        build-backend = "setuptools.build_meta"
    """))
    assert get_supported_python_versions(pyproject_toml) == v(['3.9', '3.10'])


def test_get_supported_python_versions_flit(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [tool.flit.metadata]
        name = 'foo'
        classifiers = [
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
        ]
    """))
    assert get_supported_python_versions(pyproject_toml) == v(['3.9', '3.10'])


def test_get_supported_python_versions_poetry(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [tool.poetry]
        name = 'foo'
        classifiers = [
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
        ]
    """))
    assert get_supported_python_versions(pyproject_toml) == v(['3.9', '3.10'])


def test_get_supported_python_versions_no_metadata_table(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [tool.unrelated]
        config = 42
    """))
    assert get_supported_python_versions(pyproject_toml) is None


def test_get_supported_python_versions_dynamic_classifiers(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [project]
        dynamic = ["classifiers"]

        [build-system]
        requires = ["setuptools", "setuptools-scm"]
        build-backend = "setuptools.build_meta"
    """))
    assert get_supported_python_versions(pyproject_toml) is None


def test_get_supported_python_versions_bad_data_in_list(tmp_path, capsys):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [project]
        name = 'foo'
        classifiers = [
            'Programming Language :: Python :: 3.9',
            'Programming Language :: Python :: 3.10',
            42,
        ]

        [build-system]
        requires = ["setuptools", "setuptools-scm"]
        build-backend = "setuptools.build_meta"
    """))
    assert get_supported_python_versions(pyproject_toml) == []
    assert_stderr(
        "The value specified for project.classifiers in /tmp/pyproject.toml"
        " is not an array of strings",
        capsys, tmp_path,
    )


def test_get_supported_python_versions_bad_data_type(tmp_path, capsys):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [project]
        name = 'foo'
        classifiers = {}

        [build-system]
        requires = ["setuptools", "setuptools-scm"]
        build-backend = "setuptools.build_meta"
    """))
    assert get_supported_python_versions(pyproject_toml) == []
    assert_stderr(
        "The value specified for project.classifiers in /tmp/pyproject.toml"
        " is not an array",
        capsys, tmp_path,
    )


def test_update_supported_python_versions_setuptools(tmp_path, capsys):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [project]
            name='foo'
            # comments are preserved btw
            classifiers=[
                'Programming Language :: Python :: 3.6',
            ]
        [build-system]
            requires = ["setuptools", "setuptools-scm"]
            build-backend = "setuptools.build_meta"
    """))
    result = update_supported_python_versions(pyproject_toml,
                                              v(['3.7', '3.8']))
    assert result is not None  # make mypy happy
    # I would love to preserve the existing quote style, but it's too hard
    assert "".join(result) == textwrap.dedent("""\
        [project]
            name='foo'
            # comments are preserved btw
            classifiers=[
                "Programming Language :: Python :: 3.7",
                "Programming Language :: Python :: 3.8",
            ]
        [build-system]
            requires = ["setuptools", "setuptools-scm"]
            build-backend = "setuptools.build_meta"
    """)


def test_update_supported_python_versions_setuptools_dynamic(tmp_path, capsys):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [project]
        name = 'foo'
        dynamic = ["classifiers"]

        [build-system]
        requires = ["setuptools", "setuptools-scm"]
        build-backend = "setuptools.build_meta"
    """))
    result = update_supported_python_versions(pyproject_toml,
                                              v(['3.7', '3.8']))
    assert result is None


def test_get_python_requires_setuptools(tmp_path, fix_max_python_3_version):
    fix_max_python_3_version(9)
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [project]
        name = 'foo'
        requires-python = ">= 3.8"

        [build-system]
        requires = ["setuptools", "setuptools-scm"]
        build-backend = "setuptools.build_meta"
    """))
    assert get_python_requires(pyproject_toml) == v(['3.8', '3.9'])


def test_get_python_requires_flit(tmp_path, fix_max_python_3_version):
    fix_max_python_3_version(9)
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [tool.flit.metadata]
        name = 'foo'
        requires-python = ">= 3.8"
    """))
    assert get_python_requires(pyproject_toml) == v(['3.8', '3.9'])


def test_get_python_requires_poetry(tmp_path, fix_max_python_3_version):
    fix_max_python_3_version(9)
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [tool.poetry.dependencies]
        python = "^3.8"
    """))
    assert get_python_requires(pyproject_toml) == v(['3.8', '3.9'])


def test_get_python_requires_not_specified(tmp_path, capsys):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [project]
        name = 'foo'
    """))
    assert get_python_requires(pyproject_toml) is None
    assert capsys.readouterr().err == ""


def test_get_python_requires_badly_specified(tmp_path, capsys):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [project]
        name = 'foo'
        requires-python = []
    """))
    assert get_python_requires(pyproject_toml) is None
    assert_stderr(
        "The value specified for project.requires-python in"
        " /tmp/pyproject.toml is not a string",
        capsys, tmp_path,
    )


def test_get_python_requires_bad_format(tmp_path, capsys):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [project]
        name = 'foo'
        requires-python = "something recentish"
    """))
    assert get_python_requires(pyproject_toml) is None
    assert_stderr(
        "Bad project.requires-python specifier in /tmp/pyproject.toml:"
        " something recentish",
        capsys, tmp_path,
    )


def test_update_python_requires_setuptools(tmp_path, fix_max_python_3_version):
    fix_max_python_3_version(9)
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [project]
        name = 'foo'
        # comments are preserved btw
        requires-python = ">= 3.8"

        [build-system]
        requires = ["setuptools", "setuptools-scm"]
        build-backend = "setuptools.build_meta"
    """))
    result = update_python_requires(pyproject_toml, v(['3.9']))
    assert result is not None  # make mypy happy
    assert "".join(result) == textwrap.dedent("""\
        [project]
        name = 'foo'
        # comments are preserved btw
        requires-python = ">= 3.9"

        [build-system]
        requires = ["setuptools", "setuptools-scm"]
        build-backend = "setuptools.build_meta"
    """)


@pytest.mark.parametrize("previous, versions, expected", [
    ('>=3.8', '3.8', '3.8.*'),
    ('>=3.8', '3.8 3.9', '>=3.8, <3.10'),
    ('>=3.8', '3.8 3.9 3.10', '>=3.8'),
    ('^3.8', '3.8', '~3.8'),
    ('^3.8', '3.8 3.9', '>=3.8, <3.10'),
    ('^3.8', '3.8 3.9 3.10', '^3.8'),
])
def test_update_python_requires_poetry(
    tmp_path, fix_max_python_3_version, previous, versions, expected
):
    fix_max_python_3_version(10)
    # double-check that the test data is correct
    assert parse_poetry_version_constraint(expected) == v(versions.split())
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent(f"""\
        [tool.poetry.dependencies]
        python = "{previous}"
    """))
    result = update_python_requires(pyproject_toml, v(versions.split()))
    assert result is not None  # make mypy happy
    assert "".join(result) == textwrap.dedent(f"""\
        [tool.poetry.dependencies]
        python = "{expected}"
    """)


def test_update_python_requires_not_specified(tmp_path):
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(textwrap.dedent("""\
        [project]
        name = 'foo'
    """))
    result = update_python_requires(pyproject_toml, v(['3.9']))
    assert result is None
