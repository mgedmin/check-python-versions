import textwrap
from io import StringIO

from check_python_versions.sources.manylinux import (
    get_manylinux_python_versions,
    update_manylinux_python_versions,
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


def test_update_manylinux_python_versions():
    manylinux_install_sh = StringIO(textwrap.dedent(r"""
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
    """).lstrip('\n'))
    result = update_manylinux_python_versions(
        manylinux_install_sh, ['3.6', '3.7', '3.8'])
    assert "".join(result) == textwrap.dedent(r"""
        #!/usr/bin/env bash

        set -e -x

        # Compile wheels
        for PYBIN in /opt/python/*/bin; do
            if [[ "${PYBIN}" == *"cp36"* ]] || \
               [[ "${PYBIN}" == *"cp37"* ]] || \
               [[ "${PYBIN}" == *"cp38"* ]]; then
                "${PYBIN}/pip" install -e /io/
                "${PYBIN}/pip" wheel /io/ -w wheelhouse/
                   rm -rf /io/build /io/*.egg-info
            fi
        done

        # Bundle external shared libraries into the wheels
        for whl in wheelhouse/zope.interface*.whl; do
            auditwheel repair "$whl" -w /io/wheelhouse/
        done
    """).lstrip('\n')


def test_update_manylinux_python_versions_failure(capsys):
    manylinux_install_sh = StringIO(textwrap.dedent(r"""
        #!/usr/bin/env bash

        # TBD
    """).lstrip('\n'))
    manylinux_install_sh.name = '.manylinux-install.sh'
    result = update_manylinux_python_versions(
        manylinux_install_sh, ['3.6', '3.7', '3.8'])
    assert "".join(result) == textwrap.dedent(r"""
        #!/usr/bin/env bash

        # TBD
    """).lstrip('\n')
    assert (
        "Failed to understand .manylinux-install.sh"
        in capsys.readouterr().err
    )


def test_update_manylinux_python_versions_truncated(capsys):
    manylinux_install_sh = StringIO(textwrap.dedent(r"""
        #!/usr/bin/env bash

        set -e -x

        # Compile wheels
        for PYBIN in /opt/python/*/bin; do
            if [[ "${PYBIN}" == *"cp27"* ]] || \
               [[ "${PYBIN}" == *"cp34"* ]] || \
               [[ "${PYBIN}" == *"cp35"* ]] || \
    """).lstrip('\n'))
    manylinux_install_sh.name = '.manylinux-install.sh'
    result = update_manylinux_python_versions(
        manylinux_install_sh, ['3.6', '3.7', '3.8'])
    assert "".join(result) == textwrap.dedent(r"""
        #!/usr/bin/env bash

        set -e -x

        # Compile wheels
        for PYBIN in /opt/python/*/bin; do
            if [[ "${PYBIN}" == *"cp27"* ]] || \
               [[ "${PYBIN}" == *"cp34"* ]] || \
               [[ "${PYBIN}" == *"cp35"* ]] || \
    """).lstrip('\n')
    assert (
        "Failed to understand .manylinux-install.sh"
        in capsys.readouterr().err
    )
