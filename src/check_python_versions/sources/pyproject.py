"""
Support for pyproject.toml.

There are two ways of declaring Python versions in a pyproject.toml:
classifiers like

    Programming Language :: Python :: 3.8

and tool.poetry.dependencies.python keyword.

check-python-versions supports both.
"""

from io import StringIO

from tomlkit import dumps
from tomlkit import load
from tomlkit import TOMLDocument

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

TOML_CLASSIFIERS_KWD = 'classifiers'
TOML_DEPENDENCIES_KWD = 'dependencies'
TOML_PYTHON_KWD = 'python'
TOML_PYTHON_REQUIRES_KWD = 'requires-python'

# poetry TOML keywords
TOML_TOOL_KWD = 'tool'
TOML_POETRY_KWD = 'poetry'
TOML_BUILD_SYSTEM_KWD = 'build-system'
TOML_BUILD_BACKEND_KWD = 'build-backend'
TOML_REQUIRES_KWD = 'requires'

# setuptools TOML keywords
TOML_PROJECT_KWD = 'project'
TOML_SETUPTOOLS_KWD = 'setuptools'

# flit TOML keywords
TOML_FLIT_KWD = 'flit'


def load_toml(filename: FileOrFilename) -> TOMLDocument:
    """Utility method that returns a TOMLDocument."""
    table = {}
    # tomlkit has two different API to load from file name or file object
    if isinstance(filename, str) or isinstance(filename, StringIO):
        with open_file(filename) as fp:
            table = load(fp)
    if isinstance(filename, TextIO):
        table = load(filename)
    return table


def is_poetry_toml(
    table: TOMLDocument
) -> bool:
    """Utility method to know if pyproject.toml is for poetry."""
    _ret = False

    if TOML_TOOL_KWD in table:
        if TOML_POETRY_KWD in table[TOML_TOOL_KWD]:
            _ret = True
    if TOML_BUILD_SYSTEM_KWD in table:
        if TOML_BUILD_BACKEND_KWD in table[TOML_BUILD_SYSTEM_KWD]:
            if TOML_POETRY_KWD in table[TOML_BUILD_SYSTEM_KWD][TOML_BUILD_BACKEND_KWD]:
                _ret = True
        if TOML_REQUIRES_KWD in table[TOML_BUILD_SYSTEM_KWD]:
            if list(filter(lambda x: TOML_POETRY_KWD in x, table[TOML_BUILD_SYSTEM_KWD][TOML_REQUIRES_KWD])):
                _ret = True
    return _ret


def is_setuptools_toml(
    table: TOMLDocument
) -> bool:
    """Utility method to know if pyproject.toml is for setuptool."""
    _ret = False
    if TOML_BUILD_SYSTEM_KWD in table:
        if TOML_BUILD_BACKEND_KWD in table[TOML_BUILD_SYSTEM_KWD]:
            if TOML_SETUPTOOLS_KWD in table[TOML_BUILD_SYSTEM_KWD][TOML_BUILD_BACKEND_KWD]:
                _ret = True
        if TOML_REQUIRES_KWD in table[TOML_BUILD_SYSTEM_KWD]:
            if list(filter(lambda x: TOML_SETUPTOOLS_KWD in x, table[TOML_BUILD_SYSTEM_KWD][TOML_REQUIRES_KWD])):
                _ret = True

    # from https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html#setuptools-specific-configuration
    #  "[tool.setuptools] table is still in beta"
    #  "These configurations are completely optional and probably can be skipped when creating simple packages"
    if TOML_TOOL_KWD in table:
        if TOML_SETUPTOOLS_KWD in table[TOML_TOOL_KWD]:
            _ret = True
    return _ret


def is_flit_toml(
    table: TOMLDocument
) -> bool:
    """Utility method to know if pyproject.toml is for flit."""
    _ret = False
    if TOML_TOOL_KWD in table:
        if TOML_FLIT_KWD in table[TOML_TOOL_KWD]:
            _ret = True
    if TOML_BUILD_SYSTEM_KWD in table:
        if TOML_BUILD_BACKEND_KWD in table[TOML_BUILD_SYSTEM_KWD]:
            if TOML_FLIT_KWD in table[TOML_BUILD_SYSTEM_KWD][TOML_BUILD_BACKEND_KWD]:
                _ret = True
        if TOML_REQUIRES_KWD in table[TOML_BUILD_SYSTEM_KWD]:
            if list(filter(lambda x: TOML_FLIT_KWD in x, table[TOML_BUILD_SYSTEM_KWD][TOML_REQUIRES_KWD])):
                _ret = True
    return _ret


def _get_poetry_classifiers(table: TOMLDocument) -> List[str]:
    if TOML_TOOL_KWD not in table:
        return []
    if TOML_POETRY_KWD not in table[TOML_TOOL_KWD]:
        return []
    if TOML_CLASSIFIERS_KWD not in table[TOML_TOOL_KWD][TOML_POETRY_KWD]:
        return []
    return table[TOML_TOOL_KWD][TOML_POETRY_KWD][TOML_CLASSIFIERS_KWD]


def _get_setuptools_flit_classifiers(table: TOMLDocument) -> List[str]:
    if TOML_PROJECT_KWD not in table:
        return []
    if TOML_CLASSIFIERS_KWD not in table[TOML_PROJECT_KWD]:
        return []
    return table[TOML_PROJECT_KWD][TOML_CLASSIFIERS_KWD]


def _get_pyproject_toml_classifiers(
    filename: FileOrFilename = PYPROJECT_TOML
) -> List[str]:
    _classifiers = []
    table = load_toml(filename)
    if is_poetry_toml(table):
        _classifiers = _get_poetry_classifiers(table)
    if is_setuptools_toml(table) or is_flit_toml(table):
        _classifiers = _get_setuptools_flit_classifiers(table)

    return _classifiers


def _get_poetry_python_requires(table: TOMLDocument) -> List[str]:
    if TOML_TOOL_KWD not in table:
        return []
    if TOML_POETRY_KWD not in table[TOML_TOOL_KWD]:
        return []
    if TOML_DEPENDENCIES_KWD not in table[TOML_TOOL_KWD][TOML_POETRY_KWD]:
        return []
    if TOML_PYTHON_KWD not in table[TOML_TOOL_KWD][TOML_POETRY_KWD][TOML_DEPENDENCIES_KWD]:
        return []
    return table[TOML_TOOL_KWD][TOML_POETRY_KWD][TOML_DEPENDENCIES_KWD][TOML_PYTHON_KWD]


def _get_setuptools_flit_python_requires(table: TOMLDocument) -> List[str]:
    if TOML_PROJECT_KWD not in table:
        return []
    if TOML_PYTHON_REQUIRES_KWD not in table[TOML_PROJECT_KWD]:
        return []
    return table[TOML_PROJECT_KWD][TOML_PYTHON_REQUIRES_KWD]


def _get_pyproject_toml_python_requires(
    filename: FileOrFilename = PYPROJECT_TOML
) -> List[str]:
    _python_requires = []
    table = load_toml(filename)
    if is_poetry_toml(table):
        _python_requires = _get_poetry_python_requires(table)
    if is_setuptools_toml(table) or is_flit_toml(table):
        _python_requires = _get_setuptools_flit_python_requires(table)

    return _python_requires


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

    if not isinstance(classifiers, list):
        warn('The value specified for classifiers is not a list')
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
        warn('The value specified for python dependency is not a string')
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
    if not isinstance(classifiers, list):
        warn('The value specified for classifiers is not a list')
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


def _set_poetry_classifiers(
    table: TOMLDocument,
    new_value: Union[str, List[str]],
) -> Optional[FileLines]:
    if TOML_TOOL_KWD not in table:
        return []
    if TOML_POETRY_KWD not in table[TOML_TOOL_KWD]:
        return []
    table[TOML_TOOL_KWD][TOML_POETRY_KWD][TOML_CLASSIFIERS_KWD] = new_value
    return dumps(table).split('\n')


def _set_setuptools_flit_classifiers(
    table: TOMLDocument,
    new_value: Union[str, List[str]],
) -> Optional[FileLines]:
    if TOML_PROJECT_KWD not in table:
        return []
    if TOML_CLASSIFIERS_KWD not in table[TOML_PROJECT_KWD]:
        return []
    table[TOML_PROJECT_KWD][TOML_CLASSIFIERS_KWD] = new_value
    return dumps(table).split('\n')


def _update_pyproject_toml_classifiers(
    filename: FileOrFilename,
    new_value: Union[str, List[str]],
) -> Optional[FileLines]:
    _updated_table = []
    table = load_toml(filename)
    if is_poetry_toml(table):
        _updated_table = _set_poetry_classifiers(table, new_value)
    if is_setuptools_toml(table) or is_flit_toml(table):
        _updated_table = _set_setuptools_flit_classifiers(table, new_value)

    return _updated_table


def _set_poetry_python_requires(
    table: TOMLDocument,
    new_value: Union[str, List[str]],
) -> Optional[FileLines]:
    if TOML_TOOL_KWD not in table:
        return []
    if TOML_POETRY_KWD not in table[TOML_TOOL_KWD]:
        return []
    if TOML_DEPENDENCIES_KWD not in table[TOML_TOOL_KWD][TOML_POETRY_KWD]:
        return []
    table[TOML_TOOL_KWD][TOML_POETRY_KWD][TOML_DEPENDENCIES_KWD][TOML_PYTHON_KWD] = new_value
    return dumps(table).split('\n')


def _set_setuptools_flit_python_requires(
    table: TOMLDocument,
    new_value: Union[str, List[str]],
) -> Optional[FileLines]:
    if TOML_PROJECT_KWD not in table:
        return []
    if TOML_PYTHON_REQUIRES_KWD not in table[TOML_PROJECT_KWD]:
        return []
    table[TOML_PROJECT_KWD][TOML_PYTHON_REQUIRES_KWD] = new_value
    return dumps(table).split('\n')


def _update_pyproject_toml_python_requires(
        filename: FileOrFilename,
        new_value: Union[str, List[str]],
) -> Optional[FileLines]:
    _updated_table = []
    table = load_toml(filename)
    if is_poetry_toml(table):
        _updated_table = _set_poetry_python_requires(table, new_value)
    if is_setuptools_toml(table) or is_flit_toml(table):
        _updated_table = _set_setuptools_flit_python_requires(table, new_value)

    return _updated_table


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
