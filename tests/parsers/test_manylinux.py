import textwrap

from check_python_versions.parsers.manylinux import (
    get_manylinux_python_versions,
)


def test_get_manylinux_python_versions(tmp_path):
    manylinux_install_sh = tmp_path / ".manylinux-install.sh"
    manylinux_install_sh.write_text(textwrap.dedent(r"""
        #!/usr/bin/env bash

        set -e -x

        # Compile wheels
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

        # Bundle external shared libraries into the wheels
        for whl in wheelhouse/zope.interface*.whl; do
            auditwheel repair "$whl" -w /io/wheelhouse/
        done
    """.lstrip('\n')))
    assert get_manylinux_python_versions(manylinux_install_sh) == [
        '2.7', '3.4', '3.5', '3.6', '3.7',
    ]
