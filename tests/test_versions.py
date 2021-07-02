import pytest

from check_python_versions.versions import (
    Version,
    expand_pypy,
    important,
    pypy_versions,
    update_version_list,
)


def test_version_from_string() -> None:
    assert Version.from_string('3') == Version(major=3)
    assert Version.from_string('3.0') == Version(major=3, minor=0)
    assert Version.from_string('3.6') == Version(major=3, minor=6)
    assert Version.from_string('3.10-dev') == Version('', 3, 10, '-dev')
    assert Version.from_string('PyPy') == Version('PyPy')
    assert Version.from_string('PyPy3') == Version('PyPy', 3)
    assert Version.from_string('PyPy-dev') == Version('PyPy', suffix='-dev')
    assert Version.from_string('PyPy3-dev') == Version('PyPy', 3, -1, '-dev')
    assert Version.from_string('3') != Version.from_string('3.0')


def test_version_repr() -> None:
    assert repr(Version()) == 'Version()'
    assert repr(Version(major=3)) == 'Version(major=3)'
    assert repr(Version(major=3, minor=0)) == 'Version(major=3, minor=0)'
    assert repr(Version(major=3, minor=6)) == 'Version(major=3, minor=6)'
    assert repr(Version(major=3, minor=10, suffix='-dev')) == \
        "Version(major=3, minor=10, suffix='-dev')"
    assert repr(Version(prefix='PyPy')) == "Version(prefix='PyPy')"
    assert repr(Version(prefix='PyPy', major=3, suffix='-dev')) == \
        "Version(prefix='PyPy', major=3, suffix='-dev')"


@pytest.mark.parametrize('v', [
    '3',
    '3.0',
    '3.6',
    '3.10-dev',
    'PyPy',
    'PyPy3',
    'PyPy-dev',
    'PyPy3-dev',
    'PyPy3-dev',
])
def test_version_str_roundtrips(v):
    assert str(Version.from_string(v)) == v


def test_version_sorting():
    assert sorted(Version.from_string(v) for v in [
        '2.7', '3.1', '3.6', '3.10', '3.10-dev',
        'PyPy', 'PyPy3', 'nightly',
    ]) == [Version.from_string(v) for v in [
        '2.7', '3.1', '3.6', '3.10', '3.10-dev',
        'PyPy', 'PyPy3', 'nightly',
    ]]


def test_important(fix_max_python_3_version):
    fix_max_python_3_version(7)
    assert important({
        '2.7', '3.4', '3.7-dev', '3.8', 'nightly', 'PyPy3', 'Jython',
        '3.10.0-beta.3', '3.10.0-alpha.1', '3.10.0-rc.2',
    }) == {'2.7', '3.4'}


def test_pypy_versions():
    assert pypy_versions({
        Version.from_string(v)
        for v in ['2.7', '3.4', '3.7-dev', '3.8', 'nightly', 'PyPy3', 'Jython']
    }) == {Version.from_string(v) for v in ['PyPy3']}


@pytest.mark.parametrize("versions, expected", [
    (['3.6', '2.7'], ['2.7', '3.6']),
    (['2.7', '3.6', 'PyPy'], ['2.7', '3.6', 'PyPy', 'PyPy3']),
    (['2.7', 'PyPy'], ['2.7', 'PyPy']),
    (['3.6', 'PyPy'], ['3.6', 'PyPy3']),
    (['PyPy'], []),  # lol, garbage in, garbage out
])
def test_expand_pypy(versions, expected):
    assert expand_pypy([Version.from_string(v) for v in versions]) == [
        Version.from_string(v) for v in expected
    ]


def test_update_version_list():
    assert update_version_list(['2.7', '3.4']) == ['2.7', '3.4']
    assert update_version_list(['2.7', '3.4'], add=['3.4', '3.5']) == [
        '2.7', '3.4', '3.5',
    ]
    assert update_version_list(['2.7', '3.4'], drop=['3.4', '3.5']) == [
        '2.7',
    ]
    assert update_version_list(['2.7', '3.4'], add=['3.5'], drop=['2.7']) == [
        '3.4', '3.5',
    ]
    assert update_version_list(['2.7', '3.4'], drop=['3.4', '3.5']) == [
        '2.7',
    ]
    assert update_version_list(['2.7', '3.4'], update=['3.4', '3.5']) == [
        '3.4', '3.5',
    ]
