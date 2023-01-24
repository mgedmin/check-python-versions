"""
Support for pyproject.toml.

There are two ways of declaring Python versions in a pyproject.toml:
classifiers like

    Programming Language :: Python :: 3.8

and tool.poetry.dependencies.python keyword.

check-python-versions supports both.
"""

from tomlkit import dumps
from tomlkit import parse, load

from typing import (
    List,
    Optional,
    TextIO,
    Union,
    cast,
)

from .setup_py import get_versions_from_classifiers, parse_python_requires, update_classifiers, compute_python_requires
from .base import Source
from ..utils import (
    FileLines,
    FileOrFilename,
    is_file_object,
    open_file,
    warn,
)
from ..versions import (
    SortedVersionList,
)


PYPROJECT_TOML = 'pyproject.toml'


def _load_toml(filename: FileOrFilename):
    table = {}
    # tomlkit has two different API to load from file name or file object
    if isinstance(filename, str):
        with open_file(filename) as fp:
            table = load(fp)
    if isinstance(filename, TextIO):
        table = load(filename)
    return table


def get_toml_content(
    filename: FileOrFilename = PYPROJECT_TOML
) -> FileLines:
    """Utility method to see if TOML library keeps style and comments."""
    table = _load_toml(filename)
    return dumps(table).split('\n')


def _get_pyproject_toml_classifiers(
    filename: FileOrFilename = PYPROJECT_TOML
) -> List[str]:
    table = _load_toml(filename)

    if 'tool' not in table:
        return []
    if 'poetry' not in table['tool']:
        return []
    if 'classifiers' not in table['tool']['poetry']:
        return []

    return table['tool']['poetry']['classifiers']


def _get_pyproject_toml_python_requires(
    filename: FileOrFilename = PYPROJECT_TOML
) -> List[str]:
    table = _load_toml(filename)

    if 'tool' not in table:
        return []
    if 'poetry' not in table['tool']:
        return []
    if 'dependencies' not in table['tool']['poetry']:
        return []
    if 'python' not in table['tool']['poetry']['dependencies']:
        return []
    return table['tool']['poetry']['dependencies']['python']


def get_supported_python_versions(
    filename: FileOrFilename = PYPROJECT_TOML
) -> SortedVersionList:
    """Extract supported Python versions from classifiers in pyproject.toml ."""
    classifiers = _get_pyproject_toml_classifiers(filename)

    if classifiers is None:
        # Note: do not return None because pyproject.toml is not an optional source!
        # We want errors to show up if pyproject.toml fails to declare Python
        # versions in classifiers.
        return []

    if not isinstance(classifiers, (list, tuple)):
        warn('The value passed to classifiers is not a list')
        return []

    return get_versions_from_classifiers(classifiers)


def get_python_requires(
    pyproject_toml: FileOrFilename = PYPROJECT_TOML,
) -> Optional[SortedVersionList]:
    """Extract supported Python versions from python_requires in pyproject.toml."""
    python_requires = _get_pyproject_toml_python_requires(pyproject_toml)
    if python_requires is None:
        return None
    if not isinstance(python_requires, str):
        warn('The value passed to python dependency is not a string')
        return None
    return parse_python_requires(python_requires)


def update_supported_python_versions(
    filename: FileOrFilename,
    new_versions: SortedVersionList,
) -> Optional[FileLines]:
    """Update classifiers in a pyproject.toml.

    Does not touch the file but returns a list of lines with new file contents.
    """
    classifiers = _get_pyproject_toml_classifiers(filename)
    if classifiers is None:
        return None
    if not isinstance(classifiers, (list, tuple)):
        warn('The value passed to classifiers is not a list')
        return None
    new_classifiers = update_classifiers(classifiers, new_versions)
    return _update_pyproject_toml_classifiers(filename, new_classifiers)


def update_python_requires(
    filename: FileOrFilename,
    new_versions: SortedVersionList,
) -> Optional[FileLines]:
    """Update python dependency in a pyproject.toml, if it's defined there.

    Does not touch the file but returns a list of lines with new file contents.
    """
    python_requires = _get_pyproject_toml_python_requires(filename)
    if python_requires is None or python_requires == []:
        return None
    comma = ', '
    if ',' in python_requires and ', ' not in python_requires:
        comma = ','
    space = ''
    if '> ' in python_requires or '= ' in python_requires:
        space = ' '
    new_python_requires = compute_python_requires(
        new_versions, comma=comma, space=space)
    if is_file_object(filename):
        # Make sure we can read it twice please.
        # XXX: I don't like this.
        cast(TextIO, filename).seek(0)
    return _update_pyproject_toml_python_requires(filename, new_python_requires)


def _update_pyproject_toml_classifiers(
    filename: FileOrFilename,
    new_value: Union[str, List[str]],
) -> Optional[FileLines]:
    table = _load_toml(filename)

    if 'tool' not in table:
        return []
    if 'poetry' not in table['tool']:
        return []

    table['tool']['poetry']['classifiers'] = new_value

    return dumps(table).split('\n')


def _update_pyproject_toml_python_requires(
        filename: FileOrFilename,
        new_value: Union[str, List[str]],
) -> Optional[FileLines]:
    table = _load_toml(filename)

    if 'tool' not in table:
        return []
    if 'poetry' not in table['tool']:
        return []
    if 'dependencies' not in table['tool']['poetry']:
        return []

    table['tool']['poetry']['dependencies']['python'] = new_value
    return dumps(table).split('\n')


PoetryPyProject = Source(
    title=PYPROJECT_TOML,
    filename=PYPROJECT_TOML,
    extract=get_supported_python_versions,
    update=update_supported_python_versions,
    check_pypy_consistency=True,
    has_upper_bound=True,
)

PoetryPyProjectPythonRequires = Source(
    title='- python_requires',
    filename=PYPROJECT_TOML,
    extract=get_python_requires,
    update=update_python_requires,
    check_pypy_consistency=False,
    has_upper_bound=False,  # TBH it might have one!
)
