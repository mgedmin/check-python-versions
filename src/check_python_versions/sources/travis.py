"""
Support for Travis CI.

Travis CI is a hosted Continuous Integration solution that can be configured
by dropping a file named ``.travis.yml`` into your source repository.

There are multiple ways of selecting Python versions, some more canonical
than others:

- via the top-level ``python`` list
- via ``python`` attributes in the jobs defined by ``jobs.include`` or its
  deprecated alias ``matrix.include``
- via ``TOXENV`` environment variables in the top-level ``env`` list
  (this is discouraged and check-python-versions might drop support for this in
  the future)
"""

from typing import Dict, List, Union

import yaml

from .base import Source
from .tox import parse_envlist, tox_env_to_py_version
from ..parsers.yaml import drop_yaml_node, quote_string, update_yaml_list
from ..utils import FileLines, FileOrFilename, open_file
from ..versions import SortedVersionList, Version, is_important


TRAVIS_YML = '.travis.yml'


# Back in the day you could do
#
#   dist: trusty
#   python:
#     - pypy
#     - pypy3
#
# but then xenial came out and it did not recognize 'pypy' or 'pypy3', instead
# requiring you to explicitly spell out full version numbers like
#
#   dist: trusty
#   python:
#     - pypy2.7-6.0.0
#     - pypy3.5-6.0.0
#
# and check-python-versions could upgrade your .travis.yml from the old version
# to the new.  Happily, this is no longer necessary, because Travis supports
# 'pypy' and 'pypy3' once again.
XENIAL_SUPPORTED_PYPY_VERSIONS: Dict[str, str] = {
    # e.g. 'pypy': 'pypy2.7-7.1.1',
}


def get_travis_yml_python_versions(
    filename: FileOrFilename = TRAVIS_YML,
) -> SortedVersionList:
    """Extract supported Python versions from .travis.yml."""
    with open_file(filename) as fp:
        conf = yaml.safe_load(fp)
    versions: List[Version] = []
    if conf.get('python'):
        if isinstance(conf['python'], list):
            versions += map(travis_normalize_py_version, conf['python'])
        else:
            versions.append(travis_normalize_py_version(conf['python']))
    if 'matrix' in conf and 'include' in conf['matrix']:
        for job in conf['matrix']['include']:
            if 'python' in job:
                versions.append(travis_normalize_py_version(job['python']))
    if 'jobs' in conf and 'include' in conf['jobs']:
        for job in conf['jobs']['include']:
            if 'python' in job:
                versions.append(travis_normalize_py_version(job['python']))
    if 'env' in conf:
        toxenvs = []
        for env in conf['env']:
            if env.startswith('TOXENV='):
                toxenvs.extend(parse_envlist(env.partition('=')[-1]))
        versions.extend(e for e in map(tox_env_to_py_version, toxenvs) if e)
    return sorted(set(versions))


def travis_normalize_py_version(v: Union[str, float]) -> Version:
    """Determine Python version from Travis ``python`` value."""
    v = str(v)
    if v.startswith('pypy3'):
        # could be pypy3, pypy3.5, pypy3.5-5.10.0
        return Version.from_string('PyPy3')
    elif v.startswith('pypy'):
        # could be pypy, pypy2, pypy2.7, pypy2.7-5.10.0
        return Version.from_string('PyPy')
    else:
        return Version.from_string(v)


def needs_xenial(v: Version) -> bool:
    """Check if a Python version needs dist: xenial.

    This is obsolete now that dist: xenial is the default, but it may
    be helpful to determine when we need to drop old dist: trusty.
    """
    return v >= Version(major=3, minor=7)


def update_travis_yml_python_versions(
    filename: FileOrFilename,
    new_versions: SortedVersionList,
) -> FileLines:
    """Update supported Python versions in .travis.yml.

    Does not touch the file but returns a list of lines with new file contents.
    """
    with open_file(filename) as fp:
        orig_lines = fp.readlines()
        fp.seek(0)
        conf = yaml.safe_load(fp)
    new_lines = orig_lines

    # Make sure we're using dist: xenial if we want to use Python 3.7 or newer.
    replacements = {}
    if any(map(needs_xenial, new_versions)):
        replacements.update(XENIAL_SUPPORTED_PYPY_VERSIONS)
        if conf.get('dist') == 'trusty':
            new_lines = drop_yaml_node(new_lines, 'dist', filename=fp.name)
        if conf.get('sudo') is False:
            # sudo is ignored nowadays, but in earlier times
            # you needed both dist: xenial and sudo: required
            # to get Python 3.7
            new_lines = drop_yaml_node(new_lines, "sudo", filename=fp.name)

    def keep_old(value: str) -> bool:
        """Determine if a Python version line should be preserved."""
        ver = travis_normalize_py_version(value)
        if ver == Version.from_string('PyPy'):
            return any(v.major == 2 for v in new_versions)
        if ver == Version.from_string('PyPy3'):
            return any(v.major == 3 for v in new_versions)
        return not is_important(ver)

    def keep_old_job(job: str) -> bool:
        """Determine if a job line should be preserved."""
        if job.startswith('python:'):
            ver = job[len('python:'):].strip()
            return not is_important(travis_normalize_py_version(ver))
        else:
            return True

    quote_style = ''
    old_versions = conf.get('python', [])
    if isinstance(old_versions, (str, int, float)):
        old_versions = [old_versions]
    for toplevel in 'matrix', 'jobs':
        for job in conf.get(toplevel, {}).get('include', []):
            if 'python' in job:
                old_versions.append(job['python'])
    if old_versions and all(isinstance(v, str) for v in old_versions):
        quote_style = '"'

    yaml_new_versions = [
        quote_string(str(v), quote_style)
        for v in new_versions
    ]

    if conf.get('python'):
        new_lines = update_yaml_list(
            new_lines, "python", yaml_new_versions, filename=fp.name,
            keep=keep_old,
            replacements=replacements,
        )
    else:
        replacements = {
            f'python: {k}': f'python: {v}'
            for k, v in replacements.items()
        }
        for toplevel in 'matrix', 'jobs':
            if 'include' not in conf.get(toplevel, {}):
                continue
            new_jobs = [
                f'python: {ver}'
                for ver in yaml_new_versions
            ]
            new_lines = update_yaml_list(
                new_lines, (toplevel, "include"), new_jobs, filename=fp.name,
                replacements=replacements, keep=keep_old_job,
            )

    # If python 3.7 was enabled via matrix.include, we've just added a
    # second 3.7 entry directly to top-level python by the above code.
    # So let's drop the matrix.

    if (
        conf.get('python')
            and 'include' in conf.get('matrix', {})
            and all(
                job.get('dist') == 'xenial'
                and set(job) <= {'python', 'dist', 'sudo'}
                for job in conf['matrix']['include']
            )
    ):
        # XXX: this may drop too much or too little!
        new_lines = drop_yaml_node(new_lines, "matrix", filename=fp.name)

    return new_lines


Travis = Source(
    filename=TRAVIS_YML,
    extract=get_travis_yml_python_versions,
    update=update_travis_yml_python_versions,
    check_pypy_consistency=True,
    has_upper_bound=True,
)
