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
from ..parsers.yaml import quote_string, update_yaml_list
from ..sources.tox import toxenv_for_version
from ..utils import FileLines, FileOrFilename, open_file
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
        if 'include' in matrix:
            for extra in matrix['include']:
                if 'python-version' in extra:
                    had_matrix = True
                    versions.add(parse_gh_ver(extra['python-version']))

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
    - "pypy-2.7"/"pypy-3.6"
    - "pypy-3.7-v7.3.3"

    https://github.com/actions/python-versions/blob/main/versions-manifest.json
    contains a list of supported CPython versions that can be downloaded
    and installed; this includes prereleases, but doesn't include PyPy.
    """
    v = str(v)
    if v.startswith(('pypy3', 'pypy-3')):
        return Version.from_string('PyPy3')
    elif v.startswith(('pypy2', 'pypy-2')):
        return Version.from_string('PyPy')
    else:
        return Version.from_string(v)


def update_gha_python_versions(
    filename: FileOrFilename,
    new_versions: SortedVersionList,
) -> FileLines:
    """Update supported Python versions in a GitHub workflow file.

    Does not touch the file but returns a list of lines with new file contents.
    """
    with open_file(filename) as fp:
        orig_lines = fp.readlines()
        fp.seek(0)
        conf = yaml.safe_load(fp)
    new_lines = orig_lines

    def keep_old_version(value: str) -> bool:
        """Determine if a Python version line should be preserved."""
        parsed = yaml.safe_load(value)
        ver = parse_gh_ver(parsed)
        if ver == Version.from_string('PyPy'):
            return any(v.major == 2 for v in new_versions)
        if ver == Version.from_string('PyPy3'):
            return any(v.major == 3 for v in new_versions)
        return False

    def keep_old_config(value: str) -> bool:
        """Determine if a Python version line should be preserved."""
        parsed = yaml.safe_load(value)
        if isinstance(parsed, list) and len(parsed) == 2:
            ver = parse_gh_ver(parsed[0])
            toxenv = str(parsed[1])
        else:
            return True
        if ver == Version.from_string('PyPy'):
            return any(v.major == 2 for v in new_versions)
        if ver == Version.from_string('PyPy3'):
            return any(v.major == 3 for v in new_versions)
        return toxenv != toxenv_for_version(ver)

    for job_name, job in conf.get('jobs', {}).items():
        matrix = job.get('strategy', {}).get('matrix', {})
        if 'python-version' in matrix:
            quote_style = ''
            if all(isinstance(v, str) for v in matrix['python-version']):
                quote_style = '"'
            yaml_new_versions = [
                quote_string(str(v), quote_style)
                for v in new_versions
            ]
            new_lines = update_yaml_list(
                new_lines,
                ('jobs', job_name, 'strategy', 'matrix', 'python-version'),
                yaml_new_versions, filename=fp.name,
                keep=keep_old_version,
            )
        if 'config' in matrix:
            yaml_configs = []
            for v in new_versions:
                quoted_ver = quote_string(str(v), '"')
                toxenv = quote_string(toxenv_for_version(v), '"')
                yaml_configs.append(f"[{quoted_ver + ',':<8} {toxenv}]")
            new_lines = update_yaml_list(
                new_lines,
                ('jobs', job_name, 'strategy', 'matrix', 'config'),
                yaml_configs, filename=fp.name,
                keep=keep_old_config,
            )

    return new_lines


GitHubActions = Source(
    filename=GHA_WORKFLOW_GLOB,
    extract=get_gha_python_versions,
    update=update_gha_python_versions,
    check_pypy_consistency=True,
    has_upper_bound=True,
)
