MAX_PYTHON_1_VERSION = 6  # i.e. 1.6
MAX_PYTHON_2_VERSION = 7  # i.e. 2.7
CURRENT_PYTHON_3_VERSION = 7  # i.e. 3.7

MAX_MINOR_FOR_MAJOR = {
    1: MAX_PYTHON_1_VERSION,
    2: MAX_PYTHON_2_VERSION,
    3: CURRENT_PYTHON_3_VERSION,
}


def important(versions):
    upcoming_release = f'3.{CURRENT_PYTHON_3_VERSION + 1}'
    return {
        v for v in versions
        if not v.startswith(('PyPy', 'Jython')) and v != 'nightly'
        and not v.endswith('-dev') and v != upcoming_release
    }


def update_version_list(versions, add=None, drop=None, update=None):
    if update:
        return sorted(update)
    else:
        return sorted(set(versions).union(add or ()).difference(drop or ()))
