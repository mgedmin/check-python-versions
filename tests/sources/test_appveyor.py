import textwrap
from io import StringIO
from typing import List

import pytest

from check_python_versions.sources.appveyor import (
    appveyor_detect_py_version_pattern,
    appveyor_normalize_py_version,
    get_appveyor_yml_python_versions,
    update_appveyor_yml_python_versions,
)
from check_python_versions.versions import Version


def v(versions: List[str]) -> List[Version]:
    return [Version.from_string(v) for v in versions]


def test_get_appveyor_yml_python_versions(tmp_path):
    appveyor_yml = tmp_path / "appveyor.yml"
    appveyor_yml.write_text(textwrap.dedent("""\
        environment:
          matrix:
            - PYTHON: c:\\python27
            - PYTHON: c:\\python27-x64
            - PYTHON: c:\\python36
            - PYTHON: c:\\python36-x64
              UNRELATED: variable
    """))
    assert get_appveyor_yml_python_versions(appveyor_yml) == v([
        '2.7', '3.6',
    ])


def test_get_appveyor_yml_python_versions_forward_slashs(tmp_path):
    # Regr. test for https://github.com/mgedmin/check-python-versions/issues/12
    appveyor_yml = tmp_path / "appveyor.yml"
    appveyor_yml.write_text(textwrap.dedent("""\
        environment:
          matrix:
            - PYTHON: "C:/Python27"
            - PYTHON: "C:/Python34"
            - PYTHON: "C:/Python35"
            - PYTHON: "C:/Python36"
    """))
    assert get_appveyor_yml_python_versions(appveyor_yml) == v([
        '2.7', '3.4', '3.5', '3.6',
    ])


def test_get_appveyor_yml_python_versions_python_not_recognized(tmp_path):
    # Regr. test for https://github.com/mgedmin/check-python-versions/issues/12
    appveyor_yml = tmp_path / "appveyor.yml"
    appveyor_yml.write_text(textwrap.dedent("""\
        environment:
          matrix:
            - PYTHON: "C:/SomeCustomPythonNoVersionNumber"
            - PYTHON: "C:/Python36"
            - PYTHON: "C:/Python37"
            - PYTHON: "C:/Python38"
    """))
    assert get_appveyor_yml_python_versions(appveyor_yml) == v([
        '3.6', '3.7', '3.8',
    ])


def test_get_appveyor_yml_python_versions_using_toxenv(tmp_path):
    appveyor_yml = tmp_path / "appveyor.yml"
    appveyor_yml.write_text(textwrap.dedent("""\
        environment:
          matrix:
            - TOXENV: py27
            - TOXENV: py37
    """))
    assert get_appveyor_yml_python_versions(appveyor_yml) == v([
        '2.7', '3.7',
    ])


@pytest.mark.parametrize('s, expected', [
    ('37', '3.7'),
    ('c:\\python34', '3.4'),
    ('C:\\Python27\\', '2.7'),
    ('C:\\Python27-x64', '2.7'),
    ('C:\\PYTHON34-X64', '3.4'),
    ('C:\\Python38-x64\\python.exe', '3.8'),
    ('c:/python38', '3.8'),
    ('c:/python3', None),  # would it be useful to return '3'?  probably not
    ('c:/python310', '3.10'),
    ('unknown', None),
])
def test_appveyor_normalize_py_version(s, expected):
    expected = expected and Version.from_string(expected)
    assert appveyor_normalize_py_version(s) == expected


@pytest.mark.parametrize('s, expected', [
    ('37', '{}{}'),
    ('c:\\python34', 'c:\\python{}{}'),
    ('C:\\Python27\\', 'C:\\Python{}{}\\'),
    ('C:\\Python27-x64', 'C:\\Python{}{}-x64'),
    ('C:\\PYTHON34-X64', 'C:\\PYTHON{}{}-X64'),
    ('c:/python38', 'c:/python{}{}'),
    ('c:/python310', 'c:/python{}{}'),
    ('unknown', None),
])
def test_appveyor_detect_py_version_pattern(s, expected):
    assert appveyor_detect_py_version_pattern(s) == expected


def test_update_appveyor_yml_python_versions():
    appveyor_yml = StringIO(textwrap.dedent(r"""
        environment:
           matrix:
            - PYTHON: "c:\\python27"
            - PYTHON: "c:\\python36"
    """).lstrip('\n'))
    appveyor_yml.name = 'appveyor.yml'
    result = update_appveyor_yml_python_versions(appveyor_yml, v([
        '2.7', '3.7', '3.10',
    ]))
    assert result is not None
    assert ''.join(result) == textwrap.dedent(r"""
        environment:
           matrix:
            - PYTHON: "c:\\python27"
            - PYTHON: "c:\\python37"
            - PYTHON: "c:\\python310"
    """.lstrip('\n'))


def test_update_appveyor_yml_python_versions_multiple_of_each():
    appveyor_yml = StringIO(textwrap.dedent("""\
        environment:
          matrix:
            - PYTHON: c:\\python27
            - PYTHON: c:\\python27-x64
            - PYTHON: c:\\python36
            - PYTHON: c:\\python36-x64
    """))
    appveyor_yml.name = 'appveyor.yml'
    result = update_appveyor_yml_python_versions(appveyor_yml, v([
        '2.7', '3.7',
    ]))
    assert result is not None
    assert ''.join(result) == textwrap.dedent("""\
        environment:
          matrix:
            - PYTHON: c:\\python27
            - PYTHON: c:\\python27-x64
            - PYTHON: c:\\python37
            - PYTHON: c:\\python37-x64
    """)


def test_update_appveyor_yml_leave_unknown_python_versions_alone():
    appveyor_yml = StringIO(textwrap.dedent("""\
        environment:
          matrix:
            - PYTHON: c:\\python27
            - PYTHON: c:\\python36
            - PYTHON: c:\\custompython
    """))
    appveyor_yml.name = 'appveyor.yml'
    result = update_appveyor_yml_python_versions(appveyor_yml, v([
        '3.6', '3.7',
    ]))
    assert result is not None
    assert ''.join(result) == textwrap.dedent("""\
        environment:
          matrix:
            - PYTHON: c:\\python36
            - PYTHON: c:\\python37
            - PYTHON: c:\\custompython
    """)


def test_update_appveyor_yml_python_complicated_but_oneline():
    appveyor_yml = StringIO(textwrap.dedent("""\
        environment:
          matrix:
            - PYTHON: c:\\python27
            - PYTHON: c:\\python36
            - { PYTHON: c:\\python27, EXTRA_FEATURE: 1 }
            - { PYTHON: c:\\python36, EXTRA_FEATURE: 1 }
            - { PYTHON: c:\\custom, EXTRA_FEATURE: 1 }
            - { NOT_PYTHON_AT_ALL: 1 }
            - { TOO: 1,
                COMPLICATED: 2 }
    """))
    appveyor_yml.name = 'appveyor.yml'
    result = update_appveyor_yml_python_versions(appveyor_yml, v(['3.6']))
    assert result is not None
    assert ''.join(result) == textwrap.dedent("""\
        environment:
          matrix:
            - PYTHON: c:\\python36
            - { PYTHON: c:\\python36, EXTRA_FEATURE: 1 }
            - { PYTHON: c:\\custom, EXTRA_FEATURE: 1 }
            - { NOT_PYTHON_AT_ALL: 1 }
            - { TOO: 1,
                COMPLICATED: 2 }
    """)


def test_update_appveyor_yml_python_no_understanding(capsys):
    appveyor_yml = StringIO(textwrap.dedent("""\
        environment:
          matrix:
            - FOO: 1
            - BAR: 2
    """))
    appveyor_yml.name = 'appveyor.yml'
    result = update_appveyor_yml_python_versions(appveyor_yml, v(['3.6']))
    assert result is not None
    assert ''.join(result) == textwrap.dedent("""\
        environment:
          matrix:
            - FOO: 1
            - BAR: 2
    """)
    assert (
        "Did not recognize any PYTHON environments in appveyor.yml"
        in capsys.readouterr().err
    )
