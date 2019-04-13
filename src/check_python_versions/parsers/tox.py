import configparser
import re


TOX_INI = 'tox.ini'


def get_tox_ini_python_versions(filename=TOX_INI):
    conf = configparser.ConfigParser()
    try:
        conf.read(filename)
        envlist = conf.get('tox', 'envlist')
    except configparser.Error:
        return []
    envlist = parse_envlist(envlist)
    return sorted(set(
        tox_env_to_py_version(e) for e in envlist if e.startswith('py')))


def parse_envlist(envlist):
    envs = []
    for part in re.split(r'((?:[{][^}]*[}]|[^,{\s])+)|,|\s+', envlist):
        # NB: part can be None
        part = (part or '').strip()
        if not part:
            continue
        envs += brace_expand(part)
    return envs


def brace_expand(s):
    m = re.match('^([^{]*)[{]([^}]*)[}](.*)$', s)
    if not m:
        return [s]
    left = m.group(1)
    right = m.group(3)
    res = []
    for alt in m.group(2).split(','):
        res += brace_expand(left + alt + right)
    return res


def tox_env_to_py_version(env):
    if '-' in env:
        # e.g. py34-coverage, pypy-subunit
        env = env.partition('-')[0]
    if env.startswith('pypy'):
        return 'PyPy' + env[4:]
    elif env.startswith('py') and len(env) >= 4:
        return f'{env[2]}.{env[3:]}'
    else:
        return env
