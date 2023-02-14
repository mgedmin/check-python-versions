"""
Assorted utilities that didn't fit elsewhere.

Yes, this is a sign of bad design.  Maybe someday I'll clean it up.
"""

import difflib
import logging
import os
import stat
import subprocess
import sys
from contextlib import contextmanager
from typing import (
    Any,
    Iterator,
    List,
    Sequence,
    TextIO,
    Tuple,
    TypeVar,
    Union,
    cast,
)


log = logging.getLogger('check-python-versions')


T = TypeVar('T')
OneOrMore = Union[T, Sequence[T]]
OneOrTuple = Union[T, Tuple[T, ...]]


FileObjectWithName = TextIO  # also has a .name attribute
FileOrFilename = Union[str, FileObjectWithName]
FileLines = List[str]


def get_indent(line: str) -> str:
    """Return the indentation part of a line of text."""
    return line[:-len(line.lstrip())]


def warn(msg: str) -> None:
    """Print a warning to standard error."""
    print(msg, file=sys.stderr)


def is_file_object(filename_or_file_object: FileOrFilename) -> bool:
    """Is this a file-like object?"""
    return hasattr(filename_or_file_object, 'read')


def file_name(filename_or_file_object: FileOrFilename) -> str:
    """Return the name of the file."""
    if is_file_object(filename_or_file_object):
        return cast(TextIO, filename_or_file_object).name
    else:
        return str(filename_or_file_object)


@contextmanager
def open_file(filename_or_file_object: FileOrFilename) -> Iterator[TextIO]:
    """Context manager for opening files."""
    if is_file_object(filename_or_file_object):
        yield cast(TextIO, filename_or_file_object)
    else:
        with open(cast(str, filename_or_file_object)) as fp:
            yield fp


def pipe(*cmd: str, **kwargs: Any) -> str:
    """Run a subprocess and return its standard output.

    Keyword arguments are passed directly to `subprocess.Popen`.

    Standard input and standard error are not redirected.
    """
    if 'cwd' in kwargs:
        log.debug('EXEC cd %s && %s', kwargs['cwd'], ' '.join(cmd))
    else:
        log.debug('EXEC %s', ' '.join(cmd))
    p = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                         **kwargs)
    return cast(bytes, p.communicate()[0]).decode('UTF-8', 'replace')


def confirm_and_update_file(filename: str, new_lines: FileLines) -> None:
    """Update a file with new content, after asking for confirmation."""
    if (show_diff(filename, new_lines)
            and confirm(f"Write changes to {filename}?")):
        mode = stat.S_IMODE(os.stat(filename).st_mode)
        tempfile = filename + '.tmp'
        with open(tempfile, 'w') as f:
            if hasattr(os, 'fchmod'):
                os.fchmod(f.fileno(), mode)
            else:  # pragma: windows
                # Windows, what else?
                os.chmod(tempfile, mode)
            f.writelines(new_lines)
        try:
            os.rename(tempfile, filename)
        except FileExistsError:  # pragma: windows
            # No atomic replace on Windows
            os.unlink(filename)
            os.rename(tempfile, filename)


def show_diff(
    filename_or_file_object: FileOrFilename,
    new_lines: FileLines
) -> bool:
    """Show the difference between two versions of a file."""
    with open_file(filename_or_file_object) as f:
        old_lines = f.readlines()
    print_diff(old_lines, new_lines, f.name)
    return old_lines != new_lines


def print_diff(a: List[str], b: List[str], filename: str) -> None:
    """Show the difference between two versions of a file."""
    print(''.join(difflib.unified_diff(
        a, b,
        filename, filename,
        "(original)", "(updated)",
    )))


def confirm(prompt: str) -> bool:
    """Ask the user to confirm an action."""
    while True:
        try:
            answer = input(f'{prompt} [y/N] ').strip().lower()
        except EOFError:
            answer = ""
        if answer == 'y':
            print()
            return True
        if answer == 'n' or not answer:
            print()
            return False
