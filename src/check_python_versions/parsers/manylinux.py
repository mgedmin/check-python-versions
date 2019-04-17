import re

from ..utils import open_file, warn

MANYLINUX_INSTALL_SH = '.manylinux-install.sh'


def get_manylinux_python_versions(filename=MANYLINUX_INSTALL_SH):
    magic = re.compile(r'.*\[\[ "\$\{PYBIN\}" == \*"cp(\d)(\d)"\* \]\]')
    versions = []
    with open_file(filename) as fp:
        for line in fp:
            m = magic.match(line)
            if m:
                versions.append('{}.{}'.format(*m.groups()))
    return sorted(set(versions))


def update_manylinux_python_versions(filename, new_versions):
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
        f'[[ "${{PYBIN}}" == *"cp{ver.replace(".", "")}"* ]]'
        for ver in new_versions
    )
    new_lines = orig_lines[:start] + (
        f'{indent}if {conditions}; then\n'
    ).splitlines(True) + orig_lines[end:]

    return new_lines
