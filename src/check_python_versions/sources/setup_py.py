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
import re
from functools import partial
from typing import (
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    TextIO,
    Tuple,
    Union,
    cast,
)

from ..parsers.python import (
    AstValue,
    eval_ast_node,
    find_call_kwarg_in_ast,
    update_call_arg_in_source,
)
from ..utils import (
    FileLines,
    FileOrFilename,
    is_file_object,
    open_file,
    pipe,
    warn,
)
from ..versions import MAX_MINOR_FOR_MAJOR, SortedVersionList, VersionList


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
        classifiers = pipe("python", setup_py, "-q", "--classifiers",
                           cwd=os.path.dirname(filename)).splitlines()
    if classifiers is None:
        # Note: do not return None because setup.py is not an optional source!
        # We want errors to show up if setup.py fails to declare Python
        # versions in classifiers.
        return []
    if not isinstance(classifiers, (list, tuple)):
        warn('The value passed to setup(classifiers=...) is not a list')
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
        warn('The value passed to setup(python_requires=...) is not a string')
        return None
    return parse_python_requires(python_requires)


def is_version_classifier(s: str) -> bool:
    """Is this classifier a Python version classifer?"""
    prefix = 'Programming Language :: Python :: '
    return s.startswith(prefix) and s[len(prefix):len(prefix) + 1].isdigit()


def is_major_version_classifier(s: str) -> bool:
    """Is this classifier a major Python version classifer?

    That is, is this a version classifier that omits the minor version?
    """
    prefix = 'Programming Language :: Python :: '
    return (
        s.startswith(prefix)
        and s[len(prefix):].replace(' :: Only', '').isdigit()
    )


def get_versions_from_classifiers(
    classifiers: Sequence[str],
) -> SortedVersionList:
    """Extract supported Python versions from classifiers."""
    # Based on
    # https://github.com/mgedmin/project-summary/blob/master/summary.py#L221-L234
    prefix = 'Programming Language :: Python :: '
    impl_prefix = 'Programming Language :: Python :: Implementation :: '
    cpython = impl_prefix + 'CPython'
    versions = {
        s[len(prefix):].replace(' :: Only', '').rstrip()
        for s in classifiers
        if is_version_classifier(s)
    } | {
        s[len(impl_prefix):].rstrip()
        for s in classifiers
        if s.startswith(impl_prefix) and s != cpython
    }
    for major in '2', '3':
        if major in versions and any(
                v.startswith(f'{major}.') for v in versions):
            versions.remove(major)
    return sorted(versions)


def update_classifiers(
    classifiers: Sequence[str],
    new_versions: SortedVersionList
) -> List[str]:
    """Update a list of classifiers with new Python versions."""
    prefix = 'Programming Language :: Python :: '

    for pos, s in enumerate(classifiers):
        if is_version_classifier(s):
            break
    else:
        pos = len(classifiers)

    if any(map(is_major_version_classifier, classifiers)):
        new_versions = sorted(
            set(new_versions).union(
                v.partition('.')[0] for v in new_versions
            )
        )

    classifiers = [
        s for s in classifiers if not is_version_classifier(s)
    ]
    new_classifiers = [
        f'{prefix}{version}'
        for version in new_versions
    ]
    classifiers[pos:pos] = new_classifiers
    return classifiers


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
        warn('The value passed to setup(classifiers=...) is not a list')
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
    if python_requires is None:
        return None
    comma = ', '
    if ',' in python_requires and ', ' not in python_requires:
        comma = ','
    new_python_requires = compute_python_requires(new_versions, comma=comma)
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
    return eval_ast_node(node, keyword) if node is not None else None


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
    new_lines = update_call_arg_in_source(lines, 'setup', keyword, new_value)
    return new_lines


def parse_python_requires(s: str) -> Optional[SortedVersionList]:
    """Compute Python versions allowed by a python_requires expression."""

    # https://www.python.org/dev/peps/pep-0440/#version-specifiers
    rx = re.compile(r'^(~=|==|!=|<=|>=|<|>|===)\s*(\d+(?:\.\d+)*(?:\.\*)?)$')

    class BadConstraint(Exception):
        pass

    Constraint = Tuple[Union[str, int], ...]
    Version = Tuple[int, int]
    CheckFn = Callable[[Version], bool]
    HandlerFn = Callable[[Constraint], CheckFn]
    handlers: Dict[str, HandlerFn] = {}
    handler = partial(partial, handlers.__setitem__)

    #
    # We are not doing a strict PEP-440 implementation here because if
    # python_reqiures allows, say, Python 2.7.16, then we want to report that
    # as Python 2.7.  In each handler ``candidate`` is a two-tuple (X, Y)
    # that represents any Python version between X.Y.0 and X.Y.<whatever>.
    #

    @handler('~=')
    def compatible_version(constraint: Constraint) -> CheckFn:
        if len(constraint) < 2:
            raise BadConstraint('~= requires a version with at least one dot')
        if constraint[-1] == '*':
            raise BadConstraint('~= does not allow a .*')
        return lambda candidate: candidate == constraint[:2]

    @handler('==')
    def matching_version(constraint: Constraint) -> CheckFn:
        # we know len(candidate) == 2
        if len(constraint) == 2 and constraint[-1] == '*':
            return lambda candidate: candidate[0] == constraint[0]
        elif len(constraint) == 1:
            # == X should imply Python X.0
            return lambda candidate: candidate == constraint + (0,)
        else:
            # == X.Y.* and == X.Y.Z both imply Python X.Y
            return lambda candidate: candidate == constraint[:2]

    @handler('!=')
    def excluded_version(constraint: Constraint) -> CheckFn:
        # we know len(candidate) == 2
        if constraint[-1] != '*':
            # != X or != X.Y or != X.Y.Z all are meaningless for us, because
            # there exists some W != Z where we allow X.Y.W and thus allow
            # Python X.Y.
            return lambda candidate: True
        elif len(constraint) == 2:
            # != X.* excludes the entirety of a major version
            return lambda candidate: candidate[0] != constraint[0]
        else:
            # != X.Y.* excludes one particular minor version X.Y,
            # != X.Y.Z.* does not exclude anything, but it's fine,
            # len(candidate) != len(constraint[:-1] so it'll be equivalent to
            # True anyway.
            return lambda candidate: candidate != constraint[:-1]

    @handler('>=')
    def greater_or_equal_version(constraint: Constraint) -> CheckFn:
        if constraint[-1] == '*':
            raise BadConstraint('>= does not allow a .*')
        # >= X, >= X.Y, >= X.Y.Z all work out nicely because in Python
        # (3, 0) >= (3,)
        return lambda candidate: candidate >= constraint[:2]

    @handler('<=')
    def lesser_or_equal_version(constraint: Constraint) -> CheckFn:
        if constraint[-1] == '*':
            raise BadConstraint('<= does not allow a .*')
        if len(constraint) == 1:
            # <= X allows up to X.0
            return lambda candidate: candidate <= constraint + (0,)
        else:
            # <= X.Y[.Z] allows up to X.Y
            return lambda candidate: candidate <= constraint

    @handler('>')
    def greater_version(constraint: Constraint) -> CheckFn:
        if '*' in constraint:
            raise BadConstraint('> does not allow a .*')
        if len(constraint) == 1:
            # > X allows X+1.0 etc
            return lambda candidate: candidate[:1] > constraint
        elif len(constraint) == 2:
            # > X.Y allows X.Y+1 etc
            return lambda candidate: candidate > constraint
        else:
            # > X.Y.Z allows X.Y
            return lambda candidate: candidate >= constraint[:2]

    @handler('<')
    def lesser_version(constraint: Constraint) -> CheckFn:
        if constraint[-1] == '*':
            raise BadConstraint('< does not allow a .*')
        # < X, < X.Y, < X.Y.Z all work out nicely because in Python
        # (3, 0) > (3,), (3, 0) == (3, 0) and (3, 0) < (3, 0, 1)
        return lambda candidate: candidate < constraint

    @handler('===')
    def arbitrary_version(constraint: Constraint) -> CheckFn:
        if constraint[-1] == '*':
            raise BadConstraint('=== does not allow a .*')
        # === X does not allow anything
        # === X.Y throws me into confusion; will pip compare Python's X.Y.Z ===
        # X.Y and reject all possible values of Z?
        # === X.Y.Z allows X.Y
        return lambda candidate: candidate == constraint[:2]

    constraints = []
    for specifier in map(str.strip, s.split(',')):
        m = rx.match(specifier)
        if not m:
            warn(f'Bad python_requires specifier: {specifier}')
            continue
        op, arg = m.groups()
        ver: Constraint = tuple(
            int(segment) if segment != '*' else segment
            for segment in arg.split('.')
        )
        try:
            constraints.append(handlers[op](ver))
        except BadConstraint as error:
            warn(f'Bad python_requires specifier: {specifier} ({error})')

    if not constraints:
        return None

    versions = []
    for major in sorted(MAX_MINOR_FOR_MAJOR):
        for minor in range(0, MAX_MINOR_FOR_MAJOR[major] + 1):
            if all(constraint((major, minor)) for constraint in constraints):
                versions.append(f'{major}.{minor}')
    return versions


def compute_python_requires(
    new_versions: VersionList,
    comma: str = ', '
) -> str:
    """Compute a value for python_requires that matches a set of versions."""
    new_versions = set(new_versions)
    if len(new_versions) == 1:
        return f'=={new_versions.pop()}.*'
    # XXX assumes all versions are X.Y and 3.10 will never be released
    min_version = min(new_versions)
    specifiers = [f'>={min_version}']
    for major in sorted(MAX_MINOR_FOR_MAJOR):
        for minor in range(0, MAX_MINOR_FOR_MAJOR[major] + 1):
            ver = f'{major}.{minor}'
            if ver >= min_version and ver not in new_versions:
                specifiers.append(f'!={ver}.*')
    return comma.join(specifiers)
