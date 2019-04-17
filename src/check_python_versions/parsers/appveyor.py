try:
    import yaml
except ImportError:  # pragma: nocover
    yaml = None

from .tox import parse_envlist, tox_env_to_py_version
from .travis import update_yaml_list
from ..utils import open_file


APPVEYOR_YML = 'appveyor.yml'


def get_appveyor_yml_python_versions(filename=APPVEYOR_YML):
    with open_file(filename) as fp:
        conf = yaml.safe_load(fp)
    # There's more than one way of doing this, I'm setting %PYTHON% to
    # the directory that has a Python interpreter (C:\PythonXY)
    versions = []
    for env in conf['environment']['matrix']:
        for var, value in env.items():
            if var.lower() == 'python':
                versions.append(appveyor_normalize_py_version(value))
            elif var == 'TOXENV':
                toxenvs = parse_envlist(value)
                versions.extend(
                    tox_env_to_py_version(e)
                    for e in toxenvs if e.startswith('py'))
    return sorted(set(versions))


def appveyor_normalize_py_version(ver):
    ver = str(ver).lower()
    if ver.startswith('c:\\python'):
        ver = ver[len('c:\\python'):]
    if ver.endswith('\\'):
        ver = ver[:-1]
    if ver.endswith('-x64'):
        ver = ver[:-len('-x64')]
    assert len(ver) >= 2 and ver[:2].isdigit()
    return f'{ver[0]}.{ver[1:]}'


def appveyor_detect_py_version_pattern(ver):
    ver = str(ver)
    pattern = '{}'
    if ver.lower().startswith('c:\\python'):
        pos = len('c:\\python')
        prefix, ver = ver[:pos], ver[pos:]
        pattern = pattern.format(f'{prefix}{{}}')
    if ver.endswith('\\'):
        ver = ver[:-1]
        pattern = pattern.format(f'{{}}\\')
    if ver.lower().endswith('-x64'):
        pos = -len('-x64')
        ver, suffix = ver[:pos], ver[pos:]
        pattern = pattern.format(f'{{}}{suffix}')
    assert len(ver) >= 2 and ver[:2].isdigit()
    return pattern.format('{}{}')


def escape(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def update_appveyor_yml_python_versions(filename, new_versions):
    with open_file(filename) as fp:
        orig_lines = fp.readlines()
        fp.seek(0)
        conf = yaml.safe_load(fp)

    varname = 'PYTHON'
    pattern = '{}{}'
    for env in conf['environment']['matrix']:
        for var, value in env.items():
            if var.lower() == 'python':
                varname = var
                pattern = appveyor_detect_py_version_pattern(value)
                break

    new_environments = [
        f'{varname}: "{escape(pattern.format(*ver.split(".", 1)))}"'
        for ver in new_versions
    ]
    new_lines = update_yaml_list(orig_lines, '  matrix', new_environments)
    return new_lines
