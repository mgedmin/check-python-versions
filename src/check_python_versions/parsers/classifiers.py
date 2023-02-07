"""
Tools for manipulating PyPI classifiers.
"""
from typing import List, Sequence

from ..versions import SortedVersionList, Version, expand_pypy


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
    return expand_pypy(list(map(Version.from_string, versions)))


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
                v._replace(prefix='', minor=-1, suffix='')
                for v in new_versions
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
