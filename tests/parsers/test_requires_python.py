from typing import List

import pytest

from check_python_versions.parsers.requires_python import (
    compute_python_requires,
    detect_style,
    parse_python_requires,
)
from check_python_versions.versions import Version


def v(versions: List[str]) -> List[Version]:
    return [Version.from_string(v) for v in versions]


@pytest.mark.parametrize('constraint, result', [
    ('~= 2.7', ['2.7']),
    ('~= 2.7.12', ['2.7']),
])
def test_parse_python_requires_approximately(constraint, result):
    assert parse_python_requires(constraint) == v(result)


def test_parse_python_requires_approximately_not_enough_dots(capsys):
    assert parse_python_requires('~= 2') is None
    assert (
        'Bad python_requires specifier in setup.py: ~= 2'
        ' (~= requires a version with at least one dot)'
        in capsys.readouterr().err
    )


@pytest.mark.parametrize('constraint, result', [
    ('== 2.7', ['2.7']),
    ('== 2.7.*', ['2.7']),
    ('== 2.7.12', ['2.7']),
    ('== 2.*, >= 2.6', ['2.6', '2.7']),
    ('== 3.0', ['3.0']),
    ('== 3', ['3.0']),
])
def test_parse_python_requires_matching_version(constraint, result):
    assert parse_python_requires(constraint) == v(result)


def test_parse_python_requires_greater_than(fix_max_python_3_version):
    fix_max_python_3_version(8)
    assert parse_python_requires('>= 3.6') == v(['3.6', '3.7', '3.8'])


@pytest.mark.parametrize('constraint, result', [
    ('>= 2.7, != 3.*', ['2.7']),
    ('>= 2.7.12, != 3.*', ['2.7']),
    ('>= 2.7, != 3.0.*, != 3.1.*', ['2.7', '3.2', '3.3']),
    # != 3.2 means we reject 3.2.0 but still accept any other 3.2.x
    ('>= 2.7, != 3.2', ['2.7', '3.0', '3.1', '3.2', '3.3']),
    ('>= 2.7, != 3.2.1', ['2.7', '3.0', '3.1', '3.2', '3.3']),
    ('>= 2.7, <= 3', ['2.7', '3.0']),
    ('>= 2.7, <= 3.2', ['2.7', '3.0', '3.1', '3.2']),
    ('>= 2.7, <= 3.2.1', ['2.7', '3.0', '3.1', '3.2']),
    ('>= 3', ['3.0', '3.1', '3.2', '3.3']),
])
def test_parse_python_requires_greater_than_with_exceptions(
    fix_max_python_3_version, constraint, result
):
    fix_max_python_3_version(3)
    assert parse_python_requires(constraint) == v(result)


def test_parse_python_requires_multiple_greater_than(fix_max_python_3_version):
    fix_max_python_3_version(7)
    assert parse_python_requires('>= 2.7, >= 3.6') == v(['3.6', '3.7'])


@pytest.mark.parametrize('constraint, result', [
    ('> 2, < 3.1', ['3.0']),
    ('> 2.6, < 3', ['2.7']),
    ('> 2.7.12, < 3', ['2.7']),
    ('> 2.7.12, < 3.0', ['2.7']),
    ('> 2.7.12, < 3.1', ['2.7', '3.0']),
    ('> 2.7.12, < 3.0.1', ['2.7', '3.0']),
])
def test_parse_python_requires_exclusive_ordering(constraint, result):
    assert parse_python_requires(constraint) == v(result)


@pytest.mark.parametrize('constraint, result', [
    ('=== 2.7', ['2.7']),
    ('=== 2.7.12', ['2.7']),
    ('=== 3', []),
])
def test_parse_python_requires_arbitrary_version(constraint, result):
    assert parse_python_requires(constraint) == v(result)


@pytest.mark.parametrize('op', ['~=', '>=', '<=', '>', '<', '==='])
def test_parse_python_requires_unexpected_dot_star(fix_max_python_3_version,
                                                   capsys, op):
    fix_max_python_3_version(7)
    assert parse_python_requires(f'{op} 3.6.*') is None
    assert (
        'Bad python_requires specifier in setup.py:'
        f' {op} 3.6.* ({op} does not allow a .*)'
        in capsys.readouterr().err
    )


@pytest.mark.parametrize('specifier', [
    '%= 42',
    '== nobody.knows',
    '!= *.*.*',
    'xyzzy',
])
def test_parse_python_requires_syntax_errors(capsys, specifier):
    assert parse_python_requires(specifier) is None
    assert (
        f'Bad python_requires specifier in setup.py: {specifier}'
        in capsys.readouterr().err
    )


@pytest.mark.parametrize("python_requires, comma, space", [
    (">=3.8", ", ", ""),
    (">= 3.8", ", ", " "),
    (">=2.7,!=3.0", ",", ""),
])
def test_detect_style(python_requires, comma, space):
    assert detect_style(python_requires) == dict(comma=comma, space=space)


@pytest.mark.parametrize('versions, expected', [
    (['2.7'], '==2.7.*'),
    (['3.6', '3.7'], '>=3.6'),
    (['2.7', '3.4', '3.5', '3.6', '3.7'],
     '>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*'),
    (['3.7'], '>=3.7'),
])
def test_compute_python_requires(versions, expected, fix_max_python_3_version):
    fix_max_python_3_version(7)
    result = compute_python_requires(v(versions))
    assert result == expected
    assert parse_python_requires(result) == v(versions)


@pytest.mark.parametrize('versions, expected', [
    (['3.9', '3.10'], '>=3.9'),
    (['3.10', '3.11'], '>=3.10'),
])
def test_compute_python_requires_3_10(versions, expected,
                                      fix_max_python_3_version):
    fix_max_python_3_version(10)
    result = compute_python_requires(v(versions))
    assert result == expected
