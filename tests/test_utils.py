import sys
from io import StringIO

import pytest

from check_python_versions.utils import confirm, file_name, get_indent, pipe


@pytest.mark.parametrize(['line', 'expected'], [
    ('no indent\n', ''),
    ('  indent\n', '  '),
    ('  trailing spaces  \n', '  '),
    ('\t  tabs and spaces\n', '\t  '),
    ('\n', ''),
    ('  \n', ''),
    ('', ''),
])
def test_get_indent(line, expected):
    assert get_indent(line) == expected


def test_file_name(tmp_path):
    tmpfile = tmp_path / 'test.txt'
    assert file_name(tmpfile) == str(tmpfile)
    with open(tmpfile, 'w') as fp:
        assert file_name(fp) == str(tmpfile)


def test_pipe():
    assert pipe('echo', 'hi') == 'hi\n'


def test_confirm_eof(monkeypatch):
    monkeypatch.setattr(sys, 'stdin', StringIO())
    assert not confirm("Hello how are you?")


def test_confirm_default(monkeypatch):
    monkeypatch.setattr(sys, 'stdin', StringIO("\n"))
    assert not confirm("Hello how are you?")


def test_confirm_no(monkeypatch):
    monkeypatch.setattr(sys, 'stdin', StringIO("n\n"))
    assert not confirm("Hello how are you?")


def test_confirm_yes(monkeypatch):
    monkeypatch.setattr(sys, 'stdin', StringIO("y\n"))
    assert confirm("Hello how are you?")


def test_confirm_neither(monkeypatch):
    monkeypatch.setattr(sys, 'stdin', StringIO("t\ny\n"))
    assert confirm("Hello how are you?")
