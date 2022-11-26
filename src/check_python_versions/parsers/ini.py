"""
Tools for manipulating INI files.

I want to preserve formatting and comments, therefore I cannot use a standard
INI parser and serializer.
"""

import re
from typing import List

from ..utils import FileLines, get_indent, warn


def update_ini_setting(
    orig_lines: FileLines,
    section: str,
    key: str,
    new_value: str,
    *,
    filename: str,
) -> FileLines:
    """Update a setting in an .ini file.

    Preserves formatting and comments.

    ``orig_lines`` contains the old contents of the INI file.

    ``section`` and ``key`` specify which value in which section need to be
    updated.  It is an error if the section or the key do not exist.

    ``filename`` is used for error reporting.

    Returns the updated contents.
    """
    lines = iter(enumerate(orig_lines))
    for n, line in lines:
        if line.startswith(f'[{section}]'):
            break
    else:
        warn(f'Did not find [{section}] section in {filename}')
        return orig_lines

    space = prefix = ' '
    for n, line in lines:
        m = re.match(fr'{re.escape(key)}(\s*)=(\s*)', line.rstrip())
        if m:
            start = n
            space = m.group(1)
            if not line.rstrip().endswith('='):
                prefix = m.group(2)
            break
    else:
        warn(f'Did not find {key}= in [{section}] in {filename}')
        return orig_lines

    end = start + 1
    comments = []
    pending_comments: List[str] = []
    indent = '  '
    for n, line in lines:
        if line.startswith(' '):
            indent = get_indent(line)
            comments += pending_comments
            pending_comments = []
            end = n + 1
        elif line.lstrip().startswith('#'):
            pending_comments.append(line)
        else:
            break

    firstline = orig_lines[start].strip().expandtabs().replace(' ', '')
    if firstline == f'{key}=':
        if end > start + 1:
            prefix = f'\n{"".join(comments)}{indent}'

    new_value = new_value.replace('\n', '\n' + indent)
    new_lines = orig_lines[:start] + (
        f"{key}{space}={prefix}{new_value}\n"
    ).splitlines(True) + orig_lines[end:]

    return new_lines
