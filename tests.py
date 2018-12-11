import ast

import pytest

import check_python_versions as cpv


def test_get_versions_from_classifiers():
    assert cpv.get_versions_from_classifiers([
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
    ]) == ['2.7', '3.6', '3.7', 'PyPy']


def test_get_versions_from_classifiers_major_only():
    assert cpv.get_versions_from_classifiers([
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ]) == ['2', '3']


def test_get_versions_from_classifiers_with_only_suffix():
    assert cpv.get_versions_from_classifiers([
        'Programming Language :: Python :: 2 :: Only',
    ]) == ['2']


def test_get_versions_from_classifiers_with_trailing_whitespace():
    # I was surprised too that this is allowed!
    assert cpv.get_versions_from_classifiers([
        'Programming Language :: Python :: 3.6 ',
    ]) == ['3.6']


def test_find_call_kwarg_in_ast():
    tree = ast.parse('foo(bar="foo")')
    ast.dump(tree)
    node = cpv.find_call_kwarg_in_ast(tree, 'foo', 'bar')
    assert isinstance(node, ast.Str)
    assert node.s == "foo"


@pytest.mark.parametrize('code, expected', [
    ('"hi"', "hi"),
    ('"hi\\n"', "hi\n"),
    ('["a", "b"]', ["a", "b"]),
    ('("a", "b")', ("a", "b")),
    ('"-".join(["a", "b"])', "a-b"),
])
def test_eval_ast_node(code, expected):
    tree = ast.parse(f'foo(bar={code})')
    node = cpv.find_call_kwarg_in_ast(tree, 'foo', 'bar')
    assert node is not None
    assert cpv.eval_ast_node(node, 'bar') == expected


def test_parse_python_requires_empty():
    assert cpv.parse_python_requires('') == []


def test_parse_python_requires_greater_than(monkeypatch):
    monkeypatch.setattr(cpv, 'CURRENT_PYTHON_3_VERSION', 8)
    assert cpv.parse_python_requires('>= 3.6') == ['3.6', '3.7', '3.8']


def test_parse_python_requires_greater_than_with_exceptions(monkeypatch):
    monkeypatch.setattr(cpv, 'CURRENT_PYTHON_3_VERSION', 3)
    assert cpv.parse_python_requires('>= 2.7, != 3.0.*, != 3.1.*') == [
        '2.7', '3.2', '3.3'
    ]


@pytest.mark.parametrize('s, expected', [
    ('', []),
    ('py36,py37', ['py36', 'py37']),
    ('py36, py37', ['py36', 'py37']),
    ('\n  py36,\n  py37', ['py36', 'py37']),
    ('py3{6,7},pypy', ['py36', 'py37', 'pypy']),
])
def test_parse_envlist(s, expected):
    assert cpv.parse_envlist(s) == expected


@pytest.mark.parametrize('s, expected', [
    ('', ['']),
    ('py36', ['py36']),
    ('py3{6,7}', ['py36', 'py37']),
    ('py3{6,7}-lint', ['py36-lint', 'py37-lint']),
    ('py3{6,7}{,-lint}', ['py36', 'py36-lint', 'py37', 'py37-lint']),
])
def test_brace_expand(s, expected):
    assert cpv.brace_expand(s) == expected


@pytest.mark.parametrize('s, expected', [
    ('py36', '3.6'),
    ('py37-lint', '3.7'),
    ('pypy', 'PyPy'),
    ('pypy3', 'PyPy3'),
])
def test_tox_env_to_py_version(s, expected):
    assert cpv.tox_env_to_py_version(s) == expected


@pytest.mark.parametrize('s, expected', [
    (3.6, '3.6'),
    ('3.7', '3.7'),
    ('pypy', 'PyPy'),
    ('pypy2', 'PyPy'),
    ('pypy2.7', 'PyPy'),
    ('pypy2.7-5.10.0', 'PyPy'),
    ('pypy3', 'PyPy3'),
    ('pypy3.5', 'PyPy3'),
    ('pypy3.5-5.10.1', 'PyPy3'),
    ('3.7-dev', '3.7-dev'),
    ('nightly', 'nightly'),
])
def test_travis_normalize_py_version(s, expected):
    assert cpv.travis_normalize_py_version(s) == expected


@pytest.mark.parametrize('s, expected', [
    ('37', '3.7'),
    ('c:\\python34', '3.4'),
    ('C:\\Python27\\', '2.7'),
    ('C:\\Python27-x64', '2.7'),
    ('C:\\PYTHON34-X64', '3.4'),
])
def test_appveyor_normalize_py_version(s, expected):
    assert cpv.appveyor_normalize_py_version(s) == expected


def test_important():
    assert cpv.important({
        '2.7', '3.4', '3.7-dev', 'nightly', 'PyPy3', 'Jython'
    }) == {'2.7', '3.4'}


def test_parse_expect():
    assert cpv.parse_expect('2.7,3.4-3.6') == ['2.7', '3.4', '3.5', '3.6']
