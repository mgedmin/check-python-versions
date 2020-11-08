import textwrap

from check_python_versions.parsers.ini import update_ini_setting


def test_update_ini_setting():
    source_lines = textwrap.dedent("""\
        [tox]
        envlist = py26,py27
        usedevelop = true
    """).splitlines(True)
    result = update_ini_setting(source_lines, 'tox', 'envlist', 'py36,py37',
                                filename='tox.ini')
    assert "".join(result) == textwrap.dedent("""\
        [tox]
        envlist = py36,py37
        usedevelop = true
    """)


def test_update_ini_setting_nospaces():
    source_lines = textwrap.dedent("""\
        [tox]
        envlist=py26,py27
        usedevelop=true
    """).splitlines(True)
    result = update_ini_setting(source_lines, 'tox', 'envlist', 'py36,py37',
                                filename='tox.ini')
    assert "".join(result) == textwrap.dedent("""\
        [tox]
        envlist=py36,py37
        usedevelop=true
    """)


def test_update_ini_setting_from_empty():
    source_lines = textwrap.dedent("""\
        [tox]
        envlist =
        usedevelop = true
    """).splitlines(True)
    result = update_ini_setting(source_lines, 'tox', 'envlist', 'py36,py37',
                                filename='tox.ini')
    assert "".join(result) == textwrap.dedent("""\
        [tox]
        envlist = py36,py37
        usedevelop = true
    """)


def test_update_ini_setting_multiline():
    source_lines = textwrap.dedent("""\
        [tox]
        envlist =
            py26,
            py27
        usedevelop = true
    """).splitlines(True)
    result = update_ini_setting(source_lines, 'tox', 'envlist', 'py36,\npy37',
                                filename='tox.ini')
    assert "".join(result) == textwrap.dedent("""\
        [tox]
        envlist =
            py36,
            py37
        usedevelop = true
    """)


def test_update_ini_setting_multiline_first_on_same_line():
    source_lines = textwrap.dedent("""\
        [tox]
        envlist = py26,
                  py27
        usedevelop = true
    """).splitlines(True)
    result = update_ini_setting(source_lines, 'tox', 'envlist', 'py36,\npy37',
                                filename='tox.ini')
    assert "".join(result) == textwrap.dedent("""\
        [tox]
        envlist = py36,
                  py37
        usedevelop = true
    """)


def test_update_ini_setting_multiline_with_comments():
    source_lines = textwrap.dedent("""\
        [tox]
        envlist =
        # blah blah
        #   py26,py27,pypy
            py26,py27
        # etc.
        usedevelop = true
    """).splitlines(True)
    result = update_ini_setting(source_lines, 'tox', 'envlist', 'py36,py37',
                                filename='tox.ini')
    assert "".join(result) == textwrap.dedent("""\
        [tox]
        envlist =
        # blah blah
        #   py26,py27,pypy
            py36,py37
        # etc.
        usedevelop = true
    """)


def test_update_ini_setting_no_section(capsys):
    source_lines = textwrap.dedent("""\
        [toxx]
    """).splitlines(True)
    result = update_ini_setting(source_lines, 'tox', 'envlist', 'py36,py37',
                                filename='tox.ini')
    assert "".join(result) == textwrap.dedent("""\
        [toxx]
    """)
    assert (
        "Did not find [tox] section in tox.ini"
        in capsys.readouterr().err
    )


def test_update_ini_setting_no_key(capsys):
    source_lines = textwrap.dedent("""\
        [tox]
        usedevelop = true
    """).splitlines(True)
    result = update_ini_setting(source_lines, 'tox', 'envlist', 'py36,py37',
                                filename='tox.ini')
    assert "".join(result) == textwrap.dedent("""\
        [tox]
        usedevelop = true
    """)
    assert (
        "Did not find envlist= in [tox] in tox.ini"
        in capsys.readouterr().err
    )
