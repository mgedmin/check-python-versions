import configparser
import re
from typing import Iterable, List

from ..utils import get_indent, open_file, warn


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


def split_envlist(envlist: str) -> Iterable[str]:
    for part in re.split(r'((?:[{][^}]*[}]|[^,{\s])+)|,|\s+', envlist):
        # NB: part can be None
        part = (part or '').strip()
        if part:
            yield part


def parse_envlist(envlist: str) -> List[str]:
    envs = []
    for part in split_envlist(envlist):
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


def tox_env_to_py_version(env: str) -> str:
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
        except configparser.Error as error:
            warn(f"Could not parse {fp.name}: {error}")
            return orig_lines

    new_envlist = update_tox_envlist(envlist, new_versions)

    new_lines = update_ini_setting(
        orig_lines, 'tox', 'envlist', new_envlist,
    )
    return new_lines


def update_tox_envlist(envlist, new_versions):
    # Find a comma outside brace groups and see what whitespace follows it
    # (also note that items can be separated with whitespace without a comma,
    # but the only whitespace used this way I've seen in the wild was newlines)
    m = re.search(r',\s*|\n', re.sub(r'[{][^}]*[}]', '', envlist.strip()))
    if m:
        sep = m.group()
    else:
        sep = ','

    new_envs = [
        f"py{ver.replace('.', '')}"
        for ver in new_versions
    ]

    if 'py{' in envlist or '{py' in envlist:
        # Try to preserve braced groups
        parts = []
        added_vers = False
        for part in split_envlist(envlist):
            m = re.match(
                r'(py[{](?:\d+|py\d*)(?:,(?:\d+|py\d*))*[}])(?P<rest>.*)',
                part
            )
            if m:
                keep = [env for env in brace_expand(m.group(1))
                        if should_keep(env, new_versions)]
                parts.append(
                    'py{' + ','.join(
                        env[len('py'):] for env in new_envs + keep
                    ) + '}' + m.group('rest')
                )
                added_vers = True
                continue
            m = re.match(
                r'([{]py(?:\d+|py\d*)(?:,py(?:\d+|py\d*))*[}])(?P<rest>.*)',
                part
            )
            if m:
                keep = [env for env in brace_expand(m.group(1))
                        if should_keep(env, new_versions)]
                parts.append(
                    '{' + ','.join(new_envs + keep) + '}' + m.group('rest')
                )
                added_vers = True
                continue
            vers = brace_expand(part)
            if all(not should_keep(ver, new_versions) for ver in vers):
                continue
            if not all(should_keep(ver, new_versions) for ver in vers):
                parts.append(sep.join(
                    ver for ver in vers if should_keep(ver, new_versions)
                ))
                continue
            parts.append(part)
        if not added_vers:
            parts = new_envs + parts
        return sep.join(parts)

    # Universal expansion, might destroy braced groups
    envlist = parse_envlist(envlist)
    keep = [env for env in envlist if should_keep(env, new_versions)]
    new_envlist = sep.join(new_envs + keep)
    return new_envlist


def should_keep(env, new_versions):
    if not re.match(r'py(py)?\d*($|-)', env):
        return True
    if env == 'pypy':
        return any(ver.startswith('2') for ver in new_versions)
    if env == 'pypy3':
        return any(ver.startswith('3') for ver in new_versions)
    if '-' in env:
        baseversion = tox_env_to_py_version(env)
        if baseversion in new_versions:
            return True
    return False


def update_ini_setting(orig_lines, section, key, new_value, filename=TOX_INI):
    lines = iter(enumerate(orig_lines))
    for n, line in lines:
        if line.startswith(f'[{section}]'):
            break
    else:
        warn(f'Did not find [{section}] section in {filename}')
        return orig_lines

    space = prefix = ' '
    for n, line in lines:
        m = re.match(fr'{re.escape(key)}(\s*)=(\s*)', line.rstrip())
        if m:
            start = n
            space = m.group(1)
            if not line.rstrip().endswith('='):
                prefix = m.group(2)
            break
    else:
        warn(f'Did not find {key}= in [{section}] in {filename}')
        return orig_lines

    end = start + 1
    comments = []
    indent = '  '
    for n, line in lines:
        if line.startswith(' '):
            indent = get_indent(line)
            end = n + 1
        elif line.lstrip().startswith('#'):
            comments.append(line)
        else:
            break

    firstline = orig_lines[start].strip().expandtabs().replace(' ', '')
    if firstline == f'{key}=':
        if end > start + 1:
            prefix = f'\n{"".join(comments)}{indent}'

    new_value = new_value.replace('\n', '\n' + indent)
    new_lines = orig_lines[:start] + (
        f"{key}{space}={prefix}{new_value}\n"
    ).splitlines(True) + orig_lines[end:]

    return new_lines
