try:
    import yaml
except ImportError:  # pragma: nocover
    yaml = None

from .tox import parse_envlist, tox_env_to_py_version


APPVEYOR_YML = 'appveyor.yml'


def get_appveyor_yml_python_versions(filename=APPVEYOR_YML):
    with open(filename) as fp:
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
