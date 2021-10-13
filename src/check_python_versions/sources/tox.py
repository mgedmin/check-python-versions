"""
Support for Tox.

Tox is an amazing tool for running tests (and other tasks) in virtualenvs.
You create a ``tox.ini``, tell it what Python versions you want to support
and how to run your test suite, and Tox does everything else: create the
right virtualenvs using the right Python interpreter versions, install your
packages, and run the test commands you specified.

The list of supported Python versions is extracted from ::

    [tox]
    envlist = py27,py36,py37,py38

"""

import configparser
import re
from typing import Iterable, List, Optional

from .base import Source
from ..parsers.ini import update_ini_setting
from ..utils import FileLines, FileOrFilename, open_file, warn
from ..versions import SortedVersionList, Version, VersionList


TOX_INI = 'tox.ini'


def get_tox_ini_python_versions(
    filename: FileOrFilename = TOX_INI,
) -> SortedVersionList:
    """Extract supported Python versions from tox.ini."""
    conf = configparser.ConfigParser()
    try:
        with open_file(filename) as fp:
            conf.read_file(fp)
        envlist = conf.get('tox', 'envlist')
    except configparser.Error:
        return []
    return sorted({
        e for e in map(tox_env_to_py_version, parse_envlist(envlist)) if e
    })


def split_envlist(envlist: str) -> Iterable[str]:
    """Split an environment list into items.

    Tox allows commas or whitespace as separators.

    The trick is that commas inside {...} brace groups do not count.

    This function does not expand brace groups.
    """
    for part in re.split(r'((?:[{][^}]*[}]|[^,{\s])+)|,|\s+', envlist):
        # NB: part can be None
        part = (part or '').strip()
        if part:
            yield part


def parse_envlist(envlist: str) -> List[str]:
    """Parse an environment list.

    This function expands brace groups.
    """
    envs = []
    for part in split_envlist(envlist):
        envs += brace_expand(part)
    return envs


def brace_expand(s: str) -> List[str]:
    """Expand a braced group.

    E.g. brace_expand('a{1,2}{b,c}x') == ['a1bx', 'a1cx', 'a2bx', 'a2cx'].

    Note that this function doesn't support nested brace groups.  I'm not sure
    Tox supports them.
    """
    m = re.match('^([^{]*)[{]([^}]*)[}](.*)$', s)
    if not m:
        return [s]
    left = m.group(1)
    right = m.group(3)
    res = []
    for alt in m.group(2).split(','):
        res += brace_expand(left + alt.strip() + right)
    return res


def tox_env_to_py_version(env: str) -> Optional[Version]:
    """Convert a Tox environment name to a Python version.

    E.g. py34 becomes '3.4', pypy3 becomes 'PyPy3'.

    Unrecognized environments are left alone.

    If the environment name has dashes, only the first part is considered,
    e.g. py34-django20 becomes '3.4', and jython-docs becomes 'jython'.
    """
    if '-' in env:
        # e.g. py34-coverage, pypy-subunit
        env = env.partition('-')[0]
    if env.startswith('pypy'):
        return Version.from_string('PyPy' + env[4:])
    elif env.startswith('py') and len(env) >= 4 and env[2:].isdigit():
        return Version.from_string(f'{env[2]}.{env[3:]}')
    else:
        return None


def update_tox_ini_python_versions(
    filename: FileOrFilename,
    new_versions: SortedVersionList,
) -> FileLines:
    """Update supported Python versions in tox.ini.

    Does not touch the file but returns a list of lines with new file contents.
    """
    with open_file(filename) as fp:
        orig_lines = fp.readlines()
        fp.seek(0)
        conf = configparser.ConfigParser()
        try:
            conf.read_file(fp)
            envlist = conf.get('tox', 'envlist')
        except configparser.Error as error:
            warn(f"Could not parse {fp.name}: {error}")
            return orig_lines

    new_envlist = update_tox_envlist(envlist, new_versions)

    new_lines = update_ini_setting(
        orig_lines, 'tox', 'envlist', new_envlist, filename=fp.name,
    )
    return new_lines


def update_tox_envlist(envlist: str, new_versions: SortedVersionList) -> str:
    """Update an environment list.

    Makes sure all Python versions from ``new_versions`` are in the list.
    Removes all Python versions not in ``new_versions``.  Leaves other
    environments (e.g. flake8, docs) alone.

    Tries to preserve formatting and braced groups.
    """
    # Find a comma outside brace groups and see what whitespace follows it
    # (also note that items can be separated with whitespace without a comma,
    # but the only whitespace used this way I've seen in the wild was newlines)
    m = re.search(r',\s*|\n', re.sub(r'[{][^}]*[}]', '', envlist.strip()))
    if m:
        sep = m.group()
    else:
        sep = ','

    trailing_comma = envlist.rstrip().endswith(',')

    new_envs = [
        toxenv_for_version(ver)
        for ver in new_versions
    ]

    if 'py{' in envlist or '{py' in envlist:
        # Try to preserve braced groups
        parts = []
        added_vers = False
        for part in split_envlist(envlist):
            m = re.match(
                r'(py[{](?:\d+|py\d*)(?:,(?:\d+|py\d*))*[}])(?P<rest>.*)',
                part
            )
            if m:
                keep = [env for env in brace_expand(m.group(1))
                        if should_keep(env, new_versions)]
                parts.append(
                    'py{' + ','.join(
                        env[len('py'):] for env in new_envs + keep
                    ) + '}' + m.group('rest')
                )
                added_vers = True
                continue
            m = re.match(
                r'([{]py(?:\d+|py\d*)(?:,py(?:\d+|py\d*))*[}])(?P<rest>.*)',
                part
            )
            if m:
                keep = [env for env in brace_expand(m.group(1))
                        if should_keep(env, new_versions)]
                parts.append(
                    '{' + ','.join(new_envs + keep) + '}' + m.group('rest')
                )
                added_vers = True
                continue
            vers = brace_expand(part)
            if all(not should_keep(ver, new_versions) for ver in vers):
                continue
            if not all(should_keep(ver, new_versions) for ver in vers):
                parts.append(sep.join(
                    ver for ver in vers if should_keep(ver, new_versions)
                ))
                continue
            parts.append(part)
        if not added_vers:
            parts = new_envs + parts
        return sep.join(parts)

    # Universal expansion, might destroy braced groups
    keep_before: List[str] = []
    keep_after: List[str] = []
    keep = keep_before
    for env in parse_envlist(envlist):
        if should_keep(env, new_versions):
            keep.append(env)
        else:
            keep = keep_after
    new_envlist = sep.join(keep_before + new_envs + keep_after)
    if trailing_comma:
        new_envlist += ','
    return new_envlist


def toxenv_for_version(ver: Version) -> str:
    """Compute a tox environment name for a Python version."""
    return f"py{ver.major}{ver.minor if ver.minor >= 0 else ''}"


def should_keep(env: str, new_versions: VersionList) -> bool:
    """Check if a tox environment needs to be kept.

    Any environments that refer to a specific Python version not in
    ``new_versions`` will be removed.  All other environments are kept.

    ``pypy`` and ``pypy3`` are kept only if there's at least one Python 2.x
    or 3.x version respectively in ``new_versions``.

    """
    if not re.match(r'py(py)?\d*($|-)', env):
        return True
    if env == 'pypy':
        return any(ver.major == 2 for ver in new_versions)
    if env == 'pypy3':
        return any(ver.major == 3 for ver in new_versions)
    if '-' in env:
        baseversion = tox_env_to_py_version(env)
        if baseversion in new_versions:
            return True
    return False


Tox = Source(
    filename=TOX_INI,
    extract=get_tox_ini_python_versions,
    update=update_tox_ini_python_versions,
    check_pypy_consistency=True,
    has_upper_bound=True,
)
