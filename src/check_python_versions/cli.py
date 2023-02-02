"""
Command-line user interface.

This is the main module of check-python-versions, responsible for handling
command-line arguments, extracting information about supported Python versions
from various sources, presenting it to the user and possibly making
modifications.
"""

import argparse
import glob
import os
import sys
from io import StringIO
from typing import Callable, Collection, Dict, List, Optional, Tuple

from . import __version__
from .sources.all import ALL_SOURCES
from .sources.base import SourceFile
from .utils import (
    FileLines,
    FileOrFilename,
    confirm_and_update_file,
    show_diff,
)
from .versions import (
    MAX_MINOR_FOR_MAJOR,
    SortedVersionList,
    Version,
    VersionList,
    important,
    pypy_versions,
    update_version_list,
)


def parse_version(v: str) -> Tuple[int, int]:
    """Parse a Python version number.

    Expects 'MAJOR.MINOR', no more, no less.

    Returns a tuple (major, minor).

    This function is used for command-line argument parsing and may raise an
    argparse.ArgumentTypeError.
    """
    try:
        major, minor = map(int, v.split('.', 1))
    except ValueError:
        raise argparse.ArgumentTypeError(f'bad version: {v}')
    return (major, minor)


def parse_version_list(v: str) -> SortedVersionList:
    """Parse a list of Python version ranges.

    Expects something like '2.7,3.6-3.8'.  Allows open ranges.

    Returns an ordered list of strings, each of which represents a single
    version of the form 'MAJOR.MINOR'.

    This function is used for command-line argument parsing and may raise an
    argparse.ArgumentTypeError.
    """
    versions = set()

    for part in v.split(','):
        if '-' in part:
            lo, hi = part.split('-', 1)
        else:
            lo = hi = part

        if lo and hi:
            lo_major, lo_minor = parse_version(lo)
            hi_major, hi_minor = parse_version(hi)
        elif hi and not lo:
            hi_major, hi_minor = parse_version(hi)
            lo_major, lo_minor = hi_major, 0
        elif lo and not hi:
            lo_major, lo_minor = parse_version(lo)
            try:
                hi_major, hi_minor = lo_major, MAX_MINOR_FOR_MAJOR[lo_major]
            except KeyError:
                raise argparse.ArgumentTypeError(
                    f'bad range: {part}')
        else:
            raise argparse.ArgumentTypeError(
                f'bad range: {part}')

        if lo_major != hi_major:
            raise argparse.ArgumentTypeError(
                f'bad range: {part} ({lo_major} != {hi_major})')

        for vmin in range(lo_minor, hi_minor + 1):
            versions.add(Version(major=lo_major, minor=vmin))

    return sorted(versions)


def is_package(where: str = '.') -> bool:
    """Check if there's a Python package in the given directory.

    Currently only traditional packages having a setup.py are supported.

    Does not emit any diagnostics.
    """
    setup_py = os.path.join(where, 'setup.py')
    pyproject_toml = os.path.join(where, 'pyproject.toml')
    return os.path.exists(setup_py) or os.path.exists(pyproject_toml)


PrintFn = Callable[..., None]


def check_package(where: str = '.', *, print: PrintFn = print) -> bool:
    """Check if there's a Python package in the given directory.

    Currently only traditional packages having a setup.py are supported.

    Emits diagnostics to standard output if ``where`` is not a directory
    or doesn't have a Python package in it.
    """

    if not os.path.isdir(where):
        print("not a directory")
        return False

    if not is_package(where):
        print("no setup.py or pyproject.toml -- not a Python package?")
        return False

    return True


#
# The way check-python-version does version updates is that it calls
# various update functions and gives them a filename, then gets back
# the updated content as a list of lines.  At the end we can show the diff
# to the user or write them back to the file.
#
# But.  Sometimes we want to call two update functions for the same file
# (setup.py) to update different bits in it (classifiers and python_requires).
# We don't want to write out the result of the first updater to disk before
# we call the second one.  So, here's what we do: we remember the updated
# contents of a file in a "replacement dict", then next time instead of passing
# a filename to an update function we pass it a StringIO() with the intermedate
# results, to get back the final results.
#

ReplacementDict = Dict[str, FileLines]


def filename_or_replacement(
    pathname: str, replacements: Optional[ReplacementDict]
) -> FileOrFilename:
    """Look up a file in the replacement dict.

    This is used to batch multiple updates to a single file.

    Returns the filename if no replacement was found, or a StringIO
    with replacement contents if a replacement was found.
    """
    if replacements and pathname in replacements:
        new_lines = replacements[pathname]
        buf = StringIO("".join(new_lines))
        buf.name = pathname
        return buf
    else:
        return pathname


FilenameSet = Collection[str]


def find_sources(
    where: str = '.',
    *,
    replacements: Optional[ReplacementDict] = None,
    only: Optional[FilenameSet] = None,
    supports_update: bool = False,
) -> List[SourceFile]:
    """Find all sources that exist in a given directory.

    ``replacements`` allows you to check the result of an update (see
    `update_versions`) without actually performing an update.

    ``only`` allows you to check only a subset of the files.

    ``supports_update`` lets you skip sources that don't support updates.
    """
    sources = []
    for source in ALL_SOURCES:
        if supports_update and source.update is None:
            continue  # pragma: nocover
        pathnames = glob.glob(os.path.join(where, source.filename))
        if not pathnames:
            continue
        for pathname in pathnames:
            relpath = os.path.relpath(pathname, where)
            if only and relpath not in only and source.filename not in only:
                continue
            versions = source.extract(
                filename_or_replacement(pathname, replacements))
            if versions is not None:
                sources.append(source.for_file(pathname, versions, relpath))
    return sources


def check_versions(
    where: str = '.',
    *,
    print: PrintFn = print,
    min_width: int = 0,
    expect: Optional[VersionList] = None,
    replacements: Optional[ReplacementDict] = None,
    only: Optional[FilenameSet] = None,
) -> bool:
    """Check Python versions for a single package, located in ``where``.

    ``expect`` allows you to state what versions you expect to be supported.

    ``replacements`` allows you to check the result of an update (see
    `update_versions`) without actually performing an update.

    ``only`` allows you to check only a subset of the files.

    Emits diagnostics to standard output by calling ``print``.
    """

    sources = find_sources(where, replacements=replacements, only=only)

    if not sources:
        print('no file with version information found')
        return False

    width = max(len(source.title) for source in sources) + len(" says:")

    if expect:
        width = max(width, len('expected:'))

    width = max(width, min_width)

    for source in sources:
        print(f"{source.title} says:".ljust(width),
              ", ".join(str(v) for v in source.versions) or "(empty)")

    if expect:
        print("expected:".ljust(width), ', '.join(str(v) for v in expect))

    return supported_versions_match(sources, expect)


def supported_versions_match(
    sources: List[SourceFile],
    expect: Optional[VersionList] = None,
) -> bool:
    version_sets = []
    pypy_version_sets = []

    # This loop covers everything except for setup_requires
    for source in sources:
        if source.has_upper_bound:
            version_sets.append(important(source.versions))
        if source.check_pypy_consistency:
            pypy_version_sets.append(pypy_versions(source.versions))

    # setup_requires usually has no upper bound, which causes trouble when a
    # new Python version gets released.  Let's add an artificial upper bound
    # that matches all the other sources.
    for source in sources:
        if not source.has_upper_bound:
            max_supported_version = max(v for vs in version_sets for v in vs)
            version_sets.append({v for v in important(source.versions)
                                 if v <= max_supported_version})

    if not expect:
        expect = version_sets[0]

    expect = important(expect)
    if not all(expect == v for v in version_sets):
        return False

    if not pypy_version_sets:
        # can't happen: at least one of our sources (setup.py) has pypy info
        return True  # pragma: nocover

    expect_pypy = pypy_version_sets[0]
    return all(expect_pypy == v for v in pypy_version_sets)


def update_versions(
    where: str = '.',
    *,
    add: Optional[VersionList] = None,
    drop: Optional[VersionList] = None,
    update: Optional[VersionList] = None,
    diff: bool = False,
    dry_run: bool = False,
    only: Optional[FilenameSet] = None,
) -> ReplacementDict:
    """Update Python versions for a single package, located in ``where``.

    ``add`` will add to supported versions.
    ``drop`` will remove from supported versions.
    ``update`` will specify supported versions.

    You may combine ``add`` and ``drop``.  It doesn't make sense to combine
    ``update`` with either ``add`` or ``drop``.

    ``only`` allows you to modify only a subset of the files.

    This function performs user interaction: shows a diff, asks for
    confirmation, updates files on disk.

    ``diff``, if true, prints a diff to standard output instead of writing any
    files.

    ``dry_run``, if true, returns a dictionary mapping filenames to new file
    contents instead of asking for confirmation and writing them to disk.
    """

    replacements: ReplacementDict = {}

    sources = find_sources(where, replacements=replacements, only=only,
                           supports_update=True)
    for source in sources:
        # this assert explains supports_update=True to mypy
        assert source.update is not None
        versions = sorted(important(source.versions))
        new_versions = update_version_list(
            versions, add=add, drop=drop, update=update)
        if versions != new_versions:
            fp = filename_or_replacement(source.pathname, replacements)
            new_lines = source.update(fp, new_versions)
            if new_lines is not None:
                # TODO: refactor update_versions() into two functions, one that
                # produces a replacement dict and does no user interaction, and
                # another that does user interaction based on the contents of
                # the replacement dict.  This is because showing a diff for
                # setup.py twice (once to update classifiers and once to update
                # python_requires) is weird?
                if diff:
                    fp = filename_or_replacement(source.pathname, replacements)
                    show_diff(fp, new_lines)
                if dry_run:
                    # XXX: why do this on dry-run only, why not always return a
                    # replacement dict?
                    replacements[source.pathname] = new_lines
                if not diff and not dry_run:
                    confirm_and_update_file(source.pathname, new_lines)

    return replacements


def _main() -> None:
    """The guts of the main() function.

    Parses command-line arguments, does work, reports results, exits with an
    error code if necessary.
    """
    parser = argparse.ArgumentParser(
        description="verify that supported Python versions are the same"
                    " in setup.py, tox.ini, .travis.yml and appveyor.yml")
    parser.add_argument('--version', action='version',
                        version="%(prog)s version " + __version__)
    parser.add_argument('--expect', metavar='VERSIONS',
                        type=parse_version_list,
                        help='expect these versions to be supported, e.g.'
                             ' --expect 2.7,3.5-3.7')
    parser.add_argument('--skip-non-packages', action='store_true',
                        help='skip arguments that are not Python packages'
                             ' without warning about them')
    parser.add_argument('--only', metavar='FILES',
                        help='check only the specified files'
                             ' (comma-separated list, e.g.'
                             ' --only tox.ini,appveyor.yml)')
    parser.add_argument('where', nargs='*',
                        help='directory where a Python package with a setup.py'
                             ' and other files is located')
    group = parser.add_argument_group(
        "updating supported version lists (EXPERIMENTAL)")
    group.add_argument('--add', metavar='VERSIONS', type=parse_version_list,
                       help='add these versions to supported ones, e.g'
                            ' --add 3.8')
    group.add_argument('--drop', metavar='VERSIONS', type=parse_version_list,
                       help='drop these versions from supported ones, e.g'
                            ' --drop 2.6,3.4')
    group.add_argument('--update', metavar='VERSIONS', type=parse_version_list,
                       help='update the set of supported versions, e.g.'
                            ' --update 2.7,3.5-3.7')
    group.add_argument('--diff', action='store_true',
                       help='show a diff of proposed changes')
    group.add_argument('--dry-run', action='store_true',
                       help='verify proposed changes without'
                            ' writing them to disk')
    args = parser.parse_args()

    if args.update and args.add:
        parser.error("argument --add: not allowed with argument --update")
    if args.update and args.drop:
        parser.error("argument --drop: not allowed with argument --update")
    if args.diff and not (args.update or args.add or args.drop):
        parser.error(
            "argument --diff: not allowed without --update/--add/--drop")
    if args.dry_run and not (args.update or args.add or args.drop):
        parser.error(
            "argument --dry-run: not allowed without --update/--add/--drop")
    if args.expect and args.diff and not args.dry_run:
        # XXX: the logic of this escapes me, I think this is because
        # update_versions() doesn't return a replacement dict if you don't use
        # --dry-run?  but why?
        parser.error(
            "argument --expect: not allowed with --diff,"
            " unless you also add --dry-run")

    where = args.where or ['.']
    if args.skip_non_packages:
        where = [path for path in where if is_package(path)]

    only = [a.strip() for a in args.only.split(',')] if args.only else None

    multiple = len(where) > 1

    min_width = 0
    if multiple:
        min_width = max(len(s.title) for s in ALL_SOURCES) + len('says: ')

    mismatches = []
    for n, path in enumerate(where):
        if multiple and (not args.diff or args.dry_run):
            if n:
                print("\n")
            print(f"{path}:\n")
        if not check_package(path):
            mismatches.append(path)
            continue
        replacements = {}
        if args.add or args.drop or args.update:
            replacements = update_versions(
                path, add=args.add, drop=args.drop,
                update=args.update, diff=args.diff,
                dry_run=args.dry_run, only=only)
        if not args.diff or args.dry_run:
            if not check_versions(path, expect=args.expect,
                                  replacements=replacements,
                                  only=only,
                                  min_width=min_width):
                mismatches.append(path)
                continue

    if not args.diff or args.dry_run:
        if mismatches:
            if multiple:
                sys.exit(f"\n\nmismatch in {' '.join(mismatches)}!")
            else:
                sys.exit("\nmismatch!")
        elif multiple:
            print("\n\nall ok!")


def main() -> None:
    """The main function.

    It is here because I detest programs that print tracebacks when they're
    terminated with a Ctrl+C.  I could inline _main() here, but I didn't want
    to indent all of that code.  Maybe I should've added a decorator instead.
    """
    try:
        _main()
    except KeyboardInterrupt:
        sys.exit(2)
