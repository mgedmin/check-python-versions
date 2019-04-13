try:
    import yaml
except ImportError:  # pragma: nocover
    yaml = None

from .tox import parse_envlist, tox_env_to_py_version
from ..utils import warn, confirm_and_update_file
from ..versions import is_important


TRAVIS_YML = '.travis.yml'


def get_travis_yml_python_versions(filename=TRAVIS_YML):
    with open(filename) as fp:
        conf = yaml.safe_load(fp)
    versions = []
    if 'python' in conf:
        versions += map(travis_normalize_py_version, conf['python'])
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
        versions.extend(
            tox_env_to_py_version(e) for e in toxenvs if e.startswith('py'))
    return sorted(set(versions))


def travis_normalize_py_version(v):
    v = str(v)
    if v.startswith('pypy3'):
        # could be pypy3, pypy3.5, pypy3.5-5.10.0
        return 'PyPy3'
    elif v.startswith('pypy'):
        # could be pypy, pypy2, pypy2.7, pypy2.7-5.10.0
        return 'PyPy'
    else:
        return v


def update_travis_yml_python_versions(filename, new_versions):
    with open(filename) as fp:
        orig_lines = fp.readlines()

    lines = iter(enumerate(orig_lines))
    for n, line in lines:
        if line == 'python:\n':
            break
    else:
        warn(f'Did not find python setting in {filename}')
        return

    start = end = n + 1
    indent = 2
    keep = []
    for n, line in lines:
        stripped = line.lstrip()
        if stripped.startswith('- '):
            indent = len(line) - len(stripped)
            end = n + 1
            ver = stripped[2:].strip()
            if not is_important(travis_normalize_py_version(ver)):
                keep.append(line)
        elif stripped.startswith('#'):
            keep.append(line)
            end = n + 1
        if line and line[0] != ' ':
            break

    # XXX: if python 3.7 was enabled via matrix.include, we'll add a
    # second 3.7 entry directly to top-level python, without even
    # checking for dist: xenial.
    new_lines = orig_lines[:start] + [
        f"{' ' * indent}- {ver}\n"
        for ver in new_versions
    ] + keep + orig_lines[end:]
    confirm_and_update_file(filename, orig_lines, new_lines)
