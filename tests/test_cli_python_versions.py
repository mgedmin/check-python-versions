import sys
import textwrap

from unittest.mock import Mock, patch


@patch('check_python_versions.cli.get_active_python_versions',
       Mock(return_value=[{'version': '3.10', 'latest_sw': '3.10.5'},
                          {'version': '3.11', 'latest_sw': '3.11.1'}])
       )
def test_main_show_python(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sys, 'argv', [
        'check-python-versions',
        str(tmp_path),
        '--python-versions',
        '--only', 'setup.py',
    ])
    setup_py = tmp_path / "setup.py"
    setup_py.write_text(textwrap.dedent("""\
            from setuptools import setup
            setup(
                name='foo',
                classifiers=[
                    'Programming Language :: Python :: 2.7',
                    'Programming Language :: Python :: 3.6',
                ],
            )
        """))
    import check_python_versions.cli as cpv

    cpv.main()
    assert capsys.readouterr().out == textwrap.dedent("""\
            setup.py says: 2.7, 3.6


            Active Python versions:
            version: 3.10 - latest software: 3.10.5
            version: 3.11 - latest software: 3.11.1
        """)
