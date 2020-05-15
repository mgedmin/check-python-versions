import ast
import textwrap
from io import StringIO

import pytest

from check_python_versions.parsers.python import (
    compute_python_requires,
    eval_ast_node,
    find_call_kwarg_in_ast,
    get_python_requires,
    get_setup_py_keyword,
    get_supported_python_versions,
    get_versions_from_classifiers,
    parse_python_requires,
    to_literal,
    update_call_arg_in_source,
    update_classifiers,
    update_python_requires,
    update_supported_python_versions,
)


def test_get_supported_python_versions(tmp_path):
    filename = tmp_path / "setup.py"
    filename.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: 2.7',
                'Programming Language :: Python :: 3.6',
            ],
        )
    """))
    assert get_supported_python_versions(filename) == ['2.7', '3.6']


def test_get_supported_python_versions_computed(tmp_path):
    filename = tmp_path / "setup.py"
    filename.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: %s' % v
                for v in ['2.7', '3.7']
            ],
        )
    """))
    assert get_supported_python_versions(filename) == ['2.7', '3.7']


def test_get_supported_python_versions_string(tmp_path, capsys):
    filename = tmp_path / "setup.py"
    filename.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers='''
                Programming Language :: Python :: 2.7
                Programming Language :: Python :: 3.6
            ''',
        )
    """))
    assert get_supported_python_versions(filename) == []
    assert (
        "The value passed to setup(classifiers=...) is not a list"
        in capsys.readouterr().err
    )


def test_get_supported_python_versions_from_file_object_cannot_run_setup_py():
    fp = StringIO(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: %s' % v
                for v in ['2.7', '3.7']
            ],
        )
    """))
    fp.name = 'setup.py'
    assert get_supported_python_versions(fp) == []


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
    ]) == ['2.7', '3.6', '3.7', 'PyPy']


def test_get_versions_from_classifiers_major_only():
    assert get_versions_from_classifiers([
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ]) == ['2', '3']


def test_get_versions_from_classifiers_with_only_suffix():
    assert get_versions_from_classifiers([
        'Programming Language :: Python :: 2 :: Only',
    ]) == ['2']


def test_get_versions_from_classifiers_with_trailing_whitespace():
    # I was surprised too that this is allowed!
    assert get_versions_from_classifiers([
        'Programming Language :: Python :: 3.6 ',
    ]) == ['3.6']


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
    ], ['2.7', '3.7']) == [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
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
    ], ['3.6', '3.7']) == [
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
    ], ['2.7', '3.7']) == [
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
    ], ['2.7', '3.7']) == [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.7',
    ]


def test_update_supported_python_versions(tmp_path, capsys):
    filename = tmp_path / "setup.py"
    filename.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers=[
                'Programming Language :: Python :: %s' % v
                for v in ['2.7', '3.7']
            ],
        )
    """))
    assert update_supported_python_versions(filename, ['3.7', '3.8']) is None
    assert (
        'Non-literal classifiers= passed to setup()'
        in capsys.readouterr().err
    )


def test_update_supported_python_versions_not_a_list(tmp_path, capsys):
    filename = tmp_path / "setup.py"
    filename.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            classifiers='''
                Programming Language :: Python :: 2.7
                Programming Language :: Python :: 3.6
            ''',
        )
    """))
    assert update_supported_python_versions(filename, ['3.7', '3.8']) is None
    assert (
        'The value passed to setup(classifiers=...) is not a list'
        in capsys.readouterr().err
    )


def test_get_python_requires(tmp_path, fix_max_python_3_version):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>= 3.6',
        )
    """))
    fix_max_python_3_version(7)
    assert get_python_requires(setup_py) == ['3.6', '3.7']


def test_get_python_requires_not_specified(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
        )
    """))
    assert get_python_requires(setup_py) is None
    assert capsys.readouterr().err == ''


def test_get_python_requires_not_a_string(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires=['>= 3.6'],
        )
    """))
    assert get_python_requires(setup_py) is None
    assert (
        'The value passed to setup(python_requires=...) is not a string'
        in capsys.readouterr().err
    )


def test_get_setup_py_keyword_syntax_error(tmp_path, capsys):
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
        # uh do I need to close parens?  what if I forget? ;)
    """))
    assert get_setup_py_keyword(setup_py, 'name') is None
    assert 'Could not parse' in capsys.readouterr().err


def test_update_python_requires(tmp_path, fix_max_python_3_version):
    fix_max_python_3_version(7)
    filename = tmp_path / "setup.py"
    filename.write_text(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>= 3.4',
        )
    """))
    result = update_python_requires(filename, ['3.5', '3.6', '3.7'])
    assert "".join(result) == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>=3.5',
        )
    """)


def test_update_python_requires_file_object(fix_max_python_3_version):
    fix_max_python_3_version(7)
    fp = StringIO(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>= 3.4',
        )
    """))
    fp.name = "setup.py"
    result = update_python_requires(fp, ['3.5', '3.6', '3.7'])
    assert "".join(result) == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>=3.5',
        )
    """)


def test_update_python_requires_when_missing(capsys):
    fp = StringIO(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
        )
    """))
    fp.name = "setup.py"
    result = update_python_requires(fp, ['3.5', '3.6', '3.7'])
    assert result is None
    assert capsys.readouterr().err == ""


def test_update_python_requires_preserves_style(fix_max_python_3_version):
    fix_max_python_3_version(2)
    fp = StringIO(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>=2.7,!=3.0.*',
        )
    """))
    fp.name = "setup.py"
    result = update_python_requires(fp, ['2.7', '3.2'])
    assert "".join(result) == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires='>=2.7,!=3.0.*,!=3.1.*',
        )
    """)


def test_update_python_requires_multiline(fix_max_python_3_version):
    fix_max_python_3_version(2)
    fp = StringIO(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires=', '.join([
                '>=2.7',
                '!=3.0.*',
            ]),
        )
    """))
    fp.name = "setup.py"
    result = update_python_requires(fp, ['2.7', '3.2'])
    assert "".join(result) == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires=', '.join([
                '>=2.7',
                '!=3.0.*',
                '!=3.1.*',
            ]),
        )
    """)


def test_update_python_requires_multiline_variations(fix_max_python_3_version):
    fix_max_python_3_version(2)
    fp = StringIO(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires=",".join([
                ">=2.7",
                "!=3.0.*",
            ]),
        )
    """))
    fp.name = "setup.py"
    result = update_python_requires(fp, ['2.7', '3.2'])
    assert "".join(result) == textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires=",".join([
                ">=2.7",
                "!=3.0.*",
                "!=3.1.*",
            ]),
        )
    """)


def test_update_python_requires_multiline_error(capsys):
    fp = StringIO(textwrap.dedent("""\
        from setuptools import setup
        setup(
            name='foo',
            python_requires=', '.join([
                '>=2.7',
                '!=3.0.*']),
        )
    """))
    fp.name = "setup.py"
    result = update_python_requires(fp, ['2.7', '3.2'])
    assert result == fp.getvalue().splitlines(True)
    assert (
        "Did not understand python_requires= formatting in setup() call"
        in capsys.readouterr().err
    )


def test_find_call_kwarg_in_ast():
    tree = ast.parse('foo(bar="foo")')
    ast.dump(tree)
    node = find_call_kwarg_in_ast(tree, 'foo', 'bar')
    assert isinstance(node, ast.Str)
    assert node.s == "foo"


def test_find_call_kwarg_in_ast_no_arg(capsys):
    tree = ast.parse('foo(baz="foo")')
    ast.dump(tree)
    node = find_call_kwarg_in_ast(tree, 'foo', 'bar')
    assert node is None
    assert capsys.readouterr().err == ''


def test_find_call_kwarg_in_ast_no_call(capsys):
    tree = ast.parse('fooo(bar="foo")')
    ast.dump(tree)
    node = find_call_kwarg_in_ast(tree, 'foo', 'bar')
    assert node is None
    assert 'Could not find foo() call in setup.py' in capsys.readouterr().err


@pytest.mark.parametrize('code, expected', [
    ('"hi"', "hi"),
    ('"hi\\n"', "hi\n"),
    ('["a", "b"]', ["a", "b"]),
    ('("a", "b")', ("a", "b")),
    ('"-".join(["a", "b"])', "a-b"),
    ('["a", "b"] + ["c"]', ["a", "b", "c"]),
    ('["a", "b"] + extra', ["a", "b"]),
    ('extra + ["a", "b"]', ["a", "b"]),
    ('["a", "b", extra]', ["a", "b"]),
])
def test_eval_ast_node(code, expected):
    tree = ast.parse(f'foo(bar={code})')
    node = find_call_kwarg_in_ast(tree, 'foo', 'bar')
    assert node is not None
    assert eval_ast_node(node, 'bar') == expected


@pytest.mark.parametrize('code, expected', [
    ('["a", "b", "c" if condition else "d", "e", 42]', ["a", "b", "e"]),
])
def test_eval_ast_node_skips_computed_values(code, expected, capsys):
    tree = ast.parse(f'foo(bar={code})')
    node = find_call_kwarg_in_ast(tree, 'foo', 'bar')
    assert node is not None
    assert eval_ast_node(node, 'bar') == expected
    assert (
        'Non-literal bar= passed to setup(), skipping some values'
        in capsys.readouterr().err
    )


@pytest.mark.parametrize('code', [
    '[2 * 2]',
    '"".join([2 * 2])',
    'extra + more',
])
def test_eval_ast_node_failures(code, capsys):
    tree = ast.parse(f'foo(bar={code})')
    node = find_call_kwarg_in_ast(tree, 'foo', 'bar')
    assert eval_ast_node(node, 'bar') is None
    assert 'Non-literal bar= passed to setup()' in capsys.readouterr().err


@pytest.mark.parametrize('code', [
    '["a", "b"] + "c"',
])
def test_eval_ast_node_type_mismatch(code, capsys):
    tree = ast.parse(f'foo(bar={code})')
    node = find_call_kwarg_in_ast(tree, 'foo', 'bar')
    assert eval_ast_node(node, 'bar') is None
    assert (
        'bar= is computed by adding incompatible types: list and str'
        in capsys.readouterr().err
    )


def test_to_literal():
    assert to_literal("blah") == '"blah"'
    assert to_literal("blah", "'") == "'blah'"


def test_to_literal_embedded_quote():
    assert to_literal(
        "Environment :: Handhelds/PDA's"
    ) == '"Environment :: Handhelds/PDA\'s"'
    assert to_literal(
        "Environment :: Handhelds/PDA's", "'"
    ) == '"Environment :: Handhelds/PDA\'s"'


def test_to_literal_all_the_classifiers():
    with open('CLASSIFIERS') as f:
        for line in f:
            classifier = line.strip()
            literal = to_literal(classifier)
            assert ast.literal_eval(literal) == classifier


def test_update_call_arg_in_source_string():
    source_lines = textwrap.dedent("""\
        setup(
            foo=1,
            bar="x",
            baz=2,
        )
    """).splitlines(True)
    result = update_call_arg_in_source(source_lines, "setup", "bar", "y")
    assert "".join(result) == textwrap.dedent("""\
        setup(
            foo=1,
            bar="y",
            baz=2,
        )
    """)


def test_update_call_arg_in_source_string_spaces():
    # This is against PEP-8 but there are setup.py files out there that do
    # not follow PEP-8.
    source_lines = textwrap.dedent("""\
        setup (
            foo = 1,
            bar = 'x',
            baz = 2,
        )
    """).splitlines(True)
    result = update_call_arg_in_source(source_lines, "setup", "bar", "y")
    assert "".join(result) == textwrap.dedent("""\
        setup (
            foo = 1,
            bar = 'y',
            baz = 2,
        )
    """)


def test_update_call_arg_in_source_list():
    source_lines = textwrap.dedent("""\
        setup(
            foo=1,
            bar=[
                "a",
                "b",

                r"c",
            ],
            baz=2,
        )
    """).splitlines(True)
    result = update_call_arg_in_source(source_lines, "setup", "bar",
                                       ["x", "y"])
    assert "".join(result) == textwrap.dedent("""\
        setup(
            foo=1,
            bar=[
                "x",
                "y",
            ],
            baz=2,
        )
    """)


def test_update_call_arg_in_source_preserves_indent_and_quote_style():
    source_lines = textwrap.dedent("""\
        setup(foo=1,
              bar=[
                  'a',
                  'b',
                  'c',
              ],
        )
    """).splitlines(True)
    result = update_call_arg_in_source(source_lines, "setup", "bar",
                                       ["x", "y"])
    assert "".join(result) == textwrap.dedent("""\
        setup(foo=1,
              bar=[
                  'x',
                  'y',
              ],
        )
    """)


def test_update_call_arg_in_source_fixes_closing_bracket():
    source_lines = textwrap.dedent("""\
        setup(foo=1,
              bar=[
                  'a',
                  'b',
                  'c'],
              baz=2,
        )
    """).splitlines(True)
    result = update_call_arg_in_source(source_lines, "setup", "bar",
                                       ["x", "y"])
    assert "".join(result) == textwrap.dedent("""\
        setup(foo=1,
              bar=[
                  'x',
                  'y',
              ],
              baz=2,
        )
    """)


def test_update_call_arg_in_source_fixes_opening_bracket():
    source_lines = textwrap.dedent("""\
        setup(foo=1,
              bar=['a',
                   'b',
                   'c'],
              baz=2,
        )
    """).splitlines(True)
    result = update_call_arg_in_source(source_lines, "setup", "bar",
                                       ["x", "y"])
    assert "".join(result) == textwrap.dedent("""\
        setup(foo=1,
              bar=[
                  'x',
                  'y',
              ],
              baz=2,
        )
    """)


def test_update_call_arg_in_source_handles_empty_list():
    source_lines = textwrap.dedent("""\
        setup(foo=1,
              bar=[],
              baz=2,
        )
    """).splitlines(True)
    result = update_call_arg_in_source(source_lines, "setup", "bar",
                                       ["x", "y"])
    assert "".join(result) == textwrap.dedent("""\
        setup(foo=1,
              bar=[
                  "x",
                  "y",
              ],
              baz=2,
        )
    """)


def test_update_call_arg_in_source_no_function_call(capsys):
    source_lines = textwrap.dedent("""\
    """).splitlines(True)
    result = update_call_arg_in_source(source_lines, "setup", "bar",
                                       ["x", "y"])
    assert result == source_lines
    assert "Did not find setup() call" in capsys.readouterr().err


def test_update_call_arg_in_source_no_keyword(capsys):
    source_lines = textwrap.dedent("""\
        setup()
    """).splitlines(True)
    result = update_call_arg_in_source(source_lines, "setup", "bar",
                                       ["x", "y"])
    assert result == source_lines
    assert (
        "Did not find bar= argument in setup() call"
        in capsys.readouterr().err
    )


def test_update_call_arg_in_source_too_complicated(capsys):
    source_lines = textwrap.dedent("""\
        setup(
          bar=bar)
    """).splitlines(True)
    result = update_call_arg_in_source(source_lines, "setup", "bar",
                                       ["x", "y"])
    assert result == source_lines
    assert (
        "Did not understand bar= formatting in setup() call"
        in capsys.readouterr().err
    )


@pytest.mark.parametrize('constraint, result', [
    ('~= 2.7', ['2.7']),
    ('~= 2.7.12', ['2.7']),
])
def test_parse_python_requires_approximately(constraint, result):
    assert parse_python_requires(constraint) == result


def test_parse_python_requires_approximately_not_enough_dots(capsys):
    assert parse_python_requires('~= 2') is None
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
    assert parse_python_requires(constraint) == result


def test_parse_python_requires_greater_than(fix_max_python_3_version):
    fix_max_python_3_version(8)
    assert parse_python_requires('>= 3.6') == ['3.6', '3.7', '3.8']


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
    assert parse_python_requires(constraint) == result


def test_parse_python_requires_multiple_greater_than(fix_max_python_3_version):
    fix_max_python_3_version(7)
    assert parse_python_requires('>= 2.7, >= 3.6') == ['3.6', '3.7']


@pytest.mark.parametrize('constraint, result', [
    ('> 2, < 3.1', ['3.0']),
    ('> 2.6, < 3', ['2.7']),
    ('> 2.7.12, < 3', ['2.7']),
    ('> 2.7.12, < 3.0', ['2.7']),
    ('> 2.7.12, < 3.1', ['2.7', '3.0']),
    ('> 2.7.12, < 3.0.1', ['2.7', '3.0']),
])
def test_parse_python_requires_exclusive_ordering(constraint, result):
    assert parse_python_requires(constraint) == result


@pytest.mark.parametrize('constraint, result', [
    ('=== 2.7', ['2.7']),
    ('=== 2.7.12', ['2.7']),
    ('=== 3', []),
])
def test_parse_python_requires_arbitrary_version(constraint, result):
    assert parse_python_requires(constraint) == result


@pytest.mark.parametrize('op', ['~=', '>=', '<=', '>', '<', '==='])
def test_parse_python_requires_unexpected_dot_star(fix_max_python_3_version,
                                                   capsys, op):
    fix_max_python_3_version(7)
    assert parse_python_requires(f'{op} 3.6.*') is None
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
    assert parse_python_requires(specifier) is None
    assert (
        f'Bad python_requires specifier: {specifier}'
        in capsys.readouterr().err
    )


@pytest.mark.parametrize('versions, expected', [
    (['2.7'], '==2.7.*'),
    (['3.6', '3.7'], '>=3.6'),
    (['2.7', '3.4', '3.5', '3.6', '3.7'],
     '>=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*'),
])
def test_compute_python_requires(versions, expected, fix_max_python_3_version):
    fix_max_python_3_version(7)
    result = compute_python_requires(versions)
    assert result == expected
    assert parse_python_requires(result) == versions
