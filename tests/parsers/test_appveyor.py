import textwrap
from io import StringIO

import pytest

try:
    import yaml
except ImportError:
    yaml = None

from check_python_versions.parsers.appveyor import (
    appveyor_detect_py_version_pattern,
    appveyor_normalize_py_version,
    get_appveyor_yml_python_versions,
    update_appveyor_yml_python_versions,
)


needs_pyyaml = pytest.mark.skipIf(yaml is None, "PyYAML not installed")


@needs_pyyaml
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
    assert get_appveyor_yml_python_versions(appveyor_yml) == [
        '2.7', '3.6',
    ]


@needs_pyyaml
def test_get_appveyor_yml_python_versions_using_toxenv(tmp_path):
    appveyor_yml = tmp_path / "appveyor.yml"
    appveyor_yml.write_text(textwrap.dedent("""\
        environment:
          matrix:
            - TOXENV: py27
            - TOXENV: py37
    """))
    assert get_appveyor_yml_python_versions(appveyor_yml) == [
        '2.7', '3.7',
    ]


@pytest.mark.parametrize('s, expected', [
    ('37', '3.7'),
    ('c:\\python34', '3.4'),
    ('C:\\Python27\\', '2.7'),
    ('C:\\Python27-x64', '2.7'),
    ('C:\\PYTHON34-X64', '3.4'),
])
def test_appveyor_normalize_py_version(s, expected):
    assert appveyor_normalize_py_version(s) == expected


@pytest.mark.parametrize('s, expected', [
    ('37', '{}{}'),
    ('c:\\python34', 'c:\\python{}{}'),
    ('C:\\Python27\\', 'C:\\Python{}{}\\'),
    ('C:\\Python27-x64', 'C:\\Python{}{}-x64'),
    ('C:\\PYTHON34-X64', 'C:\\PYTHON{}{}-X64'),
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
    result = update_appveyor_yml_python_versions(appveyor_yml, ['2.7', '3.7'])
    assert ''.join(result) == textwrap.dedent(r"""
        environment:
           matrix:
            - PYTHON: "c:\\python27"
            - PYTHON: "c:\\python37"
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
    result = update_appveyor_yml_python_versions(appveyor_yml, ['2.7', '3.7'])
    assert ''.join(result) == textwrap.dedent("""\
        environment:
          matrix:
            - PYTHON: c:\\python27
            - PYTHON: c:\\python27-x64
            - PYTHON: c:\\python37
            - PYTHON: c:\\python37-x64
    """)


def test_update_appveyor_yml_python_complicated_but_oneline():
    appveyor_yml = StringIO(textwrap.dedent("""\
        environment:
          matrix:
            - PYTHON: c:\\python27
            - PYTHON: c:\\python36
            - { PYTHON: c:\\python27, EXTRA_FEATURE: 1 }
            - { PYTHON: c:\\python36, EXTRA_FEATURE: 1 }
    """))
    result = update_appveyor_yml_python_versions(appveyor_yml, ['3.6'])
    assert ''.join(result) == textwrap.dedent("""\
        environment:
          matrix:
            - PYTHON: c:\\python36
            - { PYTHON: c:\\python36, EXTRA_FEATURE: 1 }
    """)


def test_update_appveyor_yml_python_no_understanding(capsys):
    appveyor_yml = StringIO(textwrap.dedent("""\
        environment:
          matrix:
            - FOO: 1
            - BAR: 2
    """))
    appveyor_yml.name = 'appveyor.yml'
    result = update_appveyor_yml_python_versions(appveyor_yml, ['3.6'])
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
