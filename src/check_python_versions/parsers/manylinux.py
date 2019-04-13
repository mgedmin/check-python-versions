import re

MANYLINUX_INSTALL_SH = '.manylinux-install.sh'


def get_manylinux_python_versions(filename=MANYLINUX_INSTALL_SH):
    magic = re.compile(r'.*\[\[ "\$\{PYBIN\}" == \*"cp(\d)(\d)"\* \]\]')
    versions = []
    with open(filename) as fp:
        for line in fp:
            m = magic.match(line)
            if m:
                versions.append('{}.{}'.format(*m.groups()))
    return sorted(set(versions))
