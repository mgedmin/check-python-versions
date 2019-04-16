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

    # XXX: if python 3.7 was enabled via matrix.include, we'll add a
    # second 3.7 entry directly to top-level python, without even
    # checking for dist: xenial.

    def keep_old(ver):
        return not is_important(travis_normalize_py_version(ver))

    new_lines = update_yaml_list(
        orig_lines, "python", new_versions, filename=filename, keep=keep_old,
    )
    confirm_and_update_file(filename, orig_lines, new_lines)


def update_yaml_list(
    orig_lines, key, new_value, filename=TRAVIS_YML, keep=None,
):
    lines = iter(enumerate(orig_lines))
    for n, line in lines:
        if line == f'{key}:\n':
            break
    else:
        warn(f'Did not find {key}: setting in {filename}')
        return

    start = end = n + 1
    indent = 2
    lines_to_keep = []
    for n, line in lines:
        stripped = line.lstrip()
        if stripped.startswith('- '):
            indent = len(line) - len(stripped)
            end = n + 1
            if keep and keep(stripped[2:].strip()):
                lines_to_keep.append(line)
        elif stripped.startswith('#'):
            lines_to_keep.append(line)
            end = n + 1
        if line and line[0] != ' ':
            break

    new_lines = orig_lines[:start] + [
        f"{' ' * indent}- {value}\n"
        for value in new_value
    ] + lines_to_keep + orig_lines[end:]
    return new_lines
