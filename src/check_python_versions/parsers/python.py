"""
Tools for manipulating Python files.
"""

import ast
import re
import string
from typing import List, Optional, Tuple, Union, cast

from ..utils import FileLines, get_indent, warn


AstValue = Union[str, List[str], Tuple[str, ...]]


def to_literal(value: str, quote_style: str = '"') -> str:
    """Convert a string value to a Python string literal."""
    # Because I don't want to deal with quoting, I'll require all values
    # to contain only safe characters (i.e. no ' or " or \).  Except some
    # PyPI classifiers do include ' so I need to handle that at least.
    # And python_requires uses all sorts of comparisons like ~= 3.7.*
    safe_chars = string.ascii_letters + string.digits + " .:,-=><!~*()/+'#"
    assert all(
        c in safe_chars for c in value
    ), f'{value!r} has unexpected characters'
    if quote_style == "'" and quote_style in value:
        quote_style = '"'
    assert quote_style not in value
    return f'{quote_style}{value}{quote_style}'


def update_call_arg_in_source(
    source_lines: FileLines,
    function: str,
    keyword: str,
    new_value: Union[str, List[str]],
) -> FileLines:
    """Update a function call statement in Python source file.

    Finds the first function all, removes the old value passed to a named
    keyword argument and replaces it with a new value.

    Tries to preserve existing formatting.

    Returns the updated source.
    """
    lines = iter(enumerate(source_lines))
    rx = re.compile(f'^{re.escape(function)}\\s*\\(')
    for n, line in lines:
        if rx.match(line):
            break
    else:
        warn(f'Did not find {function}() call')
        return source_lines
    eq = '='
    rx = re.compile(
        f'^(?P<indent>\\s*){re.escape(keyword)}(?P<eq>\\s*=\\s*)(?P<rest>.*)'
    )
    for n, line in lines:
        m = rx.match(line)
        if m:
            first_match = m
            eq = m.group('eq')
            first_indent = m.group('indent')
            break
    else:
        warn(f'Did not find {keyword}= argument in {function}() call')
        return source_lines

    quote_style = '"'
    rest = first_match.group('rest')
    joined = False

    if isinstance(new_value, list):
        start = n
        indent = first_indent + ' ' * 4
        if rest.startswith('[]'):
            fix_closing_bracket = True
            end = n + 1
        else:
            must_fix_indents = rest.rstrip() != '['
            fix_closing_bracket = False
            for n, line in lines:
                stripped = line.lstrip()
                if stripped.startswith(']'):
                    end = n
                    break
                elif stripped:
                    if not must_fix_indents:
                        indent = get_indent(line)
                    if stripped[0] in ('"', "'"):
                        quote_style = stripped[0]
                    if line.rstrip().endswith('],'):
                        end = n + 1
                        fix_closing_bracket = True
                        break
            else:
                warn(
                    f'Did not understand {keyword}= formatting'
                    f' in {function}() call'
                )
                return source_lines
    elif rest.endswith('.join(['):
        joined = True
        start = n
        indent = first_indent + ' ' * 4
        for n, line in lines:
            stripped = line.lstrip()
            if stripped.startswith(']'):
                end = n + 1
                fix_closing_bracket = True
                break
        else:
            warn(
                f'Did not understand {keyword}= formatting'
                f' in {function}() call'
            )
            return source_lines
    else:
        start = n
        end = n + 1

    if isinstance(new_value, list):
        return source_lines[:start] + [
            f"{first_indent}{keyword}{eq}[\n"
        ] + [
            f"{indent}{to_literal(value, quote_style)},\n"
            for value in new_value
        ] + ([
            f"{first_indent}],\n"
        ] if fix_closing_bracket else [
        ]) + source_lines[end:]
    elif joined:
        if rest.startswith("'"):
            quote_style = "'"
        comma = ', '
        if comma not in new_value:
            comma = ','
        new_value = new_value.split(comma)
        comma = to_literal(comma, quote_style)
        return source_lines[:start] + [
            f"{first_indent}{keyword}{eq}{comma}.join([\n"
        ] + [
            f"{indent}{to_literal(value, quote_style)},\n"
            for value in new_value
        ] + ([
            f"{first_indent}]),\n"
        ] if fix_closing_bracket else [
        ]) + source_lines[end:]
    else:
        if rest.startswith("'"):
            quote_style = "'"
        new_value_quoted = to_literal(new_value, quote_style)
        return source_lines[:start] + [
            f"{first_indent}{keyword}{eq}{new_value_quoted},\n"
        ] + source_lines[end:]


def find_call_kwarg_in_ast(
    tree: ast.AST,
    funcname: str,
    keyword: str,
    *,
    filename: str,
) -> Optional[ast.AST]:
    """Find the value passed to a function call.

    ``filename`` is used for error reporting.
    """
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == funcname):
            for kwarg in node.keywords:
                if kwarg.arg == keyword:
                    return kwarg.value
            else:
                return None
    else:
        warn(f'Could not find {funcname}() call in {filename}')
        return None


def eval_ast_node(node: ast.AST, keyword: str) -> Optional[AstValue]:
    """Partially evaluate an AST node.

    ``keyword`` is used for error reporting.
    """
    if isinstance(node, ast.Str):
        assert isinstance(node.s, str)
        return node.s
    if isinstance(node, (ast.List, ast.Tuple)):
        values: List[str] = []
        warned = False
        for element in node.elts:
            try:
                value = ast.literal_eval(element)
                if not isinstance(value, str):
                    raise ValueError
            except ValueError:
                pass
            else:
                values.append(value)
                continue
            if not warned:
                warn(f'Non-literal {keyword}= passed to setup(),'
                     ' skipping some values')
                warned = True
        if warned and not values:
            # no strings inside!
            return None
        if isinstance(node, ast.Tuple):
            return tuple(values)
        return values
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Str)
            and node.func.attr == 'join'):
        try:
            return cast(str, node.func.value.s).join(
                ast.literal_eval(node.args[0]))
        except ValueError:
            pass
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = eval_ast_node(node.left, keyword)
        right = eval_ast_node(node.right, keyword)
        if left is not None and right is not None:
            if type(left) != type(right):
                warn(f'{keyword}= is computed by adding incompatible types:'
                     f' {type(left).__name__} and {type(right).__name__}')
                return None
            # Not sure how to make mypy accept this:
            # https://github.com/python/mypy/issues/8831
            return left + right  # type: ignore
        if left is None and right is not None:
            return right
        if left is not None and right is None:
            return left
    warn(f'Non-literal {keyword}= passed to setup()')
    return None
