import pytest

from check_python_versions.parsers.classifiers import (
    get_versions_from_classifiers,
    update_classifiers,
)
from check_python_versions.versions import Version


def v(versions: list[str]) -> list[Version]:
    return [Version.from_string(v) for v in versions]


def test_get_versions_from_classifiers():
    assert get_versions_from_classifiers([
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ]) == v(['2.7', '3.6', '3.7', 'PyPy', 'PyPy3'])


def test_get_versions_from_classifiers_major_only():
    assert get_versions_from_classifiers([
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ]) == v(['2', '3'])


def test_get_versions_from_classifiers_with_only_suffix():
    assert get_versions_from_classifiers([
        'Programming Language :: Python :: 2 :: Only',
    ]) == v(['2'])


def test_get_versions_from_classifiers_with_trailing_whitespace():
    # I was surprised too that this is allowed!
    assert get_versions_from_classifiers([
        'Programming Language :: Python :: 3.6 ',
    ]) == v(['3.6'])


def test_update_classifiers():
    assert update_classifiers([
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Typing :: Typed',
    ], v(['2.7', '3.7', '3.10'])) == [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Typing :: Typed',
    ]


def test_update_classifiers_drop_major():
    assert update_classifiers([
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Typing :: Typed',
    ], v(['3.6', '3.7'])) == [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Typing :: Typed',
    ]


def test_update_classifiers_no_major():
    assert update_classifiers([
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Typing :: Typed',
    ], v(['2.7', '3.7'])) == [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Typing :: Typed',
    ]


def test_update_classifiers_none_were_present():
    assert update_classifiers([
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
    ], v(['2.7', '3.7'])) == [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.7',
    ]


@pytest.mark.parametrize(('current', 'versions', 'expected'), [
    (
        ['3', '3 :: Only', '3.10'],
        ['3.10', '3.11'],
        ['3', '3 :: Only', '3.10', '3.11'],
    ),
    (
        ['2', '2 :: Only', '2.6', '2.7'],
        ['2.7'],
        ['2', '2 :: Only', '2.7'],
    ),
    (
        ['3', '3 :: Only', '3.10'],
        ['2.7', '3.10'],
        ['2', '2.7', '3', '3.10'],
    ),
    (
        ['3', '3 :: Only', '3.10'],
        ['2.7'],
        ['2', '2.7'],
    ),
    (['3', '3 :: Only', '3.10'], [], []),
    (['3', '3.10'], ['3.10', '3.11'], ['3', '3.10', '3.11']),
])
def test_update_classifiers_exclusive_major(current, versions, expected):
    prefix = 'Programming Language :: Python :: '
    return_value = update_classifiers(
        ['Environment :: Console', *(prefix + s for s in current),
         prefix + 'Implementation :: CPython'],
        v(versions),
    )
    assert return_value == [
        'Environment :: Console', *(prefix + s for s in expected),
        prefix + 'Implementation :: CPython',
    ]
