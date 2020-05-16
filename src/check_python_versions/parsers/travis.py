"""
Support for Travis CI.

Travis CI is a hosted Continuous Integration solution that can be configured
by dropping a file named ``.travis.yml`` into your source repository.

There are multiple ways of selecting Python versions, some more canonical
than others:

- via the top-level ``python`` list
- via ``python`` attributes in the jobs defined by ``jobs.include`` or its
  deprecated alias ``matrix.include``
- via ``TOXENV`` environment variables in the top-level ``env`` list
  (this is discouraged and check-python-versions might drop support for this in
  the future)
"""

from typing import Callable, Collection, Dict, List, Optional, Tuple, Union

import yaml

from .tox import parse_envlist, tox_env_to_py_version
from ..utils import FileLines, FileOrFilename, open_file, warn
from ..versions import SortedVersionList, Version, is_important


TRAVIS_YML = '.travis.yml'


# Back in the day you could do
#
#   dist: trusty
#   python:
#     - pypy
#     - pypy3
#
# but then xenial came out and it did not recognize 'pypy' or 'pypy3', instead
# requiring you to explicitly spell out full version numbers like
#
#   dist: trusty
#   python:
#     - pypy2.7-6.0.0
#     - pypy3.5-6.0.0
#
# and check-python-versions could upgrade your .travis.yml from the old version
# to the new.  Happily, this is no longer necessary, because Travis supports
# 'pypy' and 'pypy3' once again.
XENIAL_SUPPORTED_PYPY_VERSIONS: Dict[str, str] = {
    # e.g. 'pypy': 'pypy2.7-7.1.1',
}


def get_travis_yml_python_versions(
    filename: FileOrFilename = TRAVIS_YML,
) -> SortedVersionList:
    """Extract supported Python versions from .travis.yml."""
    with open_file(filename) as fp:
        conf = yaml.safe_load(fp)
    versions: List[str] = []
    if conf.get('python'):
        if isinstance(conf['python'], list):
            versions += map(travis_normalize_py_version, conf['python'])
        else:
            versions.append(travis_normalize_py_version(conf['python']))
    if 'matrix' in conf and 'include' in conf['matrix']:
        for job in conf['matrix']['include']:
            if 'python' in job:
                versions.append(travis_normalize_py_version(job['python']))
    if 'jobs' in conf and 'include' in conf['jobs']:
        for job in conf['jobs']['include']:
            if 'python' in job:
                versions.append(travis_normalize_py_version(job['python']))
    if 'env' in conf:
        toxenvs = []
        for env in conf['env']:
            if env.startswith('TOXENV='):
                toxenvs.extend(parse_envlist(env.partition('=')[-1]))
        versions.extend(e for e in map(tox_env_to_py_version, toxenvs) if e)
    return sorted(set(versions))


def travis_normalize_py_version(v: str) -> Version:
    v = str(v)
    if v.startswith('pypy3'):
        # could be pypy3, pypy3.5, pypy3.5-5.10.0
        return 'PyPy3'
    elif v.startswith('pypy'):
        # could be pypy, pypy2, pypy2.7, pypy2.7-5.10.0
        return 'PyPy'
    else:
        return v


def needs_xenial(v: Version) -> bool:
    """Check if a Python version needs dist: xenial.

    This is obsolete now that dist: xenial is the default, but it may
    be helpful to determine when we need to drop old dist: trusty.
    """
    major, minor = map(int, v.split('.'))
    return major == 3 and minor >= 7


def update_travis_yml_python_versions(
    filename: FileOrFilename,
    new_versions: SortedVersionList,
) -> FileLines:
    """Update supported Python versions in .travis.yml.

    Does not touch the file but returns a list of lines with new file contents.
    """
    with open_file(filename) as fp:
        orig_lines = fp.readlines()
        fp.seek(0)
        conf = yaml.safe_load(fp)
    new_lines = orig_lines

    # Make sure we're using dist: xenial if we want to use Python 3.7 or newer.
    replacements = {}
    if any(map(needs_xenial, new_versions)):
        replacements.update(XENIAL_SUPPORTED_PYPY_VERSIONS)
        if conf.get('dist') == 'trusty':
            new_lines = drop_yaml_node(new_lines, 'dist', filename=fp.name)
        if conf.get('sudo') is False:
            # sudo is ignored nowadays, but in earlier times
            # you needed both dist: xenial and sudo: required
            # to get Python 3.7
            new_lines = drop_yaml_node(new_lines, "sudo", filename=fp.name)

    def keep_old(ver: str) -> bool:
        """Determine if a Python version line should be preserved."""
        ver = travis_normalize_py_version(ver)
        if ver == 'PyPy':
            return any(v.startswith('2') for v in new_versions)
        if ver == 'PyPy3':
            return any(v.startswith('3') for v in new_versions)
        return not is_important(ver)

    def keep_old_job(job: str) -> bool:
        """Determine if a job line should be preserved."""
        if job.startswith('python:'):
            ver = job[len('python:'):].strip()
            return not is_important(travis_normalize_py_version(ver))
        else:
            return True

    if conf.get('python'):
        new_lines = update_yaml_list(
            new_lines, "python", new_versions, filename=fp.name, keep=keep_old,
            replacements=replacements,
        )
    else:
        replacements = {
            f'python: {k}': f'python: {v}'
            for k, v in replacements.items()
        }
        for toplevel in 'matrix', 'jobs':
            if 'include' not in conf.get(toplevel, {}):
                continue
            new_jobs = [
                f'python: {ver}'
                for ver in new_versions
            ]
            new_lines = update_yaml_list(
                new_lines, (toplevel, "include"), new_jobs, filename=fp.name,
                replacements=replacements, keep=keep_old_job,
            )

    # If python 3.7 was enabled via matrix.include, we've just added a
    # second 3.7 entry directly to top-level python by the above code.
    # So let's drop the matrix.

    if (
        conf.get('python')
            and 'include' in conf.get('matrix', {})
            and all(
                job.get('dist') == 'xenial'
                and set(job) <= {'python', 'dist', 'sudo'}
                for job in conf['matrix']['include']
            )
    ):
        # XXX: this may drop too much or too little!
        new_lines = drop_yaml_node(new_lines, "matrix", filename=fp.name)

    return new_lines


def update_yaml_list(
    orig_lines: FileLines,
    key: Union[str, Tuple[str, ...]],
    new_value: List[str],
    *,
    filename: str = TRAVIS_YML,
    keep: Optional[Callable[[str], bool]] = None,
    replacements: Optional[Dict[str, str]] = None,
) -> FileLines:
    """Update a list of values in a YAML document.

    The document is represented as a list of lines (``orig_lines``), because
    we want to preserve the exact formatting including comments.

    ``key`` is a tuple that represents the traversal path from the root of
    the document.  As a special case it can be a string instead of a 1-tuple
    for top-level keys.

    The new value of the list will consist of ``new_value``, plus whatever
    old values need to be kept according to the ``keep`` callback.  Any of the
    kept old values will also be optionally replaced with a replacement
    from the ``replacements`` dict.

    No YAML decoding is done for old values passed to ``keep()`` or
    ``replacements.get()``.

    No YAML escaping or formatting is done for new values or replacements.

    ``filename`` is used for error reporting.

    Returns an updated list of lines.
    """
    if not isinstance(key, tuple):
        key = (key,)

    lines = iter(enumerate(orig_lines))
    current = 0
    indents = [0]
    for n, line in lines:
        stripped = line.lstrip()
        if not stripped or stripped.startswith('#'):
            continue
        indent = len(line) - len(stripped)
        if current >= len(indents):
            indents.append(indent)
        elif indent > indents[current]:
            continue
        else:
            while current > 0 and indent < indents[current]:
                del indents[current]
                current -= 1
        if stripped.startswith(f'{key[current]}:'):
            current += 1
            if current == len(key):
                break
    else:
        warn(f'Did not find {".".join(key)}: setting in {filename}')
        return orig_lines

    start = n
    end = n + 1
    indent = 2
    list_indent = None
    keep_before: List[str] = []
    keep_after: List[str] = []
    lines_to_keep = keep_before
    kept_last: Optional[bool] = False
    for n, line in lines:
        stripped = line.lstrip()
        line_indent = len(line) - len(stripped)
        if list_indent is None and stripped.startswith('- '):
            list_indent = line_indent
        if stripped.startswith('- ') and line_indent == list_indent:
            lines_to_keep = keep_after
            indent = line_indent
            end = n + 1
            value = stripped[2:].strip()
            kept_last = keep and keep(value)
            if kept_last:
                if replacements and value in replacements:
                    lines_to_keep.append(
                        f"{' '* indent}- {replacements[value]}\n"
                    )
                else:
                    lines_to_keep.append(line)
        elif stripped.startswith('#'):
            lines_to_keep.append(line)
            end = n + 1
        elif line_indent > indent:
            if kept_last:
                lines_to_keep.append(line)
            end = n + 1
        elif line == '\n':
            continue
        elif line[0] != ' ':
            break
        elif list_indent is not None and line_indent < list_indent:
            break

    new_lines = orig_lines[:start] + [
        f"{' ' * indents[-1]}{key[-1]}:\n"
    ] + keep_before + [
        f"{' ' * indent}- {value}\n"
        for value in new_value
    ] + keep_after + orig_lines[end:]
    return new_lines


def drop_yaml_node(
    orig_lines: FileLines,
    key: str,
    filename: str = TRAVIS_YML,
) -> FileLines:
    """Drop a value from a YAML document.

    The document is represented as a list of lines (``orig_lines``), because
    we want to preserve the exact formatting including comments.

    ``key`` is a string.  Currently only top-level nodes can be dropped.

    ``filename`` is used for error reporting.

    It is not an error if ``key`` is not present in the document.  In this
    case ``orig_lines`` is returned unmodified.

    Returns an updated list of lines.
    """
    lines = iter(enumerate(orig_lines))
    where = None
    for n, line in lines:
        if line.startswith(f'{key}:'):
            if where is not None:
                warn(
                    f"Duplicate {key}: setting in {filename}"
                    f" (lines {where + 1} and {n + 1})"
                )
            where = n
    if where is None:
        return orig_lines

    lines = iter(enumerate(orig_lines[where + 1:], where + 1))

    start = where
    end = start + 1
    for n, line in lines:
        if line and line[0] != ' ':
            break
        else:
            end = n + 1
    new_lines = orig_lines[:start] + orig_lines[end:]

    return new_lines


def add_yaml_node(
    orig_lines: FileLines,
    key: str,
    value: str,
    before: Optional[Union[str, Collection[str]]] = None,
) -> FileLines:
    """Add a value to a YAML document.

    The document is represented as a list of lines (``orig_lines``), because
    we want to preserve the exact formatting including comments.

    ``key`` is a string.  Currently only top-level nodes can be added.

    ``value`` is the new value, as a string.  No YAML escaping or formatting
    is done.

    ``before`` can specify a key or a set of keys.  If specified, the new
    key will be added before the first of existing keys from this set.

    Returns an updated list of lines.
    """
    lines = iter(enumerate(orig_lines))
    where = len(orig_lines)
    if before:
        if isinstance(before, str):
            before = (before, )
        lines = iter(enumerate(orig_lines))
        for n, line in lines:
            if any(line == f'{key}:\n' for key in before):
                where = n
                break

    new_lines = orig_lines[:where] + [
        f'{key}: {value}\n'
    ] + orig_lines[where:]
    return new_lines
