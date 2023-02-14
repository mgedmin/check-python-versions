"""
Support for setup.py.

There are two ways of declaring Python versions in a setup.py:
classifiers like

    Programming Language :: Python :: 3.8

and python_requires.

check-python-versions supports both.
"""

import ast
import os
import shutil
import sys
from typing import List, Optional, TextIO, Union, cast

from .base import Source
from ..parsers.classifiers import (
    get_versions_from_classifiers,
    update_classifiers,
)
from ..parsers.python import (
    AstValue,
    eval_ast_node,
    find_call_kwarg_in_ast,
    update_call_arg_in_source,
)
from ..parsers.requires_python import (
    compute_python_requires,
    detect_style,
    parse_python_requires,
)
from ..utils import (
    FileLines,
    FileOrFilename,
    file_name,
    is_file_object,
    open_file,
    pipe,
    warn,
)
from ..versions import SortedVersionList


SETUP_PY = 'setup.py'


def get_supported_python_versions(
    filename: FileOrFilename = SETUP_PY
) -> SortedVersionList:
    """Extract supported Python versions from classifiers in setup.py.

    Note: if AST-based parsing fails, this falls back to executing
    ``python setup.py --classifiers``.
    """
    classifiers = get_setup_py_keyword(filename, 'classifiers')
    if classifiers is None and not is_file_object(filename):
        # AST parsing is complicated
        filename = cast(str, filename)
        setup_py = os.path.basename(filename)
        classifiers = pipe(find_python(), setup_py, "-q", "--classifiers",
                           cwd=os.path.dirname(filename)).splitlines()
    if classifiers is None:
        # Note: do not return None because setup.py is not an optional source!
        # We want errors to show up if setup.py fails to declare Python
        # versions in classifiers.
        return []
    if not isinstance(classifiers, (list, tuple)):
        warn(f'The value passed to setup(classifiers=...) in {filename}'
             ' is not a list')
        return []
    return get_versions_from_classifiers(classifiers)


def get_python_requires(
    setup_py: FileOrFilename = SETUP_PY,
) -> Optional[SortedVersionList]:
    """Extract supported Python versions from python_requires in setup.py."""
    python_requires = get_setup_py_keyword(setup_py, 'python_requires')
    if python_requires is None:
        return None
    if not isinstance(python_requires, str):
        warn('The value passed to setup(python_requires=...)'
             f' in {file_name(setup_py)} is not a string')
        return None
    return parse_python_requires(python_requires, filename=file_name(setup_py))


def update_supported_python_versions(
    filename: FileOrFilename,
    new_versions: SortedVersionList,
) -> Optional[FileLines]:
    """Update classifiers in a setup.py.

    Does not touch the file but returns a list of lines with new file contents.
    """
    classifiers = get_setup_py_keyword(filename, 'classifiers')
    if classifiers is None:
        return None
    if not isinstance(classifiers, (list, tuple)):
        warn('The value passed to setup(classifiers=...) in'
             f' {file_name(filename)} is not a list')
        return None
    new_classifiers = update_classifiers(classifiers, new_versions)
    return update_setup_py_keyword(filename, 'classifiers', new_classifiers)


def update_python_requires(
    filename: FileOrFilename,
    new_versions: SortedVersionList,
) -> Optional[FileLines]:
    """Update python_requires in a setup.py, if it's defined there.

    Does not touch the file but returns a list of lines with new file contents.
    """
    python_requires = get_setup_py_keyword(filename, 'python_requires')
    if not isinstance(python_requires, str):
        return None
    style = detect_style(python_requires)
    new_python_requires = compute_python_requires(new_versions, **style)
    if is_file_object(filename):
        # Make sure we can read it twice please.
        # XXX: I don't like this.
        cast(TextIO, filename).seek(0)
    return update_setup_py_keyword(filename, 'python_requires',
                                   new_python_requires)


def get_setup_py_keyword(
    setup_py: FileOrFilename,
    keyword: str,
) -> Optional[AstValue]:
    """Extract a value passed to setup() in a setup.py.

    Parses the setup.py into an Abstact Syntax Tree and tries to figure out
    what value was passed to the named keyword argument.

    Returns None if the AST is too complicated to statically evaluate.
    """
    with open_file(setup_py) as f:
        try:
            tree = ast.parse(f.read(), f.name)
        except SyntaxError as error:
            warn(f'Could not parse {f.name}: {error}')
            return None
    node = find_call_kwarg_in_ast(tree, ('setup', 'setuptools.setup'), keyword,
                                  filename=f.name)
    if node is None:
        return None
    return eval_ast_node(node, keyword, filename=f.name)


def update_setup_py_keyword(
    setup_py: FileOrFilename,
    keyword: str,
    new_value: Union[str, List[str]],
) -> FileLines:
    """Update a value passed to setup() in a setup.py.

    Does not touch the file but returns a list of lines with new file contents.
    """
    with open_file(setup_py) as f:
        lines = f.readlines()
    new_lines = update_call_arg_in_source(lines, ('setup', 'setuptools.setup'),
                                          keyword, new_value, filename=f.name)
    return new_lines


def find_python() -> str:
    """Find a Python interpreter."""
    # The reason I prefer python3 or python from $PATH over sys.executable is
    # this gives the user some control.  E.g. if the setup.py of the project
    # requires some dependencies, the user could install them into a virtualenv
    # and activate it.
    if shutil.which('python3'):
        return 'python3'
    if shutil.which('python'):
        return 'python'
    return sys.executable


SetupClassifiers = Source(
    title=SETUP_PY,
    filename=SETUP_PY,
    extract=get_supported_python_versions,
    update=update_supported_python_versions,
    check_pypy_consistency=True,
    has_upper_bound=True,
)

SetupPythonRequires = Source(
    title='- python_requires',
    filename=SETUP_PY,
    extract=get_python_requires,
    update=update_python_requires,
    check_pypy_consistency=False,
    has_upper_bound=False,  # TBH it might have one!
)
