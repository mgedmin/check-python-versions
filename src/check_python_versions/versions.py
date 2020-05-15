from typing import Collection, List, Optional, Set


#
# Information about Python releases that needs to be constantly updated as
# Python makes new releases.
#

MAX_PYTHON_1_VERSION = 6  # i.e. 1.6
MAX_PYTHON_2_VERSION = 7  # i.e. 2.7
CURRENT_PYTHON_3_VERSION = 8  # i.e. 3.8

MAX_MINOR_FOR_MAJOR = {
    1: MAX_PYTHON_1_VERSION,
    2: MAX_PYTHON_2_VERSION,
    3: CURRENT_PYTHON_3_VERSION,
}


# XXX: 3.10 will wreak havoc on all my sorted(list_of_version_strings)!
# I'll probably have to make Version a named tuple with an __str__

Version = str   # 'MAJOR.MINOR' usually, but could also be e.g. 'PyPy3'
VersionSet = Set[Version]
VersionList = Collection[Version]
SortedVersionList = List[Version]


def is_important(v: str) -> bool:
    """Is the version important for matching purposes?

    Different sources can express support for different versions, e.g.
    classifiers can express support for "PyPy" but python_requires can't.
    Also some CI systems allow testing on unreleased Python versions that
    cannot be listed in classifiers, so their presence should not cause
    mismatch errors.
    """
    upcoming_release = f'3.{CURRENT_PYTHON_3_VERSION + 1}'
    return (
        not v.startswith(('PyPy', 'Jython')) and v != 'nightly'
        and not v.endswith('-dev') and v != upcoming_release
    )


def important(versions: Collection[str]) -> VersionSet:
    """Filter out unimportant versions.

    See `is_important` for what consitutes "important".
    """
    return {
        v for v in versions
        if is_important(v)
    }


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
