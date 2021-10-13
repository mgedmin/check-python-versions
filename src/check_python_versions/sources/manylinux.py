"""
Support for .manylinux-install.sh.  This is a shell script used by multiple
ZopeFoundation packages that builds manylinux wheels inside
quay.io/pypa/manylinux* Docker images.

The script loops over all installed Pythons, checks if each is a supported
version using a series of `if` statements, then builds wheels for each
supported versions.  This looks like ::

    for PYBIN in /opt/python/*/bin; do
        if [[ "${PYBIN}" == *"cp27"* ]] || \
           [[ "${PYBIN}" == *"cp34"* ]] || \
           [[ "${PYBIN}" == *"cp35"* ]] || \
           [[ "${PYBIN}" == *"cp36"* ]] || \
           [[ "${PYBIN}" == *"cp37"* ]]; then
            "${PYBIN}/pip" install -e /io/
            "${PYBIN}/pip" wheel /io/ -w wheelhouse/
            rm -rf /io/build /io/*.egg-info
        fi
    done

"""

import re

from .base import Source
from ..utils import FileLines, FileOrFilename, open_file, warn
from ..versions import SortedVersionList, Version, VersionList


MANYLINUX_INSTALL_SH = '.manylinux-install.sh'


def get_manylinux_python_versions(
    filename: FileOrFilename = MANYLINUX_INSTALL_SH,
) -> SortedVersionList:
    """Extract supported Python versions from .manylinux-install.sh."""
    magic = re.compile(r'.*\[\[ "\$\{PYBIN\}" == \*"cp(\d)(\d+)"\* \]\]')
    versions = []
    with open_file(filename) as fp:
        for line in fp:
            m = magic.match(line)
            if m:
                v = Version.from_string('{}.{}'.format(*m.groups()))
                versions.append(v)
    return sorted(set(versions))


def update_manylinux_python_versions(
    filename: FileOrFilename,
    new_versions: VersionList,
) -> FileLines:
    """Update supported Python versions in .manylinux_install_sh.

    Does not touch the file but returns a list of lines with new file contents.
    """
    magic = re.compile(r'.*\[\[ "\$\{PYBIN\}" == \*"cp(\d)(\d)"\* \]\]')
    with open_file(filename) as f:
        orig_lines = f.readlines()
    lines = iter(enumerate(orig_lines))
    for n, line in lines:
        m = magic.match(line)
        if m:
            start = n
            break
    else:
        warn(f'Failed to understand {f.name}')
        return orig_lines
    for n, line in lines:
        m = magic.match(line)
        if not m:
            end = n
            break
    else:
        warn(f'Failed to understand {f.name}')
        return orig_lines

    indent = ' ' * 4
    conditions = f' || \\\n{indent}   '.join(
        f'[[ "${{PYBIN}}" == *"cp{ver.major}{ver.minor}"* ]]'
        for ver in new_versions
    )
    new_lines = orig_lines[:start] + (
        f'{indent}if {conditions}; then\n'
    ).splitlines(True) + orig_lines[end:]

    return new_lines


Manylinux = Source(
    filename=MANYLINUX_INSTALL_SH,
    extract=get_manylinux_python_versions,
    update=update_manylinux_python_versions,
    check_pypy_consistency=False,
    has_upper_bound=True,
)
