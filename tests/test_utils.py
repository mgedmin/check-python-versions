from check_python_versions.utils import pipe


def test_pipe():
    assert pipe('echo', 'hi') == 'hi\n'
