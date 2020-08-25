import textwrap
from io import StringIO
from typing import List

from check_python_versions.sources.manylinux import (
    get_manylinux_python_versions,
    update_manylinux_python_versions,
)
from check_python_versions.versions import Version


def v(versions: List[str]) -> List[Version]:
    return [Version.from_string(v) for v in versions]


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
               [[ "${PYBIN}" == *"cp310"* ]] || \
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
    assert get_manylinux_python_versions(manylinux_install_sh) == v([
        '2.7', '3.4', '3.5', '3.6', '3.7', '3.10',
    ])


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
        manylinux_install_sh,
        v(['3.6', '3.7', '3.8', '3.10']),
    )
    # NB: when Python 3.10 arrives, any packages still declaring support for
    # Python 3.1 will be problematic, because "cp310" matches *"cp31"*.
    # Luckily no packages using manyinux-install.sh and supporting Python 3.1
    # exist any more.
    assert "".join(result) == textwrap.dedent(r"""
        #!/usr/bin/env bash

        set -e -x

        # Compile wheels
        for PYBIN in /opt/python/*/bin; do
            if [[ "${PYBIN}" == *"cp36"* ]] || \
               [[ "${PYBIN}" == *"cp37"* ]] || \
               [[ "${PYBIN}" == *"cp38"* ]] || \
               [[ "${PYBIN}" == *"cp310"* ]]; then
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
        manylinux_install_sh,
        v(['3.6', '3.7', '3.8']),
    )
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
        manylinux_install_sh,
        v(['3.6', '3.7', '3.8']),
    )
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
