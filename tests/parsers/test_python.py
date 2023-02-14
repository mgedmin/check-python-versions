import ast
import textwrap

import pytest

from check_python_versions.parsers.python import (
    eval_ast_node,
    find_call_kwarg_in_ast,
    name_matches,
    to_literal,
    update_call_arg_in_source,
)


def test_find_call_kwarg_in_ast():
    tree = ast.parse('foo(bar="foo")')
    node = find_call_kwarg_in_ast(tree, 'foo', 'bar', filename='setup.py')
    assert isinstance(node, ast.Str)
    assert node.s == "foo"


def test_find_call_kwarg_in_ast_dotted():
    tree = ast.parse('mod.foo(bar="gronk")')
    node = find_call_kwarg_in_ast(tree, 'mod.foo', 'bar', filename='setup.py')
    assert isinstance(node, ast.Str)
    assert node.s == "gronk"


def test_find_call_kwarg_in_ast_alternatives():
    tree = ast.parse('mod.foo(bar="gronk")')
    node = find_call_kwarg_in_ast(tree, ['foo', 'mod.foo'], 'bar',
                                  filename='a.py')
    assert isinstance(node, ast.Str)
    assert node.s == "gronk"


def test_find_call_kwarg_in_ast_no_arg(capsys):
    tree = ast.parse('foo(baz="foo")')
    node = find_call_kwarg_in_ast(tree, 'foo', 'bar', filename='setup.py')
    assert node is None
    assert capsys.readouterr().err == ''


def test_find_call_kwarg_in_ast_no_call(capsys):
    tree = ast.parse('fooo(bar="foo")')
    node = find_call_kwarg_in_ast(tree, 'foo', 'bar', filename='setup.py')
    assert node is None
    assert 'Could not find foo() call in setup.py' in capsys.readouterr().err


def test_name_matches():
    tree = ast.parse('a.b.c.d.e')
    node = tree.body[0].value
    assert name_matches('a.b.c.d.e', node)
    assert not name_matches('a.b.c.d.x', node)
    assert not name_matches('b.c.d.e', node)
    assert not name_matches('e', node)


@pytest.mark.parametrize('code, expected', [
    ('"hi"', "hi"),
    ('"hi\\n"', "hi\n"),
    ('3.14', None),
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
    node = find_call_kwarg_in_ast(tree, 'foo', 'bar', filename='setup.py')
    assert node is not None
    assert eval_ast_node(node, 'bar') == expected


@pytest.mark.parametrize('code, expected', [
    ('["a", "b", "c" if condition else "d", "e", 42]', ["a", "b", "e"]),
])
def test_eval_ast_node_skips_computed_values(code, expected, capsys):
    tree = ast.parse(f'foo(bar={code})')
    node = find_call_kwarg_in_ast(tree, 'foo', 'bar', filename='setup.py')
    assert node is not None
    assert eval_ast_node(node, 'bar') == expected
    assert (
        'Non-literal bar= passed to setup() in setup.py, skipping some values'
        in capsys.readouterr().err
    )


@pytest.mark.parametrize('code', [
    '[2 * 2]',
    '"".join([2 * 2])',
    'extra + more',
])
def test_eval_ast_node_failures(code, capsys):
    tree = ast.parse(f'foo(bar={code})')
    node = find_call_kwarg_in_ast(tree, 'foo', 'bar', filename='setup.py')
    assert eval_ast_node(node, 'bar') is None
    assert (
        'Non-literal bar= passed to setup() in setup.py'
        in capsys.readouterr().err
    )


@pytest.mark.parametrize('code', [
    '["a", "b"] + "c"',
])
def test_eval_ast_node_type_mismatch(code, capsys):
    tree = ast.parse(f'foo(bar={code})')
    node = find_call_kwarg_in_ast(tree, 'foo', 'bar', filename='setup.py')
    assert eval_ast_node(node, 'bar') is None
    assert (
        'bar= in setup.py is computed by adding incompatible types:'
        ' list and str'
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


def test_update_call_arg_in_source_dotted_name():
    source_lines = textwrap.dedent("""\
        setuptools.setup(
            foo=1,
            bar="x",
            baz=2,
        )
    """).splitlines(True)
    result = update_call_arg_in_source(source_lines, "setuptools.setup",
                                       "bar", "y")
    assert "".join(result) == textwrap.dedent("""\
        setuptools.setup(
            foo=1,
            bar="y",
            baz=2,
        )
    """)


def test_update_call_arg_in_source_maybe_dotted_name():
    source_lines = textwrap.dedent("""\
        setuptools.setup(
            foo=1,
            bar="x",
            baz=2,
        )
    """).splitlines(True)
    result = update_call_arg_in_source(source_lines,
                                       ("setup", "setuptools.setup"),
                                       "bar", "y")
    assert "".join(result) == textwrap.dedent("""\
        setuptools.setup(
            foo=1,
            bar="y",
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
