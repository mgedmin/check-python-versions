"""
Tools for manipulating requires-python PyPI classifiers.
"""
import re
from functools import partial
from typing import Callable, Dict, List, Optional, Tuple, Union

from ..utils import warn
from ..versions import (
    MAX_MINOR_FOR_MAJOR,
    SortedVersionList,
    Version,
    VersionList,
)


try:
    from typing import TypedDict
except ImportError:  # pragma: nocover
    from typing_extensions import TypedDict


def parse_python_requires(
    s: str,
    name: str = "python_requires",
    *,
    filename: str = "setup.py",
) -> Optional[SortedVersionList]:
    """Compute Python versions allowed by a python_requires expression."""

    # https://www.python.org/dev/peps/pep-0440/#version-specifiers
    rx = re.compile(r'^(~=|==|!=|<=|>=|<|>|===)\s*(\d+(?:\.\d+)*(?:\.\*)?)$')

    class BadConstraint(Exception):
        """The version clause is ill-formed according to PEP 440."""

    #
    # This works as follows: we split the specifier on commas into a list
    # of Constraints, each represented as a operator and a tuple of numbers
    # with a possible trailing '*'.  PEP 440 calls them "clauses".
    #

    Constraint = Tuple[Union[str, int], ...]

    #
    # The we look up a handler for each operartor.  This handler takes a
    # constraint and compiles it into a checker.  A checker is a function
    # that takes a Python version number as a 2-tuple and returns True if
    # that version passes its constraint.
    #

    VersionTuple = Tuple[int, int]
    CheckFn = Callable[[VersionTuple], bool]
    HandlerFn = Callable[[Constraint], CheckFn]

    #
    # Here we're defining the handlers for all the operators
    #

    handlers: Dict[str, HandlerFn] = {}
    handler = partial(partial, handlers.__setitem__)

    #
    # We are not doing a strict PEP-440 implementation here because if
    # python_requires allows, say, Python 2.7.16, then we want to report that
    # as Python 2.7.  In each handler ``candidate`` is a two-tuple (X, Y)
    # that represents any Python version between X.Y.0 and X.Y.<whatever>.
    #

    @handler('~=')
    def compatible_version(constraint: Constraint) -> CheckFn:
        """~= X.Y more or less means >= X.Y and == X.Y.*"""
        if len(constraint) < 2:
            raise BadConstraint('~= requires a version with at least one dot')
        if constraint[-1] == '*':
            raise BadConstraint('~= does not allow a .*')
        return lambda candidate: candidate == constraint[:2]

    @handler('==')
    def matching_version(constraint: Constraint) -> CheckFn:
        """== X.Y means X.Y, no more, no less; == X[.Y].* is allowed."""
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
        """!= X.Y is the opposite of == X.Y."""
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
        """>= X.Y allows X.Y.* or X.(Y+n).*, or (X+n).*."""
        if constraint[-1] == '*':
            raise BadConstraint('>= does not allow a .*')
        # >= X, >= X.Y, >= X.Y.Z all work out nicely because in Python
        # (3, 0) >= (3,)
        return lambda candidate: candidate >= constraint[:2]

    @handler('<=')
    def lesser_or_equal_version(constraint: Constraint) -> CheckFn:
        """<= X.Y is the opposite of > X.Y."""
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
        """> X.Y is equivalent to >= X.Y and != X.Y, I think."""
        if constraint[-1] == '*':
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
        """< X.Y is equivalent to <= X.Y and != X.Y, I think."""
        if constraint[-1] == '*':
            raise BadConstraint('< does not allow a .*')
        # < X, < X.Y, < X.Y.Z all work out nicely because in Python
        # (3, 0) > (3,), (3, 0) == (3, 0) and (3, 0) < (3, 0, 1)
        return lambda candidate: candidate < constraint

    @handler('===')
    def arbitrary_version(constraint: Constraint) -> CheckFn:
        """=== X.Y means X.Y, without any zero padding etc."""
        if constraint[-1] == '*':
            raise BadConstraint('=== does not allow a .*')
        # === X does not allow anything
        # === X.Y throws me into confusion; will pip compare Python's X.Y.Z ===
        # X.Y and reject all possible values of Z?
        # === X.Y.Z allows X.Y
        return lambda candidate: candidate == constraint[:2]

    #
    # And now we can do what we planned: split and compile the constraints
    # into checkers (which I also call "constraints", for maximum confusion).
    #

    constraints: List[CheckFn] = []
    for specifier in map(str.strip, s.split(',')):
        m = rx.match(specifier)
        if not m:
            warn(f'Bad {name} specifier in {filename}: {specifier}')
            continue
        op, arg = m.groups()
        ver: Constraint = tuple(
            int(segment) if segment != '*' else segment
            for segment in arg.split('.')
        )
        try:
            constraints.append(handlers[op](ver))
        except BadConstraint as error:
            warn(f'Bad {name} specifier in {filename}: {specifier} ({error})')

    if not constraints:
        return None

    #
    # And now we can check all the existing Python versions we know about
    # and list those that pass all the requirements.
    #

    versions = []
    for major in sorted(MAX_MINOR_FOR_MAJOR):
        for minor in range(0, MAX_MINOR_FOR_MAJOR[major] + 1):
            if all(constraint((major, minor)) for constraint in constraints):
                versions.append(Version.from_string(f'{major}.{minor}'))
    return versions


class PythonRequiresStyle(TypedDict):
    comma: str
    space: str


def detect_style(python_requires: str) -> PythonRequiresStyle:
    """Determine how a python_requires string was formatted.

    The return value is a dict of kwargs that can be splatted
    into compute_python_requires(..., **style).
    """
    comma = ', '
    if ',' in python_requires and ', ' not in python_requires:
        comma = ','
    space = ''
    if '> ' in python_requires or '= ' in python_requires:
        space = ' '
    return dict(comma=comma, space=space)


def compute_python_requires(
    new_versions: VersionList,
    *,
    comma: str = ', ',
    space: str = '',
) -> str:
    """Compute a value for python_requires that matches a set of versions."""
    new_versions = set(new_versions)
    latest_python = Version(major=3, minor=MAX_MINOR_FOR_MAJOR[3])
    if len(new_versions) == 1 and new_versions != {latest_python}:
        return f'=={space}{new_versions.pop()}.*'
    min_version = min(new_versions)
    specifiers = [f'>={space}{min_version}']
    for major in sorted(MAX_MINOR_FOR_MAJOR):
        for minor in range(0, MAX_MINOR_FOR_MAJOR[major] + 1):
            ver = Version.from_string(f'{major}.{minor}')
            if ver >= min_version and ver not in new_versions:
                specifiers.append(f'!={space}{ver}.*')
    return comma.join(specifiers)
