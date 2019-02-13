import ast
import os
import sys
import textwrap

import pytest

import check_python_versions as cpv


needs_pyyaml = pytest.mark.skipIf(cpv.yaml is None, "PyYAML not installed")


def test_pipe():
    assert cpv.pipe('echo', 'hi') == 'hi\n'


def test_get_supported_python_versions(tmp_path):
    (tmp_path / "setup.py").write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    assert cpv.get_supported_python_versions(tmp_path) == ['2.7', '3.6']


def test_get_supported_python_versions_computed(tmp_path):
    (tmp_path / "setup.py").write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: %s' % v
                for v in ['2.7', '3.7']
            ],
        )
    """))
    assert cpv.get_supported_python_versions(tmp_path) == ['2.7', '3.7']


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


def test_get_python_requires(tmp_path, monkeypatch):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>= 3.6',
        )
    """))
    monkeypatch.setattr(cpv, 'CURRENT_PYTHON_3_VERSION', 7)
    assert cpv.get_python_requires(setup_py) == ['3.6', '3.7']


def test_get_python_requires_not_specified(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
        )
    """))
    assert cpv.get_python_requires(setup_py) is None
    assert capsys.readouterr().err == ''


def test_get_setup_py_keyword_syntax_error(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
        # uh do I need to close parens?  what if I forget? ;)
    """))
    assert cpv.get_setup_py_keyword(setup_py, 'name') is None
    assert 'Could not parse' in capsys.readouterr().err


def test_find_call_kwarg_in_ast():
    tree = ast.parse('foo(bar="foo")')
    ast.dump(tree)
    node = cpv.find_call_kwarg_in_ast(tree, 'foo', 'bar')
    assert isinstance(node, ast.Str)
    assert node.s == "foo"


def test_find_call_kwarg_in_ast_no_arg(capsys):
    tree = ast.parse('foo(baz="foo")')
    ast.dump(tree)
    node = cpv.find_call_kwarg_in_ast(tree, 'foo', 'bar')
    assert node is None
    assert capsys.readouterr().err == ''


def test_find_call_kwarg_in_ast_no_call(capsys):
    tree = ast.parse('fooo(bar="foo")')
    ast.dump(tree)
    node = cpv.find_call_kwarg_in_ast(tree, 'foo', 'bar')
    assert node is None
    assert 'Could not find foo() call in setup.py' in capsys.readouterr().err


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


@pytest.mark.parametrize('code', [
    '[2 * 2]',
    '"".join([2 * 2])',
])
def test_eval_ast_node_failures(code, capsys):
    tree = ast.parse(f'foo(bar={code})')
    node = cpv.find_call_kwarg_in_ast(tree, 'foo', 'bar')
    assert cpv.eval_ast_node(node, 'bar') is None
    assert 'Non-literal bar= passed to setup()' in capsys.readouterr().err


@pytest.mark.parametrize('constraint, result', [
    ('~= 2.7', ['2.7']),
    ('~= 2.7.12', ['2.7']),
])
def test_parse_python_requires_approximately(constraint, result):
    assert cpv.parse_python_requires(constraint) == result


def test_parse_python_requires_approximately_not_enough_dots(capsys):
    assert cpv.parse_python_requires('~= 2') is None
    assert (
        'Bad python_requires specifier: ~= 2'
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
    assert cpv.parse_python_requires(constraint) == result


def test_parse_python_requires_greater_than(monkeypatch):
    monkeypatch.setattr(cpv, 'CURRENT_PYTHON_3_VERSION', 8)
    assert cpv.parse_python_requires('>= 3.6') == ['3.6', '3.7', '3.8']


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
    monkeypatch, constraint, result
):
    monkeypatch.setattr(cpv, 'CURRENT_PYTHON_3_VERSION', 3)
    assert cpv.parse_python_requires(constraint) == result


def test_parse_python_requires_multiple_greater_than(monkeypatch):
    monkeypatch.setattr(cpv, 'CURRENT_PYTHON_3_VERSION', 7)
    assert cpv.parse_python_requires('>= 2.7, >= 3.6') == ['3.6', '3.7']


@pytest.mark.parametrize('constraint, result', [
    ('> 2, < 3.1', ['3.0']),
    ('> 2.6, < 3', ['2.7']),
    ('> 2.7.12, < 3', ['2.7']),
    ('> 2.7.12, < 3.0', ['2.7']),
    ('> 2.7.12, < 3.1', ['2.7', '3.0']),
    ('> 2.7.12, < 3.0.1', ['2.7', '3.0']),
])
def test_parse_python_exclusive_ordering(constraint, result):
    assert cpv.parse_python_requires(constraint) == result


@pytest.mark.parametrize('constraint, result', [
    ('=== 2.7', ['2.7']),
    ('=== 2.7.12', ['2.7']),
    ('=== 3', []),
])
def test_parse_python_requires_arbitrary_version(constraint, result):
    assert cpv.parse_python_requires(constraint) == result


@pytest.mark.parametrize('op', ['~=', '>=', '<=', '>', '<', '==='])
def test_parse_python_requires_unexpected_dot_star(monkeypatch, capsys, op):
    monkeypatch.setattr(cpv, 'CURRENT_PYTHON_3_VERSION', 7)
    assert cpv.parse_python_requires(f'{op} 3.6.*') is None
    assert (
        f'Bad python_requires specifier: {op} 3.6.* ({op} does not allow a .*)'
        in capsys.readouterr().err
    )


@pytest.mark.parametrize('specifier', [
    '%= 42',
    '== nobody.knows',
    '!= *.*.*',
    'xyzzy',
])
def test_parse_python_requires_syntax_errors(capsys, specifier):
    assert cpv.parse_python_requires(specifier) is None
    assert (
        f'Bad python_requires specifier: {specifier}'
        in capsys.readouterr().err
    )


def test_get_tox_ini_python_versions(tmp_path):
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        [tox]
        envlist = py27,py36,py27-docs
    """))
    assert cpv.get_tox_ini_python_versions(tox_ini) == ['2.7', '3.6']


def test_get_tox_ini_python_versions_no_tox_ini(tmp_path):
    tox_ini = tmp_path / "tox.ini"
    assert cpv.get_tox_ini_python_versions(tox_ini) == []


def test_get_tox_ini_python_versions_syntax_error(tmp_path):
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        ...
    """))
    assert cpv.get_tox_ini_python_versions(tox_ini) == []


def test_get_tox_ini_python_versions_no_tox_section(tmp_path):
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        [flake8]
        source = foo
    """))
    assert cpv.get_tox_ini_python_versions(tox_ini) == []


def test_get_tox_ini_python_versions_no_tox_envlist(tmp_path):
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        [tox]
        minversion = 3.4.0
    """))
    assert cpv.get_tox_ini_python_versions(tox_ini) == []


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
    ('flake8', 'flake8'),
])
def test_tox_env_to_py_version(s, expected):
    assert cpv.tox_env_to_py_version(s) == expected


@needs_pyyaml
def test_get_travis_yml_python_versions(tmp_path):
    travis_yml = tmp_path / ".travis.yml"
    travis_yml.write_text(textwrap.dedent("""\
        python:
          - 2.7
          - 3.6
        matrix:
          include:
            - python: 3.7
        jobs:
          include:
            - python: 3.4
        env:
          - TOXENV=py35-docs
    """))
    assert cpv.get_travis_yml_python_versions(travis_yml) == [
        '2.7', '3.4', '3.5', '3.6', '3.7',
    ]


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


@needs_pyyaml
def test_get_appveyor_yml_python_versions(tmp_path):
    appveyor_yml = tmp_path / "appveyor.yml"
    appveyor_yml.write_text(textwrap.dedent("""\
        environment:
          matrix:
            - PYTHON: c:\\python27
            - PYTHON: c:\\python27-x64
            - PYTHON: c:\\python36
            - PYTHON: c:\\python36-x64
    """))
    assert cpv.get_appveyor_yml_python_versions(appveyor_yml) == [
        '2.7', '3.6',
    ]


@needs_pyyaml
def test_get_appveyor_yml_python_versions_using_toxenv(tmp_path):
    appveyor_yml = tmp_path / "appveyor.yml"
    appveyor_yml.write_text(textwrap.dedent("""\
        environment:
          matrix:
            - TOXENV: py27
            - TOXENV: py37
    """))
    assert cpv.get_appveyor_yml_python_versions(appveyor_yml) == [
        '2.7', '3.7',
    ]


@pytest.mark.parametrize('s, expected', [
    ('37', '3.7'),
    ('c:\\python34', '3.4'),
    ('C:\\Python27\\', '2.7'),
    ('C:\\Python27-x64', '2.7'),
    ('C:\\PYTHON34-X64', '3.4'),
])
def test_appveyor_normalize_py_version(s, expected):
    assert cpv.appveyor_normalize_py_version(s) == expected


def test_get_manylinux_python_versions(tmp_path):
    manylinux_install_sh = tmp_path / ".manylinux-install.sh"
    manylinux_install_sh.write_text(textwrap.dedent(r"""
        #!/usr/bin/env bash

        set -e -x

        # Compile wheels
        for PYBIN in /opt/python/*/bin; do
            if [[ "${PYBIN}" == *"cp27"* ]] || \
               [[ "${PYBIN}" == *"cp34"* ]] || \
               [[ "${PYBIN}" == *"cp35"* ]] || \
               [[ "${PYBIN}" == *"cp36"* ]] || \
               [[ "${PYBIN}" == *"cp37"* ]]; then
                "${PYBIN}/pip" install -e /io/
                "${PYBIN}/pip" wheel /io/ -w wheelhouse/
                   rm -rf /io/build /io/*.egg-info
            fi
        done

        # Bundle external shared libraries into the wheels
        for whl in wheelhouse/zope.interface*.whl; do
            auditwheel repair "$whl" -w /io/wheelhouse/
        done
    """.lstrip('\n')))
    assert cpv.get_manylinux_python_versions(manylinux_install_sh) == [
        '2.7', '3.4', '3.5', '3.6', '3.7',
    ]


def test_important():
    assert cpv.important({
        '2.7', '3.4', '3.7-dev', 'nightly', 'PyPy3', 'Jython'
    }) == {'2.7', '3.4'}


def test_parse_expect():
    assert cpv.parse_expect('2.7,3.4-3.6') == ['2.7', '3.4', '3.5', '3.6']


def test_parse_expect_bad_range():
    with pytest.raises(ValueError, match=r'bad range: 2\.7-3\.4 \(2 != 3\)'):
        cpv.parse_expect('2.7-3.4')


def test_parse_expect_bad_number():
    with pytest.raises(ValueError):
        cpv.parse_expect('2.x')


def test_parse_expect_too_few():
    with pytest.raises(ValueError):
        cpv.parse_expect('2')


def test_parse_expect_too_many_dots():
    with pytest.raises(ValueError):
        cpv.parse_expect('2.7.1')


def test_is_package(tmp_path):
    (tmp_path / "setup.py").write_text("")
    assert cpv.is_package(tmp_path)


def test_is_package_no_setup_py(tmp_path):
    assert not cpv.is_package(tmp_path)


def test_check_not_a_directory(tmp_path, capsys):
    assert cpv.check(tmp_path / "xyzzy") is None
    assert capsys.readouterr().out == 'not a directory\n'


def test_check_not_a_package(tmp_path, capsys):
    assert cpv.check(tmp_path) is None
    assert capsys.readouterr().out == 'no setup.py -- not a Python package?\n'


def test_check_unknown(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
        )
    """))
    assert cpv.check(tmp_path) is True
    assert capsys.readouterr().out == textwrap.dedent("""\
        setup.py says:              (empty)
    """)


def test_check_minimal(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    assert cpv.check(tmp_path) is True
    assert capsys.readouterr().out == textwrap.dedent("""\
        setup.py says:              2.7, 3.6
    """)


def test_check_mismatch(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    tox_ini = tmp_path / "tox.ini"
    tox_ini.write_text(textwrap.dedent("""\
        [tox]
        envlist = py27
    """))
    assert cpv.check(tmp_path) is False
    assert capsys.readouterr().out == textwrap.dedent("""\
        setup.py says:              2.7, 3.6
        tox.ini says:               2.7
    """)


def test_check_expectation(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    assert cpv.check(tmp_path, expect=['2.7', '3.6', '3.7']) is False
    assert capsys.readouterr().out == textwrap.dedent("""\
        setup.py says:              2.7, 3.6
        expected:                   2.7, 3.6, 3.7
    """)


def test_main_help(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['check-python-versions', '--help'])
    with pytest.raises(SystemExit):
        cpv.main()


@pytest.mark.parametrize('arg', [
    'xyzzy',
    '1,2,3',
    '2.x',
    '1.2.3',
    '2.7-3.6',
])
def test_main_expect_error_handling(monkeypatch, arg, capsys):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions', '--expect', arg,
    ])
    with pytest.raises(SystemExit):
        cpv.main()
    assert f'bad value for --expect: {arg}' in capsys.readouterr().err


def test_main_here(monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions',
    ])
    cpv.main()
    assert 'mismatch' not in capsys.readouterr().out


def test_main_skip_non_packages(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions', '--skip-non-packages', str(tmp_path),
    ])
    cpv.main()
    assert capsys.readouterr().out == ''


def test_main_single(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions',
        str(tmp_path / "a"),
    ])
    with pytest.raises(SystemExit) as exc_info:
        cpv.main()
    assert (
        capsys.readouterr().out + str(exc_info.value) + '\n'
    ).replace(str(tmp_path), 'tmp') == textwrap.dedent("""\
        not a directory

        mismatch!
    """)


def test_main_multiple(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions',
        str(tmp_path / "a"),
        str(tmp_path / "b"),
    ])
    with pytest.raises(SystemExit) as exc_info:
        cpv.main()
    assert (
        capsys.readouterr().out + str(exc_info.value) + '\n'
    ).replace(str(tmp_path) + os.path.sep, 'tmp/') == textwrap.dedent("""\
        tmp/a:

        not a directory


        tmp/b:

        not a directory


        mismatch in tmp/a tmp/b!
    """)


def test_main_multiple_ok(monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions', '.', '.',
    ])
    cpv.main()
    assert (
        capsys.readouterr().out.endswith('\n\nall ok!\n')
    )
