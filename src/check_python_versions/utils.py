import difflib
import logging
import os
import stat
import subprocess
import sys


log = logging.getLogger('check-python-versions')


def warn(msg):
    print(msg, file=sys.stderr)


def pipe(*cmd, **kwargs):
    if 'cwd' in kwargs:
        log.debug('EXEC cd %s && %s', kwargs['cwd'], ' '.join(cmd))
    else:
        log.debug('EXEC %s', ' '.join(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, **kwargs)
    return p.communicate()[0].decode('UTF-8', 'replace')


def confirm_and_update_file(filename, new_lines):
    if (show_diff(filename, new_lines)
            and confirm(f"Write changes to {filename}?")):
        mode = stat.S_IMODE(os.stat(filename).st_mode)
        tempfile = filename + '.tmp'
        with open(tempfile, 'w') as f:
            if hasattr(os, 'fchmod'):
                os.fchmod(f.fileno(), mode)
            else:
                # Windows, what else?
                os.chmod(tempfile, mode)
            f.writelines(new_lines)
        os.rename(tempfile, filename)


def show_diff(filename, new_lines):
    with open(filename, 'r') as f:
        old_lines = f.readlines()
    print_diff(old_lines, new_lines, filename)
    return old_lines != new_lines


def print_diff(a, b, filename):
    print(''.join(difflib.unified_diff(
        a, b,
        filename, filename,
        "(original)", "(updated)",
    )))


def confirm(prompt):
    while True:
        try:
            answer = input(f'{prompt} [y/N] ').strip().lower()
        except EOFError:
            answer = ""
        if answer == 'y':
            print()
            return True
        if answer == 'n' or not answer:
            print()
            return False
