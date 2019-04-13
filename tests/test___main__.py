import sys

import pytest

from check_python_versions import __main__


def test_main(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['check-python-versions', '--help'])
    with pytest.raises(SystemExit):
        __main__.main()
