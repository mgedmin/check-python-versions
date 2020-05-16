"""
Support for Appveyor.

Appveyor is a hosted Continuous Integration solution that can be configured
by dropping a file named ``appveyor.yml`` into your source repository.

Appveyor can be configured through a web form as well, but
check-python-manifest does not support checking that.

The aforementioned web form can specify an alternative filename, but
check-python-manifest does not support checking that.

Appveyor does not directly support specifying Python interpreter versions,
so most projects that test multiple Python versions do so by specifing the
desired Python version in an environment variable.

check-python-versions assumes this variable is called PYTHON and has either
a Python version number, or the path to a Python installation
("C:\\PythonX.Y").

Alternatively, check-python-version looks for TOXENV, which lists names
of Tox environments (pyXY).
"""

import ast
from io import StringIO
from typing import Optional, Set, cast

import yaml

from .tox import parse_envlist, tox_env_to_py_version
from .travis import update_yaml_list
from ..utils import FileLines, FileOrFilename, open_file, warn
from ..versions import SortedVersionList, Version, VersionList


APPVEYOR_YML = 'appveyor.yml'


def get_appveyor_yml_python_versions(
    filename: FileOrFilename = APPVEYOR_YML,
) -> SortedVersionList:
    """Extract supported Python versions from appveyor.yml."""

    with open_file(filename) as fp:
        conf = yaml.safe_load(fp)
    # There's more than one way of doing this, I'm setting %PYTHON% to
    # the directory that has a Python interpreter (C:\PythonXY)
    versions = []
    for env in conf['environment']['matrix']:
        for var, value in env.items():
            if var.lower() == 'python':
                versions.append(appveyor_normalize_py_version(value))
            elif var == 'TOXENV':
                toxenvs = parse_envlist(value)
                versions.extend(
                    tox_env_to_py_version(e)
                    for e in toxenvs if e.startswith('py'))
    # The cast() is a workaround for https://github.com/python/mypy/issues/8526
    return sorted(cast(Set[str], set(versions) - {None}))


def appveyor_normalize_py_version(ver: str) -> Optional[Version]:
    """Determine Python version from PYTHON environment variable."""
    ver = str(ver).lower().replace('\\', '/')
    if ver.startswith('c:/python'):
        ver = ver[len('c:/python'):]
    if ver.endswith('/python.exe'):
        ver = ver[:-len('/python.exe')]
    elif ver.endswith('/'):
        ver = ver[:-1]
    if ver.endswith('-x64'):
        ver = ver[:-len('-x64')]
    if len(ver) >= 2 and ver[:2].isdigit():
        return f'{ver[0]}.{ver[1:]}'
    else:
        return None


def appveyor_detect_py_version_pattern(ver: str) -> Optional[str]:
    """Determine the format of the PYTHON environment variable.

    Returns a format string suitable for formatting with placeholders
    for major and minor version numbers.
    """
    ver = str(ver)
    pattern = '{}'
    for prefix in 'c:\\python', 'c:/python':
        if ver.lower().startswith(prefix):
            pos = len(prefix)
            prefix, ver = ver[:pos], ver[pos:]
            pattern = pattern.format(f'{prefix}{{}}')
            break
    if ver.endswith('\\'):
        ver = ver[:-1]
        pattern = pattern.format('{}\\')
    if ver.lower().endswith('-x64'):
        pos = -len('-x64')
        ver, suffix = ver[:pos], ver[pos:]
        pattern = pattern.format(f'{{}}{suffix}')
    if len(ver) >= 2 and ver[:2].isdigit():
        return pattern.format('{}{}')
    else:
        return None


def escape(s: str) -> str:
    """Escape a string for embedding inside a double-quoted YAML string."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def update_appveyor_yml_python_versions(
    filename: FileOrFilename,
    new_versions: VersionList,
) -> Optional[FileLines]:
    """Update supported Python versions in appveyor.yml.

    Does not touch the file but returns a list of lines with new file contents.
    """
    with open_file(filename) as fp:
        orig_lines = fp.readlines()
        fp.seek(0)
        conf = yaml.safe_load(fp)

    varname = 'PYTHON'
    patterns = set()
    for env in conf['environment']['matrix']:
        for var, value in env.items():
            if var.lower() == 'python':
                varname = var
                pattern = appveyor_detect_py_version_pattern(value)
                if pattern is not None:
                    patterns.add(pattern)
                break

    if not patterns:
        warn(f"Did not recognize any PYTHON environments in {fp.name}")
        return orig_lines

    quote = any(f'{varname}: "' in line for line in orig_lines)

    new_pythons = [
        pattern.format(*ver.split(".", 1))
        for ver in new_versions
        for pattern in sorted(patterns)
    ]

    if quote:
        new_environments = [
            f'{varname}: "{escape(python)}"'
            for python in new_pythons
        ]
    else:
        new_environments = [
            f'{varname}: {python}'
            for python in new_pythons
        ]

    def keep_complicated(value: str) -> bool:
        """Determine if an environment matrix line should be preserved."""
        if value.lower().startswith('python:'):
            ver = value.partition(':')[-1].strip()
            if ver.startswith('"'):
                ver = ast.literal_eval(ver)
            nver = appveyor_normalize_py_version(ver)
            if nver is not None:
                return False
        elif value.startswith('{') and value.endswith('}'):
            env = yaml.safe_load(StringIO(value))
            for var, value in env.items():
                if var.lower() == 'python':
                    nver = appveyor_normalize_py_version(value)
                    if nver is not None and nver not in new_versions:
                        return False
        return True

    new_lines = update_yaml_list(
        orig_lines, ('environment', 'matrix'), new_environments,
        keep=keep_complicated,
    )
    return new_lines
