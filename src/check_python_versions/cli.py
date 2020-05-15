import argparse
import os
import sys
from io import StringIO
from typing import Callable, Collection, Dict, List, Optional, Tuple

from . import __version__
from .parsers.appveyor import (
    APPVEYOR_YML,
    get_appveyor_yml_python_versions,
    update_appveyor_yml_python_versions,
)
from .parsers.manylinux import (
    MANYLINUX_INSTALL_SH,
    get_manylinux_python_versions,
    update_manylinux_python_versions,
)
from .parsers.python import (
    get_python_requires,
    get_supported_python_versions,
    update_python_requires,
    update_supported_python_versions,
)
from .parsers.tox import (
    TOX_INI,
    get_tox_ini_python_versions,
    update_tox_ini_python_versions,
)
from .parsers.travis import (
    TRAVIS_YML,
    get_travis_yml_python_versions,
    update_travis_yml_python_versions,
)
from .utils import (
    FileLines,
    FileOrFilename,
    confirm_and_update_file,
    show_diff,
)
from .versions import (
    MAX_MINOR_FOR_MAJOR,
    SortedVersionList,
    VersionList,
    important,
    update_version_list,
)


try:
    import yaml  # noqa: F401
except ImportError:  # pragma: nocover
    # Shouldn't happen, we install_requires=['PyYAML'], but maybe someone is
    # running ./check-python-versions directly from a git checkout.
    print("PyYAML is needed for Travis CI/Appveyor support"
          " (apt install python3-yaml)")


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
            versions.add(f'{lo_major}.{vmin}')

    return sorted(versions)


def is_package(where: str = '.') -> bool:
    """Check if there's a Python package in the given directory.

    Currently only traditional packages having a setup.py are supported.

    Does not emit any diagnostics.
    """
    # TODO: support setup.py-less packages that use pyproject.toml instead
    setup_py = os.path.join(where, 'setup.py')
    return os.path.exists(setup_py)


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
        print("no setup.py -- not a Python package?")
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
ExtractorFn = Callable[[FileOrFilename], Optional[SortedVersionList]]


def check_versions(
    where: str = '.',
    *,
    print: PrintFn = print,
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

    sources: List[Tuple[str, ExtractorFn, str]] = [
        # title, extractor, filename
        ('setup.py', get_supported_python_versions, 'setup.py'),
        ('- python_requires', get_python_requires, 'setup.py'),
        (TOX_INI, get_tox_ini_python_versions, TOX_INI),
        (TRAVIS_YML, get_travis_yml_python_versions, TRAVIS_YML),
        (APPVEYOR_YML, get_appveyor_yml_python_versions, APPVEYOR_YML),
        (MANYLINUX_INSTALL_SH, get_manylinux_python_versions,
         MANYLINUX_INSTALL_SH),
    ]

    width = max(len(title) for title, *etc in sources) + len(" says:")

    if expect:
        width = max(width, len('expected:'))

    version_sets = []

    for (title, extractor, filename) in sources:
        if only and filename not in only:
            continue
        pathname = os.path.join(where, filename)
        if not os.path.exists(pathname):
            continue
        versions = extractor(filename_or_replacement(pathname, replacements))
        if versions is None:
            continue
        print(f"{title} says:".ljust(width), ", ".join(versions) or "(empty)")
        version_sets.append(important(versions))

    if not expect:
        expect = version_sets[0]
    else:
        print("expected:".ljust(width), ', '.join(expect))

    expect = important(expect)
    return all(
        expect == v for v in version_sets
    )


UpdaterFn = Callable[[FileOrFilename, SortedVersionList], Optional[FileLines]]


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

    sources: List[Tuple[str, ExtractorFn, UpdaterFn]] = [
        # filename, extractor, updater
        ('setup.py', get_supported_python_versions,
         update_supported_python_versions),
        ('setup.py', get_python_requires,
         update_python_requires),
        (TOX_INI, get_tox_ini_python_versions,
         update_tox_ini_python_versions),
        (TRAVIS_YML, get_travis_yml_python_versions,
         update_travis_yml_python_versions),
        (APPVEYOR_YML, get_appveyor_yml_python_versions,
         update_appveyor_yml_python_versions),
        (MANYLINUX_INSTALL_SH, get_manylinux_python_versions,
         update_manylinux_python_versions),
        # TODO: CHANGES.rst
    ]
    replacements: ReplacementDict = {}

    for (filename, extractor, updater) in sources:
        if only and filename not in only:
            continue
        pathname = os.path.join(where, filename)
        if not os.path.exists(pathname):
            continue
        versions = extractor(filename_or_replacement(pathname, replacements))
        if versions is None:
            continue

        versions = sorted(important(versions))
        new_versions = update_version_list(
            versions, add=add, drop=drop, update=update)
        if versions != new_versions:
            fp = filename_or_replacement(pathname, replacements)
            new_lines = updater(fp, new_versions)
            if new_lines is not None:
                # TODO: refactor this into two functions, one that produces a
                # replacement dict and does no user interaction, and another
                # that does user interaction based on the contents of the
                # replacement dict.
                if diff:
                    fp = filename_or_replacement(pathname, replacements)
                    show_diff(fp, new_lines)
                if dry_run:
                    # XXX: why do this on dry-run only, why not always return a
                    # replacement dict?
                    replacements[pathname] = new_lines
                if not diff and not dry_run:
                    confirm_and_update_file(pathname, new_lines)

    return replacements


def _main() -> None:
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
                                  only=only):
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
    try:
        _main()
    except KeyboardInterrupt:
        sys.exit(2)
