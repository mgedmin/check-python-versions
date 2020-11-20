"""
Support for GitHub Actions.

GitHub Actions are very flexible, so this code is going to make some
simplifying assumptions:

- you use a matrix strategy
  - on 'python-version' that contains python versions, or
  - on 'config' that contains lists of [python_version, tox_env]
"""

from typing import Optional, Set, Union

import yaml

from .base import Source
from ..utils import FileOrFilename, open_file
from ..versions import SortedVersionList, Version


GHA_WORKFLOW_FILE = '.github/workflows/tests.yml'
GHA_WORKFLOW_GLOB = '.github/workflows/*.yml'


def get_gha_python_versions(
    filename: FileOrFilename = GHA_WORKFLOW_FILE,
) -> Optional[SortedVersionList]:
    """Extract supported Python versions from a GitHub workflow."""
    with open_file(filename) as fp:
        conf = yaml.safe_load(fp)

    versions: Set[Version] = set()
    had_matrix = False
    for job_name, job in conf.get('jobs', {}).items():
        matrix = job.get('strategy', {}).get('matrix', {})
        if 'python-version' in matrix:
            had_matrix = True
            versions.update(
                e for e in map(parse_gh_ver, matrix['python-version']) if e)
        if 'config' in matrix:
            had_matrix = True
            versions.update(
                parse_gh_ver(c[0])
                for c in matrix['config']
                if isinstance(c, list)
            )

    if not had_matrix:
        return None
    return sorted(set(versions))


def parse_gh_ver(v: Union[str, float]) -> Version:
    """Parse Python versions used for actions/setup-python@v2.

    This format is not fully well documented.  There's support for
    specifying things like

    - "3.x" (latest minor in Python 3.x; currently 3.9)
    - "3.7" (latest bugfix in Python 3.7)
    - "3.7.2" (specific version to be downloaded and installed)
    - "pypy2"/"pypy3"

    https://github.com/actions/python-versions/blob/main/versions-manifest.json
    contains a list of supported CPython versions that can be downloaded
    and installed; this includes prereleases, but doesn't include PyPy.
    """
    v = str(v)
    if v.startswith('pypy3'):
        return Version.from_string('PyPy3')
    elif v.startswith('pypy2'):
        return Version.from_string('PyPy')
    else:
        return Version.from_string(v)


GitHubActions = Source(
    filename=GHA_WORKFLOW_GLOB,
    extract=get_gha_python_versions,
    update=None,
)
