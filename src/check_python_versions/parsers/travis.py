try:
    import yaml
except ImportError:  # pragma: nocover
    yaml = None

from .tox import parse_envlist, tox_env_to_py_version
from ..utils import warn, open_file
from ..versions import is_important


TRAVIS_YML = '.travis.yml'

XENIAL_SUPPORTED_PYPY_VERSIONS = {
    # 2019-05-02:
    #   pypy is now an alias for pypy2.7-7.1.1
    #   pypy3 is now an alias for pypy3.6-7.1.1
    # you can check whether a version is available by doing e.g.
    # baseurl=https://s3.amazonaws.com/travis-python-archives/binaries
    # http head $baseurl/ubuntu/16.04/x86_64/pypy3.6-7.1.1.tar.bz2
}


def get_travis_yml_python_versions(filename=TRAVIS_YML):
    with open_file(filename) as fp:
        conf = yaml.safe_load(fp)
    versions = []
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


def needs_xenial(v):
    major, minor = map(int, v.split('.'))
    return major == 3 and minor >= 7


def update_travis_yml_python_versions(filename, new_versions):
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

    def keep_old(ver):
        ver = travis_normalize_py_version(ver)
        if ver == 'PyPy':
            return any(v.startswith('2') for v in new_versions)
        if ver == 'PyPy3':
            return any(v.startswith('3') for v in new_versions)
        return not is_important(ver)

    def keep_old_job(job):
        if job.startswith('python:'):
            ver = job[len('python:'):].strip()
            return not is_important(travis_normalize_py_version(ver))
        else:
            return True

    if conf.get('python'):
        new_lines = update_yaml_list(
            new_lines, "python", new_versions, filename=fp.name, keep=keep_old,
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
                for ver in new_versions
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


def update_yaml_list(
    orig_lines, key, new_value, filename=TRAVIS_YML, keep=None,
    replacements=None,
):
    if not isinstance(key, tuple):
        key = (key,)

    lines = iter(enumerate(orig_lines))
    current = 0
    indents = [0]
    for n, line in lines:
        stripped = line.lstrip()
        if not stripped or stripped.startswith('#'):
            continue
        indent = len(line) - len(stripped)
        if current >= len(indents):
            indents.append(indent)
        elif indent > indents[current]:
            continue
        else:
            while current > 0 and indent < indents[current]:
                del indents[current]
                current -= 1
        if stripped.startswith(f'{key[current]}:'):
            current += 1
            if current == len(key):
                break
    else:
        warn(f'Did not find {".".join(key)}: setting in {filename}')
        return orig_lines

    start = n
    end = n + 1
    indent = 2
    list_indent = None
    keep_before = []
    keep_after = []
    lines_to_keep = keep_before
    kept_last = False
    for n, line in lines:
        stripped = line.lstrip()
        line_indent = len(line) - len(stripped)
        if list_indent is None and stripped.startswith('- '):
            list_indent = line_indent
        if stripped.startswith('- ') and line_indent == list_indent:
            lines_to_keep = keep_after
            indent = line_indent
            end = n + 1
            value = stripped[2:].strip()
            kept_last = keep and keep(value)
            if kept_last:
                if replacements and value in replacements:
                    lines_to_keep.append(
                        f"{' '* indent}- {replacements[value]}\n"
                    )
                else:
                    lines_to_keep.append(line)
        elif stripped.startswith('#'):
            lines_to_keep.append(line)
            end = n + 1
        elif line_indent > indent:
            if kept_last:
                lines_to_keep.append(line)
            end = n + 1
        elif line == '\n':
            continue
        elif line[0] != ' ':
            break
        elif list_indent is not None and line_indent < list_indent:
            break

    new_lines = orig_lines[:start] + [
        f"{' ' * indents[-1]}{key[-1]}:\n"
    ] + keep_before + [
        f"{' ' * indent}- {value}\n"
        for value in new_value
    ] + keep_after + orig_lines[end:]
    return new_lines


def drop_yaml_node(orig_lines, key, filename=TRAVIS_YML):
    lines = iter(enumerate(orig_lines))
    where = None
    for n, line in lines:
        if line.startswith(f'{key}:'):
            if where is not None:
                warn(
                    f"Duplicate {key}: setting in {filename}"
                    f" (lines {where + 1} and {n + 1})"
                )
            where = n
    if where is None:
        return orig_lines

    lines = iter(enumerate(orig_lines[where + 1:], where + 1))

    start = where
    end = start + 1
    for n, line in lines:
        if line and line[0] != ' ':
            break
        else:
            end = n + 1
    new_lines = orig_lines[:start] + orig_lines[end:]

    return new_lines


def add_yaml_node(orig_lines, key, value, before=None):
    lines = iter(enumerate(orig_lines))
    where = len(orig_lines)
    if before:
        if not isinstance(before, (list, tuple, set)):
            before = (before, )
        lines = iter(enumerate(orig_lines))
        for n, line in lines:
            if any(line == f'{key}:\n' for key in before):
                where = n
                break

    new_lines = orig_lines[:where] + [
        f'{key}: {value}\n'
    ] + orig_lines[where:]
    return new_lines
