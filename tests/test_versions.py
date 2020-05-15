from check_python_versions.versions import important, update_version_list


def test_important(fix_max_python_3_version):
    fix_max_python_3_version(7)
    assert important({
        '2.7', '3.4', '3.7-dev', '3.8', 'nightly', 'PyPy3', 'Jython'
    }) == {'2.7', '3.4'}


def test_update_version_list():
    assert update_version_list(['2.7', '3.4']) == ['2.7', '3.4']
    assert update_version_list(['2.7', '3.4'], add=['3.4', '3.5']) == [
        '2.7', '3.4', '3.5',
    ]
    assert update_version_list(['2.7', '3.4'], drop=['3.4', '3.5']) == [
        '2.7',
    ]
    assert update_version_list(['2.7', '3.4'], add=['3.5'], drop=['2.7']) == [
        '3.4', '3.5',
    ]
    assert update_version_list(['2.7', '3.4'], drop=['3.4', '3.5']) == [
        '2.7',
    ]
    assert update_version_list(['2.7', '3.4'], update=['3.4', '3.5']) == [
        '3.4', '3.5',
    ]
