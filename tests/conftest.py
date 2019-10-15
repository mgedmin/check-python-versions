import pytest

from check_python_versions import versions


@pytest.fixture
def fix_max_python_3_version(monkeypatch):
    def helper(ver):
        monkeypatch.setattr(versions, 'CURRENT_PYTHON_3_VERSION', ver)
        monkeypatch.setitem(versions.MAX_MINOR_FOR_MAJOR, 3, ver)
    return helper
