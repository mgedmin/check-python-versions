from typing import List

import pytest

from check_python_versions.parsers.poetry_version_spec import (
    compute_poetry_spec,
    detect_poetry_version_spec_style,
    parse_poetry_version_constraint,
)
from check_python_versions.versions import Version


def v(versions: List[str]) -> List[Version]:
    return [Version.from_string(v) for v in versions]


@pytest.mark.parametrize('constraint, result', [
    ('^2.7', ['2.7']),
    ('^2.7.12', ['2.7']),
    ('^3', ['3.0', '3.1', '3.2', '3.3']),
    ('^3.0', ['3.0', '3.1', '3.2', '3.3']),
    ('^3.2', ['3.2', '3.3']),
    ('^3.2.3', ['3.2', '3.3']),
])
def test_caret_version(constraint, result, fix_max_python_3_version):
    fix_max_python_3_version(3)
    assert parse_poetry_version_constraint(constraint) == v(result)


@pytest.mark.parametrize('constraint, result', [
    ('~2.7', ['2.7']),
    ('~2.7.12', ['2.7']),
    ('~3', ['3.0', '3.1', '3.2', '3.3']),
    ('~3.2', ['3.2']),
    ('~3.2.3', ['3.2']),
])
def test_tilde_version(constraint, result, fix_max_python_3_version):
    fix_max_python_3_version(3)
    assert parse_poetry_version_constraint(constraint) == v(result)


@pytest.mark.parametrize('constraint, result', [
    ('2.7', ['2.7']),
    ('2.7.*', ['2.7']),
    ('2.7.12', ['2.7']),
    ('2.*, >= 2.6', ['2.6', '2.7']),
    ('3.0', ['3.0']),
    ('3', ['3.0']),
])
def test_plain_version(constraint, result):
    assert parse_poetry_version_constraint(constraint) == v(result)


@pytest.mark.parametrize('constraint, result', [
    ('== 2.7', ['2.7']),
    ('== 2.7.*', ['2.7']),
    ('== 2.7.12', ['2.7']),
    ('== 2.*, >= 2.6', ['2.6', '2.7']),
    ('== 3.0', ['3.0']),
    ('== 3', ['3.0']),
])
def test_matching_version(constraint, result):
    assert parse_poetry_version_constraint(constraint) == v(result)


def test_greater_than(fix_max_python_3_version):
    fix_max_python_3_version(8)
    assert parse_poetry_version_constraint('>= 3.6') == v([
        '3.6', '3.7', '3.8',
    ])


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
def test_greater_than_with_exceptions(
    fix_max_python_3_version, constraint, result
):
    fix_max_python_3_version(3)
    assert parse_poetry_version_constraint(constraint) == v(result)


def test_multiple_greater_than(fix_max_python_3_version):
    fix_max_python_3_version(7)
    assert parse_poetry_version_constraint('>= 2.7, >= 3.6') == v([
        '3.6', '3.7',
    ])


@pytest.mark.parametrize('constraint, result', [
    ('> 2, < 3.1', ['3.0']),
    ('> 2.6, < 3', ['2.7']),
    ('> 2.7.12, < 3', ['2.7']),
    ('> 2.7.12, < 3.0', ['2.7']),
    ('> 2.7.12, < 3.1', ['2.7', '3.0']),
    ('> 2.7.12, < 3.0.1', ['2.7', '3.0']),
])
def test_exclusive_ordering(constraint, result):
    assert parse_poetry_version_constraint(constraint) == v(result)


@pytest.mark.parametrize('op', ['^', '~', '>=', '<=', '>', '<'])
def test_unexpected_dot_star(fix_max_python_3_version, capsys, op):
    fix_max_python_3_version(7)
    assert parse_poetry_version_constraint(f'{op} 3.6.*', 'version') is None
    assert (
        'Bad version specifier in pyproject.toml:'
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
    assert parse_poetry_version_constraint(specifier, 'version') is None
    assert (
        f'Bad version specifier in pyproject.toml: {specifier}'
        in capsys.readouterr().err
    )


@pytest.mark.parametrize("spec, comma, space, caret_tilde", [
    (">=3.8", ", ", "", False),
    (">= 3.8", ", ", " ", False),
    (">=2.7,!=3.0", ",", "", False),
    ("^3.8", ", ", "", True),
    ("^ 3.8", ", ", " ", True),
    ("~3.8", ", ", "", True),
])
def test_detect_style(spec, comma, space, caret_tilde):
    assert detect_poetry_version_spec_style(spec) == dict(
        comma=comma, space=space, prefer_caret_tilde=caret_tilde,
    )


@pytest.mark.parametrize('versions, expected', [
    (['2.7'], '2.7.*'),
    (['3.6', '3.7'], '>=3.6'),
    (['2.7', '3.4', '3.5', '3.6', '3.7'],
     '>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*'),
    (['3.7'], '>=3.7'),
    (['3.5', '3.6'], '>=3.5, <3.7'),
    # not very realistic corner case
    (['2.5', '2.6'], '>=2.5, <2.7'),
])
def test_compute_python_requires(versions, expected, fix_max_python_3_version):
    fix_max_python_3_version(7)
    result = compute_poetry_spec(v(versions), prefer_caret_tilde=False)
    assert result == expected
    assert parse_poetry_version_constraint(result) == v(versions)


@pytest.mark.parametrize('versions, expected', [
    (['2.7'], '~2.7'),
    (['3.6', '3.7'], '^3.6'),
    (['2.7', '3.4', '3.5', '3.6', '3.7'],
     '>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*'),
    (['3.7'], '^3.7'),
    (['3.5', '3.6'], '>=3.5, <3.7'),
    # not very realistic corner case
    (['2.5', '2.6'], '>=2.5, <2.7'),
])
def test_compute_python_requires_with_caret_and_tilde(
    versions, expected, fix_max_python_3_version
):
    fix_max_python_3_version(7)
    result = compute_poetry_spec(v(versions))
    assert result == expected
    assert parse_poetry_version_constraint(result) == v(versions)
