"""Python version business logic."""

import re
from typing import Collection, List, NamedTuple, Optional, Set, Union


#
# Information about Python releases that needs to be constantly updated as
# Python makes new releases.
#

MAX_PYTHON_1_VERSION = 6  # i.e. 1.6
MAX_PYTHON_2_VERSION = 7  # i.e. 2.7
CURRENT_PYTHON_3_VERSION = 11  # i.e. 3.10

MAX_MINOR_FOR_MAJOR = {
    1: MAX_PYTHON_1_VERSION,
    2: MAX_PYTHON_2_VERSION,
    3: CURRENT_PYTHON_3_VERSION,
}


VERSION_RX = re.compile('^([^-0-9]*)([0-9]*)([.][0-9]+)?(.*)$')


class Version(NamedTuple):
    """A simplified Python version number.

    Primarily needed so we can sort lists of version numbers correctly, i.e.
    2.7, 3.0, 3.1, 3.2, ..., 3.9, 3.10, ...

    Can have an optional prefix, e.g. PyPy3.6 is Version(prefix='PyPy',
    major=3, minor=6).

    Can have an optional suffix, e.g. 3.10-dev is Version(major=3, minor=10,
    suffix='-dev').

    Any string can be round-tripped to a Version and back via
    Version.from_string() and Version.__str__.
    """

    prefix: str = ''
    major: int = -1  # I'd've preferred to use None, but it complicates sorting
    minor: int = -1
    suffix: str = ''

    @classmethod
    def from_string(cls, v: str) -> 'Version':
        m = VERSION_RX.match(v)
        assert m is not None
        prefix, major, minor, suffix = m.groups()
        return cls(
            prefix,
            int(major) if major else -1,
            int(minor[1:]) if minor else -1,
            suffix,
        )

    def __repr__(self) -> str:
        return 'Version({})'.format(', '.join(part for part in [
            f'prefix={self.prefix!r}' if self.prefix else '',
            f'major={self.major!r}' if self.major != -1 else '',
            f'minor={self.minor!r}' if self.minor != -1 else '',
            f'suffix={self.suffix!r}' if self.suffix else '',
        ] if part))

    def __str__(self) -> str:
        major = '' if self.major == -1 else f'{self.major}'
        minor = '' if self.minor == -1 else f'.{self.minor}'
        return f'{self.prefix}{major}{minor}{self.suffix}'


VersionSet = Set[Version]
VersionList = Collection[Version]
SortedVersionList = List[Version]


def is_important(v: Union[Version, str]) -> bool:
    """Is the version important for matching purposes?

    Different sources can express support for different versions, e.g.
    classifiers can express support for "PyPy" but python_requires can't.
    Also some CI systems allow testing on unreleased Python versions that
    cannot be listed in classifiers, so their presence should not cause
    mismatch errors.
    """
    if not isinstance(v, Version):
        v = Version.from_string(v)
    upcoming_release = Version(major=3, minor=CURRENT_PYTHON_3_VERSION + 1)
    return (
        not v.prefix.startswith(('PyPy', 'Jython')) and v.prefix != 'nightly'
        and '-dev' not in v.suffix
        and '-alpha' not in v.suffix
        and '-beta' not in v.suffix
        and '-rc' not in v.suffix
        and v != upcoming_release
    )


def important(versions: Collection[Version]) -> VersionSet:
    """Filter out unimportant versions.

    See `is_important` for what consitutes "important".
    """
    return {
        v for v in versions
        if is_important(v)
    }


def pypy_versions(versions: Collection[Version]) -> VersionSet:
    """Filter PyPy versions."""
    return {
        v for v in versions
        if v.prefix.startswith('PyPy')
    }


def expand_pypy(versions: Collection[Version]) -> SortedVersionList:
    """Determine whether PyPy support means PyPy2 or PyPy3 or both.

    Some data sources (like setup.py classifiers) allow you to indicate PyPy
    support without specifying whether you mean PyPy2 or PyPy3.  Other data
    sources (like all CI systems) are more explicit.  To make these version
    lists directly comparable we need to look at supported CPython versions and
    translate that knowledge into PyPy versions.
    """
    supports_pypy = any(v.prefix == 'PyPy' for v in versions)
    if not supports_pypy:
        return sorted(versions)
    supports_py2 = any(v.major == 2 for v in versions)
    supports_py3 = any(v.major == 3 for v in versions)
    return sorted(
        [v for v in versions if v.prefix != 'PyPy'] +
        ([Version.from_string('PyPy')] if supports_py2 else []) +
        ([Version.from_string('PyPy3')] if supports_py3 else [])
    )


def update_version_list(
    versions: VersionList,
    add: Optional[VersionList] = None,
    drop: Optional[VersionList] = None,
    update: Optional[VersionList] = None,
) -> SortedVersionList:
    """Compute a new list of supported versions.

    ``add`` will add to supported versions.
    ``drop`` will remove from supported versions.
    ``update`` will specify supported versions.

    You may combine ``add`` and ``drop``.  It doesn't make sense to combine
    ``update`` with either ``add`` or ``drop``.
    """
    if update:
        return sorted(update)
    else:
        return sorted(set(versions).union(add or ()).difference(drop or ()))
