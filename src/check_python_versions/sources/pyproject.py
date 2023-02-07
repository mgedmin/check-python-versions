"""
Support for pyproject.toml.

There are several build tools that use pyproject.toml to specify metadata.
Some of them use the PEP 621::

    [project]
    classifiers = [
        ...
        "Programming Language :: Python :: 3.8",
        ...
    ]
    requires-python = ">= 3.8"

check-python-versions also supports old-style flit and poetry metadata::

    [tool.flit.metadata]
    classifiers = [
        ...
        "Programming Language :: Python :: 3.8",
        ...
    ]
    requires-python = ">= 3.8"

    [tool.poetry]
    classifiers = [
        ...
        "Programming Language :: Python :: 3.8",
        ...
    ]

tool.poetry.dependencies.python uses a different syntax and is not supported::

    [tool.poetry.dependencies]
    python = "^3.8"   # not supported yet

"""
from typing import TYPE_CHECKING, Any, List, Optional, Tuple, Union

import tomlkit
from tomlkit import TOMLDocument, dumps, load

from .base import Source
from ..parsers.classifiers import (
    get_versions_from_classifiers,
    update_classifiers,
)
from ..parsers.requires_python import (
    compute_python_requires,
    parse_python_requires,
)
from ..utils import FileLines, FileOrFilename, open_file, warn
from ..versions import SortedVersionList


PYPROJECT_TOML = 'pyproject.toml'


if TYPE_CHECKING:
    from tomlkit.container import Container
    from tomlkit.items import Item


def traverse(document: TOMLDocument, path: str, default: Any = None) -> Any:
    obj: Union[Container, Item] = document
    for step in path.split('.'):
        if not isinstance(obj, dict):
            # complain
            return default
        if step not in obj:
            return default
        obj = obj[step]
    return obj


def _get_pyproject_toml_classifiers(
    filename: FileOrFilename = PYPROJECT_TOML,
) -> Tuple[TOMLDocument, str, Optional[List[str]]]:
    """Extract the list of PyPI classifiers from a pyproject.toml"""

    with open_file(filename) as fp:
        document = load(fp)

    for path in 'project', 'tool.flit.metadata', 'tool.poetry':
        classifiers = traverse(document, f"{path}.classifiers")
        if classifiers is not None:
            break

    if classifiers is None:
        return document, path, None

    if not isinstance(classifiers, list):
        warn(f'The value specified for {path}.classifiers is not an array')
        return document, path, None

    if not all(isinstance(s, str) for s in classifiers):
        warn(f'The value specified for {path}.classifiers'
             ' is not an array of strings')
        return document, path, None

    return document, path, classifiers


def get_supported_python_versions(
    filename: FileOrFilename = PYPROJECT_TOML,
) -> SortedVersionList:
    """Extract supported Python versions from classifiers in pyproject.toml."""

    _d, _p, classifiers = _get_pyproject_toml_classifiers(filename)

    return get_versions_from_classifiers(classifiers or [])


def _get_pyproject_toml_requires_python(
    filename: FileOrFilename = PYPROJECT_TOML,
) -> Tuple[TOMLDocument, str, Optional[str]]:

    with open_file(filename) as fp:
        document = load(fp)

    for path in 'project', 'tool.flit.metadata':
        python_requires = traverse(document, f"{path}.requires-python")
        if python_requires is not None:
            break

    if python_requires is None:
        return document, path, None

    if not isinstance(python_requires, str):
        warn(f'The value specified for {path}.requires-python is not a string')
        return document, path, None

    return document, path, python_requires


def get_python_requires(
    filename: FileOrFilename = PYPROJECT_TOML,
) -> Optional[SortedVersionList]:
    """Extract Python versions from require-python in pyproject.toml."""

    _d, _p, python_requires = _get_pyproject_toml_requires_python(filename)

    if python_requires is None:
        return None

    return parse_python_requires(python_requires)


def update_supported_python_versions(
    filename: FileOrFilename,
    new_versions: SortedVersionList,
) -> Optional[FileLines]:
    """Update classifiers in a pyproject.toml.

    Does not touch the file but returns a list of lines with new file contents.
    """

    document, path, classifiers = _get_pyproject_toml_classifiers(filename)

    if classifiers is None:
        return None

    new_classifiers = update_classifiers(classifiers, new_versions)

    table = traverse(document, path)
    table['classifiers'] = a = tomlkit.array().multiline(True)
    a.extend(new_classifiers)

    return dumps(document).splitlines(True)


def update_python_requires(
    filename: FileOrFilename,
    new_versions: SortedVersionList,
) -> Optional[FileLines]:
    """Update python dependency in a pyproject.toml, if it's defined there.

    Does not touch the file but returns a list of lines with new file contents.
    """

    document, path, python_requires = _get_pyproject_toml_requires_python(
        filename)

    if python_requires is None:
        return None

    comma = ', '
    if ',' in python_requires and ', ' not in python_requires:
        comma = ','
    space = ''
    if '> ' in python_requires or '= ' in python_requires:
        space = ' '

    new_requires = compute_python_requires(
        new_versions, comma=comma, space=space)

    table = traverse(document, path)
    table['requires-python'] = new_requires

    return dumps(document).splitlines(True)


PyProject = Source(
    title=PYPROJECT_TOML,
    filename=PYPROJECT_TOML,
    extract=get_supported_python_versions,
    update=update_supported_python_versions,
    check_pypy_consistency=True,
    has_upper_bound=True,
)

PyProjectPythonRequires = Source(
    title='- python_requires',
    filename=PYPROJECT_TOML,
    extract=get_python_requires,
    update=update_python_requires,
    check_pypy_consistency=False,
    has_upper_bound=False,  # TBH it might have one!
)
