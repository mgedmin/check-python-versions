import configparser
import re

from ..utils import warn, open_file, get_indent
from ..versions import is_important


TOX_INI = 'tox.ini'


def get_tox_ini_python_versions(filename=TOX_INI):
    conf = configparser.ConfigParser()
    try:
        with open_file(filename) as fp:
            conf.read_file(fp)
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


def update_tox_ini_python_versions(filename, new_versions):
    with open_file(filename) as fp:
        orig_lines = fp.readlines()
        fp.seek(0)
        conf = configparser.ConfigParser()
        try:
            conf.read_file(fp)
            envlist = conf.get('tox', 'envlist')
        except configparser.Error:
            return orig_lines

    new_envlist = update_tox_envlist(envlist, new_versions)

    new_lines = update_ini_setting(
        orig_lines, 'tox', 'envlist', new_envlist,
    )
    return new_lines


def update_tox_envlist(envlist, new_versions):
    sep = ','
    if ', ' in envlist:
        sep = ', '

    envlist = parse_envlist(envlist)
    keep = []
    for env in envlist:
        if not env.startswith('py'):
            keep.append(env)
            continue
        if not is_important(tox_env_to_py_version(env)):
            keep.append(env)
            continue
        if '-' in env:
            baseversion = tox_env_to_py_version(env)
            if baseversion in new_versions:
                keep.append(env)

    new_envlist = sep.join([
        f"py{ver.replace('.', '')}"
        for ver in new_versions
    ] + keep)

    return new_envlist


def update_ini_setting(orig_lines, section, key, new_value, filename=TOX_INI):
    lines = iter(enumerate(orig_lines))
    for n, line in lines:
        if line.startswith(f'[{section}]'):
            break
    else:
        warn(f'Did not find [{section}] in {filename}')
        return orig_lines

    # TODO: use a regex to allow an arbitrary number of spaces around =
    for n, line in lines:
        if line.startswith(f'{key} ='):
            start = n
            break
    else:
        warn(f'Did not find {key}= in [{section}] in {filename}')
        return orig_lines

    end = start + 1
    for n, line in lines:
        if line.startswith(' '):
            end = n + 1
        else:
            break

    prefix = ' '
    firstline = orig_lines[start].strip().expandtabs().replace(' ', '')
    if firstline == f'{key}=':
        if end > start + 1:
            indent = get_indent(orig_lines[start + 1])
            prefix = f'\n{indent}'

    new_lines = orig_lines[:start] + (
        f"{key} ={prefix}{new_value}\n"
    ).splitlines(True) + orig_lines[end:]

    return new_lines
