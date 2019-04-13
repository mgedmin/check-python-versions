import pytest

from check_python_versions.versions import MAX_MINOR_FOR_MAJOR


@pytest.fixture
def fix_max_python_3_version(monkeypatch):
    def helper(ver):
        monkeypatch.setitem(MAX_MINOR_FOR_MAJOR, 3, ver)
    return helper
