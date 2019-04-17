import ast
import os
import re
import string
from functools import partial

from ..utils import warn, pipe, open_file, is_file_object
from ..versions import MAX_MINOR_FOR_MAJOR


def get_supported_python_versions(filename='setup.py'):
    classifiers = get_setup_py_keyword(filename, 'classifiers')
    if classifiers is None and not is_file_object(filename):
        # AST parsing is complicated
        setup_py = os.path.basename(filename)
        classifiers = pipe("python", setup_py, "-q", "--classifiers",
                           cwd=os.path.dirname(filename)).splitlines()
    if classifiers is None:
        return []
    return get_versions_from_classifiers(classifiers)


def get_python_requires(setup_py='setup.py'):
    python_requires = get_setup_py_keyword(setup_py, 'python_requires')
    if python_requires is None:
        return None
    return parse_python_requires(python_requires)


def is_version_classifier(s):
    prefix = 'Programming Language :: Python :: '
    return s.startswith(prefix) and s[len(prefix):len(prefix) + 1].isdigit()


def is_major_version_classifier(s):
    prefix = 'Programming Language :: Python :: '
    return (
        s.startswith(prefix)
        and s[len(prefix):].replace(' :: Only', '').isdigit()
    )


def get_versions_from_classifiers(classifiers):
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
    return sorted(versions)


def update_classifiers(classifiers, new_versions):
    prefix = 'Programming Language :: Python :: '

    for pos, s in enumerate(classifiers):
        if is_version_classifier(s):
            break
    else:
        pos = len(classifiers)

    if any(map(is_major_version_classifier, classifiers)):
        new_versions = sorted(
            set(new_versions).union(
                v.partition('.')[0] for v in new_versions
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


def update_supported_python_versions(filename, new_versions):
    classifiers = get_setup_py_keyword(filename, 'classifiers')
    if classifiers is None:
        return None
    new_classifiers = update_classifiers(classifiers, new_versions)
    return update_setup_py_keyword(filename, 'classifiers', new_classifiers)


def update_python_requires(filename, new_versions):
    python_requires = get_setup_py_keyword(filename, 'python_requires')
    if python_requires is None:
        return None
    new_python_requires = compute_python_requires(new_versions)
    if is_file_object(filename):
        filename.seek(0)
    return update_setup_py_keyword(filename, 'python_requires',
                                   new_python_requires)


def get_setup_py_keyword(setup_py, keyword):
    with open_file(setup_py) as f:
        try:
            tree = ast.parse(f.read(), f.name)
        except SyntaxError as error:
            warn(f'Could not parse {f.name}: {error}')
            return None
    node = find_call_kwarg_in_ast(tree, 'setup', keyword)
    return node and eval_ast_node(node, keyword)


def update_setup_py_keyword(setup_py, keyword, new_value):
    with open_file(setup_py) as f:
        lines = f.readlines()
    new_lines = update_call_arg_in_source(lines, 'setup', keyword, new_value)
    return new_lines


def to_literal(value, quote_style='"'):
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


def update_call_arg_in_source(source_lines, function, keyword, new_value):
    lines = iter(enumerate(source_lines))
    for n, line in lines:
        if line.startswith(f'{function}('):
            break
    else:
        warn(f'Did not find {function}() call')
        return source_lines
    for n, line in lines:
        stripped = line.lstrip()
        if stripped.startswith(f'{keyword}='):
            first_indent = len(line) - len(stripped)
            must_fix_indents = not line.rstrip().endswith('=[')
            break
    else:
        warn(f'Did not find {keyword}= argument in {function}() call')
        return source_lines

    quote_style = '"'

    if isinstance(new_value, list):
        start = n
        indent = first_indent + 4
        fix_closing_bracket = False
        for n, line in lines:
            stripped = line.lstrip()
            if stripped.startswith(']'):
                end = n
                break
            elif stripped:
                if not must_fix_indents:
                    indent = len(line) - len(stripped)
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
    else:
        start = n
        end = n + 1

    if isinstance(new_value, list):
        return source_lines[:start] + [
            f"{' ' * first_indent}{keyword}=[\n"
        ] + [
            f"{' ' * indent}{to_literal(value, quote_style)},\n"
            for value in new_value
        ] + ([
            f"{' ' * first_indent}],\n"
        ] if fix_closing_bracket else [
        ]) + source_lines[end:]
    else:
        if line.lstrip().startswith(f"{keyword}='"):
            quote_style = "'"
        new_value_quoted = to_literal(new_value, quote_style)
        return source_lines[:start] + [
            f"{' ' * first_indent}{keyword}={new_value_quoted},\n"
        ] + source_lines[end:]


def find_call_kwarg_in_ast(tree, funcname, keyword, filename='setup.py'):
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


def eval_ast_node(node, keyword):
    if isinstance(node, ast.Str):
        return node.s
    if isinstance(node, (ast.List, ast.Tuple)):
        try:
            return ast.literal_eval(node)
        except ValueError:
            if any(isinstance(element, ast.Str) for element in node.elts):
                # Let's try our best!!!
                warn(f'Non-literal {keyword}= passed to setup(),'
                     ' skipping some values')
                return [
                    eval_ast_node(element, keyword)
                    for element in node.elts
                    if isinstance(element, ast.Str)
                ]
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Str)
            and node.func.attr == 'join'):
        try:
            return node.func.value.s.join(ast.literal_eval(node.args[0]))
        except ValueError:
            pass
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = eval_ast_node(node.left, keyword)
        right = eval_ast_node(node.right, keyword)
        if left is not None and right is not None:
            return left + right
        if left is None and right is not None:
            return right
        if left is not None and right is None:
            return left
    warn(f'Non-literal {keyword}= passed to setup()')
    return None


def parse_python_requires(s):
    # https://www.python.org/dev/peps/pep-0440/#version-specifiers
    rx = re.compile(r'^(~=|==|!=|<=|>=|<|>|===)\s*(\d+(?:\.\d+)*(?:\.\*)?)$')

    class BadConstraint(Exception):
        pass

    handlers = {}
    handler = partial(partial, handlers.__setitem__)

    #
    # We are not doing a strict PEP-440 implementation here because if
    # python_reqiures allows, say, Python 2.7.16, then we want to report that
    # as Python 2.7.  In each handler ``canditate`` is a two-tuple (X, Y)
    # that represents any Python version between X.Y.0 and X.Y.<whatever>.
    #

    @handler('~=')
    def compatible_version(constraint):
        if len(constraint) < 2:
            raise BadConstraint('~= requires a version with at least one dot')
        if constraint[-1] == '*':
            raise BadConstraint('~= does not allow a .*')
        return lambda candidate: candidate == constraint[:2]

    @handler('==')
    def matching_version(constraint):
        # we know len(candidate) == 2
        if len(constraint) == 2 and constraint[-1] == '*':
            return lambda candidate: candidate[0] == constraint[0]
        elif len(constraint) == 1:
            # == X should imply Python X.0
            return lambda candidate: candidate == constraint + (0,)
        else:
            # == X.Y.* and == X.Y.Z both imply Python X.Y
            return lambda candidate: candidate == constraint[:2]

    @handler('!=')
    def excluded_version(constraint):
        # we know len(candidate) == 2
        if constraint[-1] != '*':
            # != X or != X.Y or != X.Y.Z all are meaningless for us, because
            # there exists some W != Z where we allow X.Y.W and thus allow
            # Python X.Y.
            return lambda candidate: True
        elif len(constraint) == 2:
            # != X.* excludes the entirety of a major version
            return lambda candidate: candidate[0] != constraint[0]
        else:
            # != X.Y.* excludes one particular minor version X.Y,
            # != X.Y.Z.* does not exclude anything, but it's fine,
            # len(candidate) != len(constraint[:-1] so it'll be equivalent to
            # True anyway.
            return lambda candidate: candidate != constraint[:-1]

    @handler('>=')
    def greater_or_equal_version(constraint):
        if constraint[-1] == '*':
            raise BadConstraint('>= does not allow a .*')
        # >= X, >= X.Y, >= X.Y.Z all work out nicely because in Python
        # (3, 0) >= (3,)
        return lambda candidate: candidate >= constraint[:2]

    @handler('<=')
    def lesser_or_equal_version(constraint):
        if constraint[-1] == '*':
            raise BadConstraint('<= does not allow a .*')
        if len(constraint) == 1:
            # <= X allows up to X.0
            return lambda candidate: candidate <= constraint + (0,)
        else:
            # <= X.Y[.Z] allows up to X.Y
            return lambda candidate: candidate <= constraint

    @handler('>')
    def greater_version(constraint):
        if constraint[-1] == '*':
            raise BadConstraint('> does not allow a .*')
        if len(constraint) == 1:
            # > X allows X+1.0 etc
            return lambda candidate: candidate[0] > constraint[0]
        elif len(constraint) == 2:
            # > X.Y allows X.Y+1 etc
            return lambda candidate: candidate > constraint
        else:
            # > X.Y.Z allows X.Y
            return lambda candidate: candidate >= constraint[:2]

    @handler('<')
    def lesser_version(constraint):
        if constraint[-1] == '*':
            raise BadConstraint('< does not allow a .*')
        # < X, < X.Y, < X.Y.Z all work out nicely because in Python
        # (3, 0) > (3,), (3, 0) == (3, 0) and (3, 0) < (3, 0, 1)
        return lambda candidate: candidate < constraint

    @handler('===')
    def arbitrary_version(constraint):
        if constraint[-1] == '*':
            raise BadConstraint('=== does not allow a .*')
        # === X does not allow anything
        # === X.Y throws me into confusion; will pip compare Python's X.Y.Z ===
        # X.Y and reject all possible values of Z?
        # === X.Y.Z allows X.Y
        return lambda candidate: candidate == constraint[:2]

    constraints = []
    for specifier in map(str.strip, s.split(',')):
        m = rx.match(specifier)
        if not m:
            warn(f'Bad python_requires specifier: {specifier}')
            continue
        op, ver = m.groups()
        ver = tuple(
            int(segment) if segment != '*' else segment
            for segment in ver.split('.')
        )
        try:
            constraints.append(handlers[op](ver))
        except BadConstraint as error:
            warn(f'Bad python_requires specifier: {specifier} ({error})')

    if not constraints:
        return None

    versions = []
    for major in sorted(MAX_MINOR_FOR_MAJOR):
        for minor in range(0, MAX_MINOR_FOR_MAJOR[major] + 1):
            if all(constraint((major, minor)) for constraint in constraints):
                versions.append(f'{major}.{minor}')
    return versions


def compute_python_requires(new_versions):
    new_versions = set(new_versions)
    # XXX assumes all versions are X.Y and 3.10 will never be released
    min_version = min(new_versions)
    specifiers = [f'>={min_version}']
    for major in sorted(MAX_MINOR_FOR_MAJOR):
        for minor in range(0, MAX_MINOR_FOR_MAJOR[major] + 1):
            ver = f'{major}.{minor}'
            if ver >= min_version and ver not in new_versions:
                specifiers.append(f'!={ver}.*')
    return ', '.join(specifiers)
